"""Curated trigger effects: deterministic "when X happens in the music, do Y" accents, defined
in the hand-editable `xlights-trigger-cookbook.md` and placed SPARINGLY over the woven show.

The cookbook (judgment, hand-authored) declares each trigger's effect/render/rarity/color; the
DETECTORS here (code) find the events from the analysis; the realizer turns them into placements.
Code owns timing + realization, the markdown owns the curation — same split as the guides.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from xlights_core.knowledge.colors import _brighten, _resolve, contrast_anchors
from xlights_core.knowledge.value_curves import brightness_setting

from ..agents.catalog import candidate_look_ids, placeable_effect_types
from ..show_plan import EffectInstruction
from .beats import _downsample, effect_palette
from .features import STEM_EFFECT, instrument_entrances
from .semantic_groups import ACCENT_GROUPS, HERO_GROUP, RHYTHM_POOL, WHOLE_HOUSE_GROUPS
from .tuning import PEAK_BAND, PEAK_FLOOR

log = logging.getLogger(__name__)

COLOR_WORDS = {"red", "green", "blue", "gold", "golden", "white", "silver", "purple", "violet",
               "pink", "orange", "amber", "yellow", "cyan", "teal", "crimson", "scarlet"}
DRUM_PROMINENT_SHARE = 0.22  # a section counts as drum-prominent at/above this drum energy share
SPARSE_MAX_INTENSITY = 0.5   # 'sparse_beat' = a strong beat with little else (low overall energy)
EVENT_MS = 220               # a point trigger's pop/flash duration (short — a drum hit)
POP_BRIGHTNESS = 320         # 0–400 scale (100=normal): a pop is a bright FLASH, not a tint

# A radiating Shockwave that reads on an accent prop — the user's hand-authored settings
# (snowflakes/spinners, 0:30–0:44): a modest ring expanding from center. Overrides the look base.
SHOCKWAVE_SETTINGS = {
    "E_NOTEBOOK_Shockwave": "Position", "E_CHECKBOX_Shockwave_Blend_Edges": "1",
    "E_CHECKBOX_Shockwave_Scale": "1", "E_SLIDER_Shockwave_Accel": "0",
    "E_SLIDER_Shockwave_CenterX": "50", "E_SLIDER_Shockwave_CenterY": "50",
    "E_SLIDER_Shockwave_Cycles": "1", "E_SLIDER_Shockwave_Start_Radius": "1",
    "E_SLIDER_Shockwave_End_Radius": "76", "E_SLIDER_Shockwave_Start_Width": "5",
    "E_SLIDER_Shockwave_End_Width": "43",
}
GROUP_POOLS = {"rhythm": RHYTHM_POOL, "accents": ACCENT_GROUPS, "focal": (HERO_GROUP,)}


@dataclass
class TriggerEvent:
    time_ms: int
    magnitude: float = 1.0           # 0–1, for top:<pct> filtering
    group: str | None = None         # explicit target (else realizer rotates the rhythm pool)
    color: str | None = None         # explicit color (lyric word); else the spec's color rule
    end_ms: int | None = None        # set for span triggers (a guitar solo); else a point hit
    stem: str | None = None


@dataclass
class TriggerSpec:
    name: str
    detector: str = ""
    effect: str = "On"
    render: str = "per_model"
    sections: str = "any"
    select: str = "all"
    density: str = "per_onset"
    magnitude: str = "any"
    color: str = "section"
    direction: str = "none"
    groups: str = "rhythm"           # which per_model pool: rhythm | accents | focal
    stem: str = "drums"              # which instrument stem drives stem_onsets / stem_prominent
    enabled: bool = True


# -- cookbook parse (best-effort; a bad block is skipped, never fatal) ----------

def parse_cookbook(text: str) -> list[TriggerSpec]:
    specs: list[TriggerSpec] = []
    block: dict | None = None
    name = ""
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            if block is not None:
                specs.append(_spec_from(name, block))
            name, block = line[3:].strip(), {}
        elif block is not None and line.lstrip().startswith("- ") and ":" in line:
            k, v = line.lstrip()[2:].split(":", 1)
            block[k.strip().lower()] = v.strip()
    if block is not None:
        specs.append(_spec_from(name, block))
    return [s for s in specs if s.detector]


def _spec_from(name: str, b: dict) -> TriggerSpec:
    return TriggerSpec(
        name=name, detector=b.get("detector", ""), effect=b.get("effect", "On"),
        render=b.get("render", "per_model"), sections=b.get("sections", "any"),
        select=b.get("select", "all"), density=b.get("density", "per_onset"),
        magnitude=b.get("magnitude", "any"), color=b.get("color", "section"),
        direction=b.get("direction", "none"), groups=b.get("groups", "rhythm"),
        stem=b.get("stem", "drums"),
        enabled=b.get("enabled", "true").lower() != "false")


# -- magnitude (small vs big hits, from the stem's own energy at the onset) -----

def energy_at(arc, t_s: float, peak: float | None = None) -> float:
    """The stem's RMS at time `t_s`, normalized to its peak (0–1). Nearest sample — `energy_arc`
    is ~0.5s-spaced, fine for small/mid/big bucketing."""
    if not arc:
        return 0.0
    pk = peak if peak is not None else (max((p.rms for p in arc), default=0.0) or 1.0)
    nearest = min(arc, key=lambda p: abs(p.time - t_s))
    return max(0.0, min(1.0, nearest.rms / pk))


def _stem(sa, name: str):
    return next((f for f in (getattr(sa, "stems", None) or []) if f.stem == name), None)


# -- detectors: analysis -> [TriggerEvent] -------------------------------------

def _guitar_solo(sa, sections, spec=None) -> list[TriggerEvent]:
    """Sections where guitar dominates and vocals are absent — the soloist's window."""
    out: list[TriggerEvent] = []
    for inst in (getattr(sa, "section_instrumentation", None) or []):
        sh = inst.shares or {}
        gtr = sh.get("guitar", 0.0)
        if gtr >= 0.30 and gtr >= sh.get("vocals", 0.0) * 1.5 and gtr == max(sh.values(), default=0):
            out.append(TriggerEvent(time_ms=inst.start_ms, end_ms=inst.end_ms,
                                    magnitude=gtr, group=HERO_GROUP, stem="guitar"))
    return out


