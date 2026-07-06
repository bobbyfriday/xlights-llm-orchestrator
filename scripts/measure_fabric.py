"""Fabric measurement — reproducible corpus-comparison stats for a show's effect fabric.

The 2026-06-11 corpus study (`docs/effects-layering-analysis.md`) was a one-off: it found the
generated fabric inverted relative to community practice (punctuation-heavy vs woven-motion) but
the number was never re-derived. This module makes that comparison a *tool*: one report shape, two
input modes, so a community `.xsq` and one of our generated shows produce directly comparable
tables.

Two input modes, one report shape (`FabricStats`):
    - ``stats_from_instructions(instrs, duration_s, sections=...)`` — over an `instructions` cache
      (a list of `EffectInstruction` dumps) or the hermetic golden fixture. This is the honest,
      author-side number for our shows and the CI-runnable canary.
    - ``stats_from_xsq(path)`` — parse the `<Effect>` elements of a finalized `.xsq` (a community
      show OR our own saved output), so both sides measure identically.

`FabricStats` carries: effects/min, share by family (motion / punctuation / bed / feature / other),
share by type, median duration by type (ms), blend-mode and transition share, value-curve kinds
(brightness vs motion params), a layer-depth histogram, a prop-row-equivalent density
normalization (`per_prop_expansion`), and `per_section` (a list of `SectionStats`, intensity- and
treatment-bucketed).

The §2.1 community aggregates are frozen into `COMMUNITY` so the comparison still runs when the
licensed vendor corpus is not on the machine.

Run as a CLI::

    python scripts/measure_fabric.py <instructions.json>|<show.xsq> [--duration-s S] [--rgbeffects X]
    python scripts/measure_fabric.py --golden       # measure tests/fixtures/golden_instructions.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# The per-effect capability tables are the single source of truth for effect families; import them
# rather than re-listing (a family split that drifts from effect_meta would mis-measure the fabric).
_PKG_SRC = Path(__file__).resolve().parent.parent / "packages" / "xlights-orchestrator" / "src"
if _PKG_SRC.is_dir() and str(_PKG_SRC) not in sys.path:      # allow direct `python scripts/…` runs
    sys.path.insert(0, str(_PKG_SRC))
_CORE_SRC = Path(__file__).resolve().parent.parent / "packages" / "xlights-core" / "src"
if _CORE_SRC.is_dir() and str(_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_CORE_SRC))

from xlights_orchestrator.pipeline.effect_meta import EFFECT_META, MOTION_EFFECTS  # noqa: E402

# xLights writes an effect's DISPLAY name into a placed <Effect name="…"> (e.g. "Single Strand"),
# but effect_meta/our instructions use the placeable form ("SingleStrand"). Map the space-collapsed
# display name back to the placeable key so a finalized .xsq classifies identically to an
# instructions cache (else "Single Strand" chases fall into the "other" bucket, understating motion).
_CANON_BY_SQUEEZED: dict[str, str] = {et.replace(" ", ""): et for et in EFFECT_META}


def canon_name(name: str) -> str:
    """Normalize an effect name to its placeable/effect_meta form ('Single Strand' → 'SingleStrand');
    unknown names pass through unchanged."""
    if not name or name in EFFECT_META:
        return name
    return _CANON_BY_SQUEEZED.get(name.replace(" ", ""), name)

# -- effect families ----------------------------------------------------------------------------
# The analysis §1 fabric split, made authoritative here. MOTION comes from effect_meta (cell-able
# motion + Fire/Galaxy); the other families are the analysis's own lists. Priority is
# motion > punctuation > feature > bed > other, so an effect that could read two ways (Shockwave is
# a hit AND a feature) lands in the bucket the fabric argument cares about (punctuation).
MOTION_FAMILY: frozenset[str] = frozenset(MOTION_EFFECTS)
# punctuation/static fills — the share the analysis said to demote (§1: On, Twinkle, Strobe,
# Shockwave, Lightning, Shimmer). `On`/`Twinkle` alone are the inversion this change targets.
PUNCTUATION_FAMILY: frozenset[str] = frozenset(
    {"On", "Twinkle", "Strobe", "Shockwave", "Lightning", "Shimmer"})
# high-attention feature moments (catalog rule #4 set, minus Shockwave which is punctuation above).
FEATURE_FAMILY: frozenset[str] = frozenset({"Kaleidoscope", "Shader", "Fireworks", "Galaxy"})
# sustained wash/bed effects (long beds; `On` is punctuation above, not a bed here).
BED_FAMILY: frozenset[str] = frozenset({"Color Wash", "Plasma", "Fill", "Liquid", "Life"})

# The `source` tag vocabulary (Decision 8) — the transient per-layer provenance the measurement
# report reads. Kept here so both the report and the (report-only) tagging agree on the names.
SOURCE_TAGS: tuple[str, ...] = (
    "weave", "accents", "bed", "triggers", "flash", "generator", "vu", "composite")


def effect_family(effect_type: str) -> str:
    """The fabric family of an effect type (motion > punctuation > feature > bed > other).

    The name is canonicalized first, so an .xsq display name ('Single Strand') classifies the same
    as the placeable form ('SingleStrand')."""
    effect_type = canon_name(effect_type)
    if effect_type in MOTION_FAMILY:
        return "motion"
    if effect_type in PUNCTUATION_FAMILY:
        return "punctuation"
    if effect_type in FEATURE_FAMILY:
        return "feature"
    if effect_type in BED_FAMILY:
        return "bed"
    return "other"


# -- frozen community aggregates (§2.1 of docs/effects-layering-analysis.md, 2026-06-11) ---------
# 130,229 effects mined from the 17 community/vendor .xsq. Frozen so the comparison runs without the
# (machine-local, licensed) corpus. `stats_from_xsq` re-derives these on demand when the folder is
# reachable; these are the goalpost otherwise.
@dataclass(frozen=True)
class CommunityAggregates:
    motion_share: float = 0.58            # §1: continuous-motion effects
    punctuation_share: float = 0.31       # §1: On/Twinkle/Strobe/Shockwave/Lightning/Shimmer
    on_share: float = 0.03                # §1: `On` alone
    twinkle_share: float = 0.005          # §1: `Twinkle` alone (<1%)
    effects_per_min_typical: float = 1300.0   # §2: typical density (up to 3,200)
    effects_per_min_peak: float = 3200.0
    duration_p50_ms_lo: float = 300.0     # §2: median durations 0.3–0.9s across top types
    duration_p50_ms_hi: float = 900.0
    blend_brightness_share: float = 0.36  # §3: Brightness blend
    blend_layered_share: float = 0.23     # §3: Layered blend
    blend_mask_share: float = 0.16        # §3: masks/unmasks
    max_layer_depth: int = 19             # §5: hero rows stack to 19
    multi_layer_row_share: float = 0.22   # §5: 22% of rows multi-layer


COMMUNITY = CommunityAggregates()


# -- report shape -------------------------------------------------------------------------------
@dataclass
class SectionStats:
    """One section's fabric, so a whole-show number never hides the quiet-vs-peak contrast."""

    section_index: int
    intensity: float | None
    treatment: str | None        # improve-musicality Phase 2 treatment (full/feature/…); None pre-P2
    n: int                       # instructions in the section
    duration_s: float
    effects_per_min: float
    motion_share: float
    punctuation_share: float
    on_twinkle_share: float      # the inversion metric: On + Twinkle combined
    prop_row_effects_per_min: float | None = None    # raw × expansion for group-targeted rows

    @property
    def energetic(self) -> bool:
        """Energetic = intensity ≥ 0.5 OR a full/feature treatment — the sections the density
        targets are evaluated on. rest/gesture/pulse and quiet sections are exempt."""
        if self.treatment:
            return self.treatment in ("full", "feature")
        return (self.intensity or 0.0) >= 0.5


