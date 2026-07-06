"""Placement-rules QA (objective) — the effects catalog §11 rules that are 'normative for
automated sequencing', detected deterministically. The Generator stays the author: violations
become section-scoped findings the refine loop regenerates (plus two hard duration caps the
catalog states verbatim).

Enforced here: #2 texture-on-linear affinity, #3 energy bands (±1), #4 one-feature-per-moment,
#7 Strobe/Shimmer hard caps (via `clamp_hard_caps`).
"""

from __future__ import annotations

from typing import Any

from ..refine import Finding
# Per-effect metadata (energy bands, duration classes, the motion-fabric set) lives in the
# consolidated table (pipeline/effect_meta.py); re-exported here so QA callers keep the old names.
# Catalog §2 energy bands (min, max) — only effects we can place; absent = unconstrained.
# Duration classes (catalog §2.1 v0.3): a HIT is ≤1-bar punctuation; a PHRASE is a bounded gesture;
# CELL-ABLE motion effects default to 1–2 bar cells; explicit long beds (ColorWash/Plasma on bed
# groups) exempt. MOTION_EFFECTS is the woven continuous-motion set (~58% community vs ~16% ours).
from ..pipeline.effect_meta import (  # re-export: tests + external callers (weave/beats historical paths)
    DURATION_CELLABLE,  # noqa: F401 — re-export
    DURATION_HIT,  # noqa: F401 — re-export
    DURATION_PHRASE,  # noqa: F401 — re-export
    ENERGY_BAND,
    MOTION_EFFECTS,
)
# Bar-math + motion-share dials moved to the tuning module's refine-control / behavior sections.
from ..pipeline.tuning import MOTION_SHARE_MIN  # re-export

_BED_TARGET_PREFIXES = ("SEM_BAND_",)                  # band rows MAY hold long beds
_BED_TARGETS = {"SEM_ALL", "SEM_YARD"}                 # exact — NOT SEM_ALL_LESS_* (those weave)

MOTION_SHARE_INTENSITY = 0.5
# improve-musicality Phase 2 treatments that are deliberately still — exempt from the motion-share
# advisory even at high intensity (their sparseness is intent, not a fabric regression).
_QUIET_TREATMENTS = frozenset({"rest", "gesture"})

TEXTURE = {"Plasma", "Fire", "Liquid", "Life"}                   # rule #2: never on linear props
FEATURES = {"Kaleidoscope", "Shader", "Shockwave", "Fireworks"}  # rule #4: one at a time
_LINEAR_PREFIXES = ("SEM_ARCHES", "SEM_OUTLINE", "SEM_CANES", "SEM_ICICLES", "SEM_PATH")

STROBE_CAP_MS = 1000          # rule #7, verbatim: "Strobe ≤ ~1s per instance"
SHIMMER_BARS = 2              # rule #7: "Shimmer ≤ 2 bars"
_PENALTY = 8                  # objective points per violation


_LINEAR_RES = {"LINEAR_HIGH", "LINEAR_LOW"}


def _target_res(target: str, manifest) -> set[str] | None:
    """The capability res classes of a target from the manifest: a prop's own class, or the UNION
    of member classes for a group. `None` when the manifest doesn't describe the target."""
    if manifest is None:
        return None
    props = {p.id: p for p in getattr(manifest, "props", None) or []}
    p = props.get(target)
    if p is not None:
        return {p.res}
    gr = (getattr(manifest, "groups", None) or {}).get(target)
    if gr is not None:
        classes = {props[m].res for m in gr.members if m in props}
        return classes or None
    return None


def _is_linear(target: str, manifest=None) -> bool:
    """Manifest-derived when a manifest is loaded (res ⊆ linear classes → the whole target reads as
    a linear prop); otherwise the legacy name-prefix fallback so QA is unchanged from today."""
    res = _target_res(target, manifest)
    if res is not None:
        return bool(res) and res <= _LINEAR_RES
    return target.startswith(_LINEAR_PREFIXES)


def _section_band(intensity: float) -> int:
    return 1 + round(4 * max(0.0, min(1.0, intensity or 0.0)))