def _onsets_for(sa, name: str) -> list[TriggerEvent]:
    """Every onset of stem `name`, each carrying that stem's normalized energy as magnitude."""
    f = _stem(sa, name)
    if not f or not f.onsets:
        return []
    peak = max((p.rms for p in f.energy_arc), default=0.0) or 1.0
    return [TriggerEvent(time_ms=int(t * 1000), magnitude=energy_at(f.energy_arc, t, peak),
                         stem=name) for t in f.onsets]


def _stem_onsets(sa, sections, spec=None) -> list[TriggerEvent]:
    """Onsets of the trigger's chosen stem (`spec.stem`, default drums) — a melodic line (piano,
    bass, …) walking the props, not only the beat."""
    return _onsets_for(sa, (getattr(spec, "stem", None) or "drums"))


def _drum_onsets(sa, sections, spec=None) -> list[TriggerEvent]:
    """Back-compat name: stem_onsets forced to drums regardless of the spec's stem."""
    return _onsets_for(sa, "drums")


def _lyric_color(sa, sections, spec=None) -> list[TriggerEvent]:
    """A color WORD in the lyric → an event at that word's time (word timing if persisted, else
    the line start), carrying the color."""
    lyr = getattr(sa, "lyrics", None) or {}
    out: list[TriggerEvent] = []
    for line in lyr.get("lines", []):
        words = line.get("words") or []
        for w in words:
            tok = (w.get("word") or "").strip(".,!?'\"").lower()
            if tok in COLOR_WORDS and _resolve(tok):
                out.append(TriggerEvent(time_ms=int(w["start"] * 1000), color=tok))
        if not words:                                # line-precise fallback (no word timing)
            for tok in line.get("text", "").lower().replace(",", " ").split():
                tok = tok.strip(".,!?'\"")
                if tok in COLOR_WORDS and _resolve(tok):
                    out.append(TriggerEvent(time_ms=int(line["start"] * 1000), color=tok))
                    break
    return out


def _instrument_entrance(sa, sections, spec=None) -> list[TriggerEvent]:
    """The folded-in entrance feature: a stem surging in → ride its onsets on the focal prop."""
    onsets_by_stem = {f.stem: [int(t * 1000) for t in (f.onsets or [])]
                      for f in (getattr(sa, "stems", None) or [])}
    out: list[TriggerEvent] = []
    for t_ms, stem in instrument_entrances(sa):
        for t in onsets_by_stem.get(stem, []):
            if t_ms <= t < t_ms + 10_000:
                out.append(TriggerEvent(time_ms=t, group=HERO_GROUP, stem=stem))
    return out