@dataclass
class FabricStats:
    """A show's effect fabric, in comparable form (see module docstring)."""

    total: int
    duration_s: float
    effects_per_min: float
    prop_row_effects_per_min: float | None
    per_prop_expansion: float | None
    share_by_family: dict[str, float]
    share_by_type: dict[str, float]           # top-N by count (see `top` arg)
    duration_p50_by_type: dict[str, float]    # median ms per type
    blend_mode_share: float
    transition_share: float
    value_curve_kinds: dict[str, float]       # {"brightness": .., "motion": .., "other": ..}
    layer_depth_hist: dict[int, int]
    per_section: list[SectionStats] = field(default_factory=list)
    source_by_type: dict[str, dict[str, int]] = field(default_factory=dict)   # {type: {source: n}}

    @property
    def energetic_sections(self) -> list[SectionStats]:
        return [s for s in self.per_section if s.energetic]


# -- value-curve classification for stats -------------------------------------------------------
# Motion params the community curves (§4: Rotation, Twist, Radius, Position, Movement, Speed);
# brightness is the loudness param we over-curve. Substring match so `E_VALUECURVE_Pinwheel_Twist`
# etc. all classify without a per-effect table.
_MOTION_VC_TOKENS = ("rotation", "twist", "radius", "position", "movement", "speed", "cycles",
                     "angle", "spacing", "swirl", "offset", "zoom", "width", "scale")