def evaluate(instructions, plan, manifest=None) -> tuple[int, list[Finding]]:
    sections = list(getattr(plan, "sections", None) or []) if plan else []
    findings: list[Finding] = []

    features: list = []
    for ins in instructions or []:
        si = getattr(ins, "section_index", None)
        # #2 — texture on linear props (manifest-derived when loaded, prefix fallback otherwise)
        if ins.effect_type in TEXTURE and _is_linear(ins.target, manifest):
            findings.append(Finding(
                scope=f"section {si} / {ins.target}", severity="error", metric="rules",
                objective=True, section_index=si,
                detail=f"{ins.effect_type} (texture) on a linear prop group — reads as flicker, "
                       f"not texture (catalog rule #2)"))
        # #3 — energy band vs the section's energy (±1 allowed)
        band = ENERGY_BAND.get(ins.effect_type)
        if band and si is not None and 0 <= si < len(sections):
            sec_band = _section_band(getattr(sections[si], "intensity", 0.5))
            gap = max(band[0] - sec_band, sec_band - band[1], 0)
            if gap >= 2:
                findings.append(Finding(
                    scope=f"section {si} / {ins.target}", severity="error", metric="rules",
                    objective=True, section_index=si,
                    detail=f"{ins.effect_type} (energy {band[0]}–{band[1]}) in an energy-"
                           f"{sec_band} section — a defect, not a choice (catalog rule #3)"))
        if ins.effect_type in FEATURES:
            features.append(ins)
    # #4 — one high-attention feature MOMENT at a time. The same effect on many groups in the
    # same window is ONE gesture, so merge same-type overlapping spans into events first.
    events: list[tuple[int, int, str, Any]] = []      # (start, end, effect_type, representative ins)
    for etype in {x.effect_type for x in features}:
        spans = sorted(((x.start_ms, x.end_ms, x) for x in features if x.effect_type == etype),
                       key=lambda t: (t[0], t[1]))
        for st_, en_, x in spans:
            if events and events[-1][2] == etype and st_ < events[-1][1]:
                events[-1] = (events[-1][0], max(events[-1][1], en_), etype, events[-1][3])
            else:
                events.append((st_, en_, etype, x))
    events.sort(key=lambda e: (e[0], e[1]))
    # Sweep with a running max-end: a long feature must collide with EVERY later
    # overlapping event, not just its immediate neighbor in start order.
    open_end, open_type = None, None
    for st_, en_, etype, x in events:
        if open_end is not None and st_ < open_end:
            findings.append(Finding(
                scope=f"section {getattr(x, 'section_index', None)} / {x.target}",
                severity="error", metric="rules", objective=True,
                section_index=getattr(x, "section_index", None),
                detail=f"{etype} overlaps {open_type} — at most one high-attention "
                       f"feature at a time (catalog rule #4)"))
        if open_end is None or en_ > open_end:
            open_end, open_type = en_, etype
    score = max(0, 100 - _PENALTY * len(findings))      # advisories below do NOT gate the score
    # motion-share advisory: an energetic section that is mostly static/punctuation reads as
    # "pulses over a wash", not the community's woven-motion fabric.
    by_section: dict[int, list] = {}
    for ins in instructions or []:
        si = getattr(ins, "section_index", None)
        if si is not None:
            by_section.setdefault(si, []).append(ins)
    for si, group in sorted(by_section.items()):
        if not (0 <= si < len(sections)):
            continue
        if (getattr(sections[si], "intensity", 0.5) or 0.5) < MOTION_SHARE_INTENSITY:
            continue
        # treatment exemption (improve-musicality Phase 2, forward-compatible): a deliberately still
        # rest/gesture section is not a fabric regression, even if its intensity reads high.
        if (getattr(sections[si], "treatment", "") or "").lower() in _QUIET_TREATMENTS:
            continue
        share = sum(1 for x in group if x.effect_type in MOTION_EFFECTS) / len(group)
        if share < MOTION_SHARE_MIN:
            findings.append(Finding(
                scope=f"section {si}", severity="warn", metric="rules",
                objective=False, section_index=si,
                detail=f"motion-effect share {share:.0%} (< {MOTION_SHARE_MIN:.0%}) in an "
                       f"energetic section — mostly static/punctuation effects; weave motion "
                       f"cells (chases/spirals/ripples) instead (2026-07 re-measurement target "
                       f"≥ 45%; real shows clear it — docs/effects-layering-analysis-2026-07.md)"))
    return score, findings


def clamp_hard_caps(instructions, tempo_bpm: float | None) -> int:
    """Catalog rule #7 hard caps, enforced in place. Returns the number clamped."""
    bar_ms = (4 * 60000 / tempo_bpm) if tempo_bpm else 2000.0
    shimmer_cap = int(SHIMMER_BARS * bar_ms)
    n = 0
    for ins in instructions or []:
        cap = STROBE_CAP_MS if ins.effect_type == "Strobe" else \
              shimmer_cap if ins.effect_type == "Shimmer" else None
        if cap and ins.end_ms - ins.start_ms > cap:
            ins.end_ms = ins.start_ms + cap
            n += 1
    return n