# A "big moment" is not its own detector — it's `drum_onsets` gated to top-magnitude hits
# (whole-house render, low top:<pct>): naturally rare, length-proportional, capped per section.
DETECTORS = {"guitar_solo": _guitar_solo, "drum_onsets": _drum_onsets,
             "stem_onsets": _stem_onsets,
             "lyric_color": _lyric_color, "instrument_entrance": _instrument_entrance}


# -- section helpers -----------------------------------------------------------

def _section_index(sections, t_ms: int) -> int | None:
    for i, s in enumerate(sections or []):
        if s.start_ms <= t_ms < s.end_ms:
            return i
    return None


def _eligible_sections(spec: TriggerSpec, sa, sections) -> list[int]:
    n = len(sections or [])
    if spec.sections == "any":
        elig = list(range(n))
    elif spec.sections == "peak":
        # same definition as beats.peak_sections — the tuning dials, not local copies
        peak = max((getattr(s, "intensity", 0.0) or 0.0 for s in sections), default=0.0)
        elig = [i for i, s in enumerate(sections)
                if peak >= PEAK_FLOOR and (getattr(s, "intensity", 0.0) or 0.0) >= peak - PEAK_BAND]
    elif spec.sections in ("drum_prominent", "sparse_beat", "stem_prominent"):
        # which stem must be prominent: the chosen stem for stem_prominent, else drums.
        stem = (spec.stem or "drums") if spec.sections == "stem_prominent" else "drums"
        elig = []
        for i, s in enumerate(sections):
            inst = next((x for x in (getattr(sa, "section_instrumentation", None) or [])
                         if x.start_ms < s.end_ms and x.end_ms > s.start_ms), None)
            prominent = inst and (inst.shares or {}).get(stem, 0.0) >= DRUM_PROMINENT_SHARE
            # sparse_beat = a STRONG beat with little else going on (the user's intro shockwaves):
            # prominent AND low overall energy. drum_prominent / stem_prominent ignore intensity.
            if prominent and (spec.sections != "sparse_beat"
                              or (getattr(s, "intensity", 1.0) or 0.0) <= SPARSE_MAX_INTENSITY):
                elig.append(i)
    elif spec.sections == "has_guitar_solo":
        solos = {_section_index(sections, e.time_ms) for e in _guitar_solo(sa, sections, spec)}
        elig = sorted(i for i in solos if i is not None)
    else:
        elig = list(range(n))
    return elig