_BRIGHTNESS_VC_TOKENS = ("brightness",)


def _value_curve_kind(key: str) -> str:
    """'brightness' | 'motion' | 'other' for a value-curve setting key."""
    k = key.lower()
    if any(tok in k for tok in _BRIGHTNESS_VC_TOKENS):
        return "brightness"
    if any(tok in k for tok in _MOTION_VC_TOKENS):
        return "motion"
    return "other"


def _is_value_curve_key(key: str) -> bool:
    return "_VALUECURVE_" in key or key.endswith("VALUECURVE") or "VALUECURVE" in key


def _is_active_vc(value: str) -> bool:
    """A value-curve setting is only counted when it is Active=TRUE (an inactive VC is inert)."""
    return "ACTIVE=TRUE" in (value or "").upper()


# -- the core aggregation (shared by both input modes) ------------------------------------------
@dataclass
class _Row:
    """One placed effect, normalized to the fields the stats need (from either input mode)."""

    effect_type: str
    start_ms: int
    end_ms: int
    target: str
    layer: int
    section_index: int | None
    blend: bool                          # carries a T_CHOICE_LayerMethod
    transition: bool                     # carries an in/out transition type
    vc_kinds: list[str]                  # active value-curve kinds on this row
    source: str | None = None           # transient provenance (Decision 8); report-only

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


def _row_from_instruction(d: dict) -> _Row:
    """A `_Row` from an `EffectInstruction` dump (the instructions cache / golden fixture)."""
    extra = dict(d.get("extra_settings") or {})
    extra.update(d.get("knob_values") or {})
    vc_kinds = [_value_curve_kind(k) for k, v in extra.items()
                if _is_value_curve_key(k) and _is_active_vc(v)]
    return _Row(
        effect_type=canon_name(d.get("effect_type", "")),
        start_ms=int(d.get("start_ms", 0)), end_ms=int(d.get("end_ms", 0)),
        target=d.get("target", ""), layer=int(d.get("layer", 0) or 0),
        section_index=d.get("section_index"),
        blend=bool(extra.get("T_CHOICE_LayerMethod")),
        transition=bool(extra.get("T_CHOICE_In_Transition_Type")
                        or extra.get("T_CHOICE_Out_Transition_Type")),
        vc_kinds=vc_kinds,
        source=d.get("__source"))       # transient tag some callers stamp (never persisted)


def _stats(rows: list[_Row], duration_s: float, *, top: int,
           sections: dict[int, dict] | None, per_prop_expansion: float | None) -> FabricStats:
    """Build a `FabricStats` from normalized rows. `sections` maps section_index -> {intensity,
    treatment} so per-section stats can be energy/treatment bucketed."""
    n = len(rows)
    mins = (duration_s / 60.0) if duration_s > 0 else 0.0
    epm = (n / mins) if mins > 0 else 0.0

    fam_counts: Counter = Counter(effect_family(r.effect_type) for r in rows)
    type_counts: Counter = Counter(r.effect_type for r in rows)
    dur_by_type: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        dur_by_type[r.effect_type].append(r.duration_ms)

    share_by_family = {fam: fam_counts.get(fam, 0) / n for fam in
                       ("motion", "punctuation", "bed", "feature", "other")} if n else {}
    share_by_type = {t: c / n for t, c in type_counts.most_common(top)} if n else {}
    p50_by_type = {t: float(statistics.median(ds)) for t, ds in dur_by_type.items()}

    blend_share = (sum(1 for r in rows if r.blend) / n) if n else 0.0
    trans_share = (sum(1 for r in rows if r.transition) / n) if n else 0.0
    vc_counter: Counter = Counter(k for r in rows for k in r.vc_kinds)
    vc_total = sum(vc_counter.values())
    vc_kinds = {k: vc_counter.get(k, 0) / vc_total for k in ("brightness", "motion", "other")} \
        if vc_total else {}
    layer_hist = dict(Counter(r.layer for r in rows))

    # prop-row-equivalent density: group-targeted rows animate a whole SEM_ group; multiply their
    # count by the mean member count so we compare like-with-like against per-prop community rows.
    prop_epm: float | None = None
    if per_prop_expansion is not None and mins > 0:
        group_rows = sum(1 for r in rows if _is_group_target(r.target))
        prop_rows = group_rows * per_prop_expansion + (n - group_rows)
        prop_epm = prop_rows / mins

    # source-by-type breakdown (transient; only present when rows carry a __source tag)
    source_by_type: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r.source:
            source_by_type[r.effect_type][r.source] += 1
    source_by_type = {t: dict(s) for t, s in source_by_type.items()}

    per_section = _per_section(rows, sections or {}, per_prop_expansion)
    return FabricStats(
        total=n, duration_s=duration_s, effects_per_min=epm,
        prop_row_effects_per_min=prop_epm, per_prop_expansion=per_prop_expansion,
        share_by_family=share_by_family, share_by_type=share_by_type,
        duration_p50_by_type=p50_by_type, blend_mode_share=blend_share,
        transition_share=trans_share, value_curve_kinds=vc_kinds,
        layer_depth_hist=layer_hist, per_section=per_section, source_by_type=source_by_type)


def _per_section(rows: list[_Row], sections: dict[int, dict],
                 per_prop_expansion: float | None) -> list[SectionStats]:
    """Per-section stats, intensity/treatment bucketed. Section span → duration; if a section's
    metadata is absent, span is inferred from the rows' own start/end so effects/min still reports."""
    by_si: dict[int, list[_Row]] = defaultdict(list)
    for r in rows:
        if r.section_index is not None:
            by_si[r.section_index].append(r)
    out: list[SectionStats] = []
    for si in sorted(by_si):
        grp = by_si[si]
        meta = sections.get(si, {})
        if "start_ms" in meta and "end_ms" in meta:
            dur_s = max(0.0, (meta["end_ms"] - meta["start_ms"]) / 1000.0)
        else:                                        # fall back to the rows' own extent
            dur_s = max(0.0, (max(r.end_ms for r in grp) - min(r.start_ms for r in grp)) / 1000.0)
        mins = (dur_s / 60.0) if dur_s > 0 else 0.0
        m = len(grp)
        epm = (m / mins) if mins > 0 else 0.0
        motion = sum(1 for r in grp if effect_family(r.effect_type) == "motion") / m if m else 0.0
        punct = sum(1 for r in grp if effect_family(r.effect_type) == "punctuation") / m if m else 0.0
        on_tw = sum(1 for r in grp if r.effect_type in ("On", "Twinkle")) / m if m else 0.0
        prop_epm: float | None = None
        if per_prop_expansion is not None and mins > 0:
            gr = sum(1 for r in grp if _is_group_target(r.target))
            prop_epm = (gr * per_prop_expansion + (m - gr)) / mins
        out.append(SectionStats(
            section_index=si, intensity=meta.get("intensity"), treatment=meta.get("treatment"),
            n=m, duration_s=dur_s, effects_per_min=epm, motion_share=motion,
            punctuation_share=punct, on_twinkle_share=on_tw, prop_row_effects_per_min=prop_epm))
    return out