def _select(spec: TriggerSpec, eligible: list[int], offset: int, sections) -> set[int]:
    """`rotate` keeps a sparse subset so not every section features the accent — but the subset is
    the most ENERGETIC eligible sections (drum pops belong on the drum-driven moments, not the
    quiet ones), with the offset rotating the tie-break so different triggers spread out."""
    if spec.select != "rotate" or len(eligible) <= 1:
        return set(eligible)
    ranked = sorted(eligible,
                    key=lambda i: (-(getattr(sections[i], "intensity", 0.0) or 0.0), (i + offset) % 2))
    keep = max(1, (len(eligible) + 1) // 2)              # the top ~half by energy
    return set(ranked[:keep])


def _mag_keep(spec: TriggerSpec, events: list[TriggerEvent]) -> list[TriggerEvent]:
    if spec.magnitude.startswith("top:") and events:
        try:
            pct = float(spec.magnitude.split(":", 1)[1])
        except ValueError:
            return events
        keep = max(1, round(len(events) * pct / 100))
        return sorted(events, key=lambda e: -e.magnitude)[:keep]
    return events


# -- realize -------------------------------------------------------------------

def _look(effect: str, stem: str | None) -> tuple[str, str] | None:
    eff = STEM_EFFECT.get(stem or "", "Twinkle") if effect == "stem_default" else effect
    if eff not in placeable_effect_types():
        return None
    looks = candidate_look_ids(eff)
    return (eff, looks[0]) if looks else None


def _shockwave_settings(effect: str, direction: str, idx: int) -> dict[str, str]:
    """The user's radiating-Shockwave settings; `direction` in/out (or alternate) just swaps the
    radius endpoints so the ring expands or contracts."""
    if effect != "Shockwave":
        return {}
    s = dict(SHOCKWAVE_SETTINGS)
    if direction and direction != "none":
        d = ("out", "in")[idx % 2] if direction == "alternate" else direction
        if d == "in":                                # collapse inward instead of expanding
            s["E_SLIDER_Shockwave_Start_Radius"], s["E_SLIDER_Shockwave_End_Radius"] = \
                s["E_SLIDER_Shockwave_End_Radius"], s["E_SLIDER_Shockwave_Start_Radius"]
    return s


def realize_triggers(specs: list[TriggerSpec], sa, sections, available_groups: list[str]
                     ) -> list[EffectInstruction]:
    avail = set(available_groups or [])
    whole = next((g for g in WHOLE_HOUSE_GROUPS if g in avail), None)
    out: list[EffectInstruction] = []
    for offset, spec in enumerate(s for s in specs if s.enabled):
        pool = [g for g in GROUP_POOLS.get(spec.groups, RHYTHM_POOL) if g in avail] \
            or [g for g in RHYTHM_POOL if g in avail] or list(available_groups or [])
        det = DETECTORS.get(spec.detector)
        if det is None:
            log.info("trigger %r: unknown detector %r — skipped", spec.name, spec.detector)
            continue
        try:
            events = _mag_keep(spec, det(sa, sections, spec))
        except Exception as exc:  # noqa: BLE001 — a detector failure never sinks the run
            log.warning("trigger %r detector failed: %s", spec.name, exc)
            from ..degradations import note                 # aggregate into the run summary
            note("generate:triggers", f"{spec.name}: {exc}", stage="generate",
                 level=logging.DEBUG)                        # DEBUG: log.warning above is the detail
            continue
        selected = _select(spec, _eligible_sections(spec, sa, sections), offset, sections)
        # group events by their section, keep only selected sections, cap density
        by_sec: dict[int, list[TriggerEvent]] = {}
        for ev in events:
            si = _section_index(sections, ev.time_ms)
            if si is not None and si in selected:
                by_sec.setdefault(si, []).append(ev)
        for si, evs in by_sec.items():
            sec = sections[si]
            cap = None if spec.density == "per_onset" else _int(spec.density)
            evs = _downsample(sorted(evs, key=lambda e: e.time_ms), cap) if cap else evs
            anchors = contrast_anchors(getattr(sec, "palette", []) or [])
            for i, ev in enumerate(evs):
                placed = _one(spec, ev, i, sec, si, pool, whole, anchors)
                if placed:
                    out.append(placed)
    return out


def _one(spec, ev, idx, sec, si, pool, whole, anchors) -> EffectInstruction | None:
    lk = _look(spec.effect, ev.stem)
    if not lk:
        return None
    eff, look = lk
    if spec.render == "whole_house":
        target, style = (ev.group or whole), "Per Preview"
    else:
        target = ev.group or (pool[idx % len(pool)] if pool else None)
        style = "Per Model Default"
    if not target:
        return None
    if spec.color == "lyric" and ev.color:
        colors = [ev.color]
    elif spec.color == "anchor_alternate":
        colors = [anchors[idx % 2]]
    elif spec.color.startswith("fixed:"):
        colors = [spec.color.split(":", 1)[1]]
    else:                                            # "section"
        colors = effect_palette(list(getattr(sec, "palette", []) or []), eff, idx)
    start = ev.time_ms
    end = ev.end_ms or (start + EVENT_MS)
    extra = _shockwave_settings(eff, spec.direction, idx)
    # A POP IS A FLASH: brighten the hue (a hue-distant anchor can be near-black, e.g. navy
    # luminance 10 — invisible) and boost brightness so the accent reads as a punch of light,
    # not the prop blinking off. Point accents only (spans like a guitar solo stay as-is).
    if ev.end_ms is None:
        colors = [_brighten(_resolve(c) or c) or c for c in colors]
        extra.update(brightness_setting(POP_BRIGHTNESS))
    # section_index=None so the refine loop's replace_section (which strips a section's tagged
    # instructions) does NOT delete these — triggers are deterministic global accents, not
    # per-section LLM output to be revised. (Same pattern the old instrument_feature_layer used.)
    return EffectInstruction(target=target, effect_type=eff, look_id=look,
                             palette_colors=colors, render_style=style, extra_settings=extra,
                             start_ms=int(start), end_ms=int(end), section_index=None,
                             on_top=True)            # punch through the fabric (opaque, top layer)


def _int(s: str) -> int | None:
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


# -- entry point ---------------------------------------------------------------

def place_triggers(sa, sections, available_groups: list[str], cookbook_text: str
                   ) -> list[EffectInstruction]:
    """Parse the cookbook + place all enabled triggers. Empty/absent cookbook → []."""
    specs = parse_cookbook(cookbook_text)
    if not specs:
        return []
    return realize_triggers(specs, sa, sections, available_groups)