def _is_group_target(target: str) -> bool:
    """A group-canvas target (one effect animates every member prop) — the rows the prop-row
    normalization scales up. SEM_ groups are our group vocabulary; a bare model name is per-prop."""
    return target.startswith("SEM_")


# -- input mode A: instructions ------------------------------------------------------------------
def stats_from_instructions(instrs: list[dict], duration_s: float, *, top: int = 12,
                            sections: dict[int, dict] | None = None,
                            per_prop_expansion: float | None = None) -> FabricStats:
    """Fabric stats from a list of `EffectInstruction` dumps (the `instructions` cache / golden).

    `sections` maps section_index -> {"intensity": .., "treatment": .., "start_ms": .., "end_ms": ..}
    so per-section stats can be energy/treatment bucketed; omit it for a whole-show-only report.
    `per_prop_expansion` (from `expansion_from_rgbeffects`) turns on the prop-row-equivalent column.
    """
    rows = [_row_from_instruction(d) for d in instrs]
    return _stats(rows, duration_s, top=top, sections=sections,
                  per_prop_expansion=per_prop_expansion)


def stats_from_effect_instructions(instrs, duration_s: float, *, top: int = 12,
                                   sections: dict[int, dict] | None = None,
                                   per_prop_expansion: float | None = None) -> FabricStats:
    """Fabric stats from live `EffectInstruction` OBJECTS (not dumps), so the transient `source`
    provenance (excluded from `model_dump`) is read off the model for the per-type-per-source
    breakdown. Used when measuring an in-process run; the on-disk instructions cache carries no
    source (by design), so `stats_from_instructions` over the cache reports an empty source table."""
    dumped: list[dict] = []
    for ins in instrs:
        d = ins.model_dump()
        src = getattr(ins, "source", None)
        if src:
            d["__source"] = src                # a transient key `_row_from_instruction` reads
        dumped.append(d)
    return stats_from_instructions(dumped, duration_s, top=top, sections=sections,
                                   per_prop_expansion=per_prop_expansion)


# -- input mode B: a finalized .xsq --------------------------------------------------------------
def _row_from_xsq_effect(name: str, start_ms: int, end_ms: int, target: str, layer: int,
                         settings: str) -> _Row:
    from xlights_core.knowledge.settings import parse_settings
    pairs = parse_settings(settings)
    d = dict(pairs)
    vc_kinds = [_value_curve_kind(k) for k, v in pairs
                if _is_value_curve_key(k) and _is_active_vc(v)]
    return _Row(
        effect_type=canon_name(name), start_ms=start_ms, end_ms=end_ms, target=target, layer=layer,
        section_index=None,
        blend=bool(d.get("T_CHOICE_LayerMethod")),
        transition=bool(d.get("T_CHOICE_In_Transition_Type")
                        or d.get("T_CHOICE_Out_Transition_Type")),
        vc_kinds=vc_kinds)


def stats_from_xsq(path: str | Path, *, top: int = 12,
                   per_prop_expansion: float | None = None) -> FabricStats:
    """Fabric stats from a finalized `.xsq` (a community show OR our own output), parsed with
    ElementTree — so both sides of the comparison measure identically, no xLights needed.

    The `.xsq` layout: `<EffectDB>` holds settings strings (a placed `<Effect ref="N">` indexes
    into it); placed effects live under `<ElementEffects><Element type="model" name="TARGET">
    <EffectLayer><Effect ref name startTime endTime>`. Duration = (last endTime − first startTime)
    across all placed effects.
    """
    root = ET.parse(Path(path)).getroot()
    edb = root.find("EffectDB")
    settings_db = [(e.text or "").strip() for e in edb.findall("Effect")] if edb is not None else []

    rows: list[_Row] = []
    ee = root.find("ElementEffects")
    for el in (ee.findall("Element") if ee is not None else []):
        if el.get("type") != "model":                    # skip timing tracks
            continue
        target = el.get("name", "")
        for li, layer_el in enumerate(el.findall("EffectLayer")):
            for eff in layer_el.findall("Effect"):
                name = eff.get("name")
                if name is None:
                    continue
                try:
                    start = int(eff.get("startTime", "0"))
                    end = int(eff.get("endTime", "0"))
                except ValueError:
                    continue
                ref = eff.get("ref")
                settings = ""
                if ref is not None and ref.isdigit() and 0 <= int(ref) < len(settings_db):
                    settings = settings_db[int(ref)]
                rows.append(_row_from_xsq_effect(name, start, end, target, li, settings))

    if rows:
        span_ms = max(r.end_ms for r in rows) - min(r.start_ms for r in rows)
        duration_s = max(0.0, span_ms / 1000.0)
    else:
        duration_s = 0.0
    return _stats(rows, duration_s, top=top, sections=None,
                  per_prop_expansion=per_prop_expansion)


# -- prop-row expansion from the layout ---------------------------------------------------------
def expansion_from_rgbeffects(rgb_path: str | Path,
                              targeted_groups: set[str] | None = None) -> float | None:
    """Mean member-count of the SEM_ groups we actually target, from `rgbeffects.xml` modelGroups.

    Reuses the same modelGroups the layout parsing keys off. `targeted_groups` restricts the mean to
    the groups a show actually used (the honest expansion); None averages all SEM_ groups. Returns
    None when membership can't be resolved (the prop-row column is then reported absent)."""
    try:
        root = ET.parse(Path(rgb_path)).getroot()
    except Exception:  # noqa: BLE001 — best-effort; absence → null column
        return None
    mg = root.find("modelGroups")
    if mg is None:
        return None
    counts: list[int] = []
    for el in mg.findall("modelGroup"):
        name = el.get("name", "")
        if not name.startswith("SEM_"):
            continue
        if targeted_groups is not None and name not in targeted_groups:
            continue
        members = [m for m in (el.get("models", "") or "").split(",") if m.strip()]
        if members:
            counts.append(len(members))
    if not counts:
        return None
    return sum(counts) / len(counts)


# -- report rendering ---------------------------------------------------------------------------
def render_report(stats: FabricStats, *, title: str = "fabric") -> str:
    """A compact text table comparing `stats` against the frozen community aggregates."""
    lines: list[str] = [f"== {title} =="]
    lines.append(f"total: {stats.total} effects over {stats.duration_s:.1f}s  "
                 f"= {stats.effects_per_min:.0f} effects/min "
                 f"(community typical {COMMUNITY.effects_per_min_typical:.0f})")
    if stats.prop_row_effects_per_min is not None:
        lines.append(f"prop-row-equivalent: {stats.prop_row_effects_per_min:.0f}/min "
                     f"(×{stats.per_prop_expansion:.1f} expansion)")
    fam = stats.share_by_family
    lines.append(f"family: motion {fam.get('motion', 0):.0%} (community {COMMUNITY.motion_share:.0%})"
                 f"  punctuation {fam.get('punctuation', 0):.0%} "
                 f"(community {COMMUNITY.punctuation_share:.0%})"
                 f"  bed {fam.get('bed', 0):.0%}  feature {fam.get('feature', 0):.0%}"
                 f"  other {fam.get('other', 0):.0%}")
    top_types = ", ".join(f"{t} {s:.0%}" for t, s in stats.share_by_type.items())
    lines.append(f"by type: {top_types}")
    on_tw = stats.share_by_type.get("On", 0.0) + stats.share_by_type.get("Twinkle", 0.0)
    lines.append(f"On+Twinkle: {on_tw:.0%} "
                 f"(community {COMMUNITY.on_share + COMMUNITY.twinkle_share:.0%})")
    lines.append(f"blend-mode share: {stats.blend_mode_share:.0%} "
                 f"(community brightness {COMMUNITY.blend_brightness_share:.0%})"
                 f"  transition share: {stats.transition_share:.0%}")
    if stats.value_curve_kinds:
        vc = "  ".join(f"{k} {v:.0%}" for k, v in stats.value_curve_kinds.items())
        lines.append(f"value curves: {vc}  (community shapes MOTION, we over-shape brightness)")
    depth = stats.layer_depth_hist
    lines.append(f"layer depth: max {max(depth) if depth else 0} "
                 f"(community {COMMUNITY.max_layer_depth})  hist {dict(sorted(depth.items()))}")
    if stats.per_section:
        lines.append("per section:")
        for s in stats.per_section:
            tag = f" [{s.treatment}]" if s.treatment else ""
            flag = "  ENERGETIC" if s.energetic else ""
            lines.append(
                f"  §{s.section_index} i={s.intensity if s.intensity is not None else '?'}{tag}: "
                f"{s.n} eff, {s.effects_per_min:.0f}/min, motion {s.motion_share:.0%}, "
                f"On+Tw {s.on_twinkle_share:.0%}{flag}")
    if stats.source_by_type:
        lines.append("source by type:")
        for t in sorted(stats.source_by_type):
            srcs = ", ".join(f"{s}:{n}" for s, n in sorted(stats.source_by_type[t].items()))
            lines.append(f"  {t}: {srcs}")
    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------------------------
def _load_sections_from_show_plan(path: Path) -> dict[int, dict]:
    """section_index -> {intensity, treatment, start_ms, end_ms} from a cached show_plan.json."""
    try:
        doc = json.loads(path.read_text())
    except Exception:  # noqa: BLE001
        return {}
    secs = doc.get("sections") or []
    return {i: {"intensity": s.get("intensity"), "treatment": s.get("treatment", "") or None,
                "start_ms": s.get("start_ms"), "end_ms": s.get("end_ms")}
            for i, s in enumerate(secs)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Measure a show's effect fabric.")
    ap.add_argument("input", nargs="?", help="an instructions.json cache OR a finalized .xsq")
    ap.add_argument("--golden", action="store_true",
                    help="measure tests/fixtures/golden_instructions.json")
    ap.add_argument("--duration-s", type=float, default=None,
                    help="song duration for effects/min (instructions mode; default from spans)")
    ap.add_argument("--show-plan", default=None,
                    help="a show_plan.json for per-section intensity/treatment (instructions mode)")
    ap.add_argument("--rgbeffects", default=None,
                    help="rgbeffects.xml for the prop-row-equivalent expansion")
    ap.add_argument("--top", type=int, default=12, help="top-N effect types in the by-type table")
    args = ap.parse_args(argv)

    expansion = expansion_from_rgbeffects(args.rgbeffects) if args.rgbeffects else None

    if args.golden or (args.input and args.input.endswith(".json")):
        path = (Path(__file__).resolve().parent.parent / "tests" / "fixtures"
                / "golden_instructions.json") if args.golden else Path(args.input)
        instrs = json.loads(path.read_text())
        sections = _load_sections_from_show_plan(Path(args.show_plan)) if args.show_plan else None
        duration_s = args.duration_s
        if duration_s is None:
            duration_s = max((int(d.get("end_ms", 0)) for d in instrs), default=0) / 1000.0
        stats = stats_from_instructions(instrs, duration_s, top=args.top, sections=sections,
                                        per_prop_expansion=expansion)
        title = path.name
    elif args.input and args.input.endswith(".xsq"):
        stats = stats_from_xsq(args.input, top=args.top, per_prop_expansion=expansion)
        title = Path(args.input).name
    else:
        ap.error("give an instructions.json / .xsq input, or --golden")
        return 2

    print(render_report(stats, title=title))
    return 0


if __name__ == "__main__":
    sys.exit(main())
