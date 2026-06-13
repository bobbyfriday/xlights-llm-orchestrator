"""Beat-aware accent layer: deterministic per-section rhythm + beat-synced accent placement.

Timing is code-owned (beats / the prominent stem's onsets from SongAnalysis); the creative
choices (which groups, which stem, what accent) come from the brief with sensible defaults. The
accents are a SECOND layer added over the section washes, chasing across the rhythm groups.
"""

from __future__ import annotations

import bisect

from xlights_core.knowledge.colors import contrast_anchors, expand_palette
from xlights_core.knowledge.value_curves import brightness_setting

from ..agents.catalog import candidate_look_ids, placeable_effect_types
from ..show_plan import EffectInstruction, SectionPlan

MAX_ACCENTS_PER_SECTION = 80       # hard upper bound (every-beat + downbeat hits stay under this)
ACCENT_MS = 250                    # short punctuation
# SEM_ semantic groups (xlights-layout-semantics-spec): the beat chase sweeps L→C→R spatially,
# the hero onset layer rides the focal props, flashes hit the whole display.
RHYTHM_GROUPS = ("SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT")
RHYTHM_POOL = ("SEM_ARCHES", "SEM_CANES", "SEM_MINITREES")    # the guide's rhythm cells (call-and-response)
ACCENT_GROUPS = ("SEM_SNOWFLAKES", "SEM_SPINNERS")            # sparkle props: fire on hits, dark otherwise
HERO_GROUP = "SEM_FOCAL"
FULL_DISPLAY = "SEM_ALL"
BEATS_PER_BAR = 4                  # derived 4/4 (downbeat = every 4th beat)
HERO_MAX_ONSETS = 40               # hero hits scale with intensity, up to this (keeps it tasteful)


WASH_MIN_B, WASH_MAX_B = 50.0, 180.0     # 0–400 brightness scale (100=normal): dim quiet, boost loud
MIN_LIT_GROUPS = 2                       # a section is never fully blacked out by the coverage rule


def wash_brightness(intensity: float) -> float:
    """Section wash brightness level (0–400 scale) keyed to energy."""
    i = max(0.0, min(1.0, intensity or 0.0))
    return WASH_MIN_B + (WASH_MAX_B - WASH_MIN_B) * i


SIMPLE_COLOR = {"On", "Off", "Strobe", "Lightning", "Fill"}   # 1-2 colors read best
PALETTE_DEPTH = 5                                             # expanded section palette size


def effect_palette(section_palette: list[str], effect_type: str, index: int) -> list[str]:
    """Per-effect colors from the section family: multi-color effects get the FULL expanded
    palette; simple effects get a rotated pair — so concurrent effects differ instead of being
    identical, and Plasma/Spirals/Bars get enough colors to render as intended."""
    full = expand_palette(section_palette, PALETTE_DEPTH)
    if not full:
        return list(section_palette)
    rot = full[index % len(full):] + full[:index % len(full)]
    return rot[:2] if effect_type in SIMPLE_COLOR else rot


# Each effect's REAL speed/cycles/movement parameter + corpus-observed range.
# The old blanket `E_SLIDER_<Effect>_Speed` was a real key for only a few effects — the
# intensity→speed feature silently no-op'd elsewhere AND xLights logged ApplySetting errors
# on every UI selection. Effects with no speed concept emit nothing.
# (key, lo, hi, fmt)  fmt: "int" slider | "f1" one-decimal textctrl
SPEED_KEYS: dict[str, tuple[str, float, float, str]] = {
    "Meteors":     ("E_SLIDER_Meteors_Speed", 10, 45, "int"),
    "Pinwheel":    ("E_SLIDER_Pinwheel_Speed", 5, 20, "int"),
    "Butterfly":   ("E_SLIDER_Butterfly_Speed", 8, 40, "int"),
    "Marquee":     ("E_SLIDER_Marquee_Speed", 1, 8, "int"),
    "Plasma":      ("E_SLIDER_Plasma_Speed", 70, 90, "int"),
    "Snowflakes":  ("E_SLIDER_Snowflakes_Speed", 10, 25, "int"),
    "Snowstorm":   ("E_SLIDER_Snowstorm_Speed", 10, 30, "int"),
    "Circles":     ("E_SLIDER_Circles_Speed", 5, 25, "int"),
    "Tree":        ("E_SLIDER_Tree_Speed", 5, 20, "int"),
    "Warp":        ("E_SLIDER_Warp_Speed", 5, 30, "int"),
    "Color Wash":  ("E_TEXTCTRL_ColorWash_Cycles", 1, 6, "f1"),
    # "On" deliberately ABSENT: On_Cycles would make steady beds PULSE — pulses are the
    # beat layer's job; beds stay flat.
    "Bars":        ("E_TEXTCTRL_Bars_Cycles", 0.5, 4, "f1"),
    "Garlands":    ("E_TEXTCTRL_Garlands_Cycles", 1, 4, "f1"),
    "Ripple":      ("E_TEXTCTRL_Ripple_Cycles", 1, 8, "f1"),
    "Shimmer":     ("E_TEXTCTRL_Shimmer_Cycles", 4, 12, "f1"),
    "Wave":        ("E_TEXTCTRL_Wave_Speed", 5, 35, "f1"),
    "Curtain":     ("E_TEXTCTRL_Curtain_Speed", 0.5, 4, "f1"),
    "Spirals":     ("E_TEXTCTRL_Spirals_Movement", 0.5, 4, "f1"),
}


def effect_speed_setting(effect_type: str, intensity: float) -> dict[str, str]:
    """The effect's REAL speed parameter scaled to energy; `{}` when it has none."""
    spec = SPEED_KEYS.get(effect_type)
    if spec is None:
        return {}
    key, lo, hi, fmt = spec
    i = max(0.0, min(1.0, intensity or 0.0))
    v = lo + (hi - lo) * i
    return {key: str(round(v)) if fmt == "int" else f"{v:.1f}"}


ESCALATION_BOOST = 0.25                   # how much a final recurrence can lift effective intensity


def escalation_level(section_index: int, repetition_map: dict | None) -> float:
    """0 for the first occurrence of a recurring section → 1 for the last; 0 if it doesn't recur."""
    for indices in (repetition_map or {}).values():
        if section_index in indices and len(indices) > 1:
            return sorted(indices).index(section_index) / (len(indices) - 1)
    return 0.0


def effective_intensity(intensity: float, section_index: int, repetition_map: dict | None) -> float:
    """Section intensity lifted by its escalation level so later recurrences build."""
    base = max(0.0, min(1.0, intensity or 0.0))
    return min(1.0, base + ESCALATION_BOOST * escalation_level(section_index, repetition_map))


def coverage_cap(intensity: float, n_groups: int) -> int:
    """How many prop groups a section lights, by energy (quiet sparse, loud full)."""
    i = max(0.0, min(1.0, intensity or 0.0))
    return min(n_groups, max(MIN_LIT_GROUPS, round(n_groups * (0.3 + 0.7 * i))))


def trim_coverage(instructions: list, intensity: float) -> list:
    """Keep the wash on the first `cap` distinct targets (Director priority); leave the rest dark."""
    order: list[str] = []
    for ins in instructions:
        if ins.target not in order:
            order.append(ins.target)
    keep = set(order[:coverage_cap(intensity, len(order))])
    return [ins for ins in instructions if ins.target in keep]


def _off_beat_stride(intensity: float) -> int | None:
    """How sparse the OFF-beats are by section energy (downbeats are always kept).
    None = downbeats only; 2 = every other off-beat; 1 = every beat."""
    if intensity <= 0.30:
        return None
    if intensity <= 0.65:
        return 2
    return 1


def _chord_color(t: int, chords_ms: list, colors: list[str]) -> str | None:
    """The palette color for the chord active at time t (steps each chord change)."""
    if not chords_ms or not colors:
        return None
    idx = bisect.bisect_right([c[0] for c in chords_ms], t) - 1
    return colors[max(0, idx) % len(colors)]


def section_rhythm(sa, section: SectionPlan) -> dict:
    """Per-section beats + each stem's onsets in-window (ms) + the prominent stem.

    Prominent stem = the non-"other" stem with the most onsets in the section window (so it's
    derived from the audio, not a brief field). The brief's `follow_stem` can override it.
    """
    s, e = section.start_ms, section.end_ms
    beats = [int(b.time * 1000) for b in (getattr(sa, "beats", None) or [])
             if s <= b.time * 1000 < e]
    onsets_by_stem: dict[str, list[int]] = {}
    for f in getattr(sa, "stems", None) or []:
        ons = sorted(int(t * 1000) for t in (f.onsets or []) if s <= t * 1000 < e)
        if ons:
            onsets_by_stem[f.stem] = ons
    cand = {k: len(v) for k, v in onsets_by_stem.items() if k != "other"}
    prominent = max(cand, key=cand.get) if cand else None
    chords = sorted((int(c.time * 1000), c.label) for c in (getattr(sa, "chords", None) or [])
                    if s <= c.time * 1000 < e)
    return {"beats_ms": sorted(beats), "prominent_stem": prominent,
            "onsets_by_stem": onsets_by_stem, "chords_ms": chords,
            "tempo": getattr(sa, "tempo_overall", None)}


FLASH_MS = 150                            # brief full-display white hit
FLASH_KINDS = ("climax", "accent", "drop", "hit")
FLASH_BRIGHTNESS = 300.0                  # 0–400 scale → a bright white pop


def key_moment_flashes(show_plan, available_groups: list[str]) -> list:
    """A short WHITE flash on the whole display (SEM_ALL) at climax/accent key-moments."""
    moments = [m for m in (getattr(show_plan, "key_moments", None) or [])
               if any(k in (m.kind or "").lower() for k in FLASH_KINDS)][:8]
    target = FULL_DISPLAY if FULL_DISPLAY in (available_groups or []) else None
    if not moments or not target:
        return []
    look = candidate_look_ids("On")[0]
    boost = brightness_setting(FLASH_BRIGHTNESS)
    return [EffectInstruction(target=target, effect_type="On", look_id=look, palette_colors=["white"],
                              extra_settings=dict(boost), start_ms=int(m.at_ms),
                              end_ms=int(m.at_ms) + FLASH_MS)
            for m in moments]


def _accent_look(effect_type: str) -> tuple[str, str]:
    """A placeable accent effect + a valid look — fall back to On (`Pulse` is not placeable)."""
    if effect_type and effect_type in placeable_effect_types():
        looks = candidate_look_ids(effect_type)
        if looks:
            return effect_type, looks[0]
    return "On", candidate_look_ids("On")[0]


def _downsample(times: list, cap: int) -> list:
    if cap <= 0:
        return []
    if len(times) <= cap:
        return times
    k = len(times) / cap
    return [times[int(i * k)] for i in range(cap)]


def place_beat_accents(section: SectionPlan, rhythm: dict, available_groups: list[str],
                       *, carrier_covers: bool = False) -> list[EffectInstruction]:
    """Accents on ~every beat, chasing the rhythm groups, in a CONTRASTING accent color, with a
    bigger all-groups hit on each bar start (downbeat). Onset mode keeps the simple rotating chase.

    `carrier_covers=True` (a weave carrier already rides the rhythm pool): the every-beat chase
    and downbeat group hits are the CARRIER's job now — only the sparkle-prop downbeats and the
    hero onset layer place, so the beat is carried once, not doubled."""
    groups = list(section.pulse_groups or [])
    for g in RHYTHM_POOL:                              # a chase needs ≥2 groups — rhythm cells join
        if len(groups) >= 3:
            break
        if g in available_groups and g not in groups:
            groups.append(g)
    if not groups:
        groups = [g for g in RHYTHM_GROUPS if g in available_groups] or list(section.target_groups)
    if not groups:
        return []
    eff, look = _accent_look(section.accent_effect)
    # The wash keeps the palette family; the beats use the CONTRAST anchors (the two most
    # hue-distant colors after the LED legibility floor) — pixels render hue contrast, not the
    # old brightened-same-hue accents, which read as the wash. Anchors stay SATURATED
    # (_brighten washes hue out into exactly the pastel tint LEDs can't show); the pop comes
    # from luminance settings, not color dilution. Chord changes step the pair.
    a, b = contrast_anchors(section.palette)
    cycle = [b, a]                                        # hue-distant anchor leads
    accent_colors = [cycle[0]]
    chords_ms = rhythm.get("chords_ms") or []

    def _color_at(t: int) -> list[str]:
        c = _chord_color(t, chords_ms, cycle)                 # step color with the harmony
        return [c] if c else list(accent_colors)

    def _mk(target: str, t: int, end: int) -> EffectInstruction:
        # a 250ms punctuation must FILL its props — the global fallback sends chase-family
        # accent effects to 'Per Preview' (spread over the whole yard ≈ invisible)
        return EffectInstruction(target=target, effect_type=eff, look_id=look,
                                 render_style="Per Model Default",
                                 palette_colors=_color_at(t), start_ms=int(t), end_ms=int(end))

    def _end(times: list[int], i: int, t: int) -> int:
        nxt = times[i + 1] if i + 1 < len(times) else section.end_ms
        return min(nxt, t + ACCENT_MS, section.end_ms)

    pulse_on = section.pulse_on or "beat"
    stem = section.follow_stem or rhythm["prominent_stem"]
    onsets = rhythm["onsets_by_stem"].get(stem, []) if stem else []
    if pulse_on == "onset" and onsets:                 # explicit override: ride the stem's hits
        times = _downsample(sorted(onsets), MAX_ACCENTS_PER_SECTION)
        out = [] if carrier_covers else \
            [_mk(groups[i % len(groups)], t, e)
             for i, t in enumerate(times) if (e := _end(times, i, t)) > t]
        # bars still exist under an onset groove — sparkle props fire on the beat-grid downbeats
        sparkle = [g for g in ACCENT_GROUPS if g in available_groups and g not in groups]
        for t in sorted(rhythm["beats_ms"])[::BEATS_PER_BAR]:
            e = min(t + ACCENT_MS, section.end_ms)
            if e > t:
                out.extend(_mk(g, t, e) for g in sparkle)
        return out

    beats = sorted(rhythm["beats_ms"])
    if not beats:
        return []
    accent_hits = [g for g in ACCENT_GROUPS if g in available_groups and g not in groups]
    stride = _off_beat_stride(getattr(section, "intensity", 0.8) or 0.8)   # energy-scaled density
    downbeats: list[EffectInstruction] = []
    offbeats: list[EffectInstruction] = []
    off_n = 0
    for i, t in enumerate(beats):
        e = _end(beats, i, t)
        if e <= t:
            continue
        if i % BEATS_PER_BAR == 0:                      # bar start → bigger hit (every group)
            if not carrier_covers:                      # the weave carrier owns the group hits
                downbeats.extend(_mk(g, t, e) for g in groups)
            downbeats.extend(_mk(g, t, e) for g in accent_hits)   # snowflakes/spinners fire on the bar
        else:                                           # off-beat → single rotating group (energy-gated)
            if not carrier_covers and stride is not None and off_n % stride == 0:
                # the chase BOUNCES: forward through the spatial group order on even bars,
                # backward on odd — direction variety with no LLM surface. Position WITHIN
                # the bar drives the walk (bar and pool periods differ).
                n, p = len(groups), i % BEATS_PER_BAR
                idx = p % n if (i // BEATS_PER_BAR) % 2 == 0 else (n - 1) - (p % n)
                offbeats.append(_mk(groups[idx], t, e))
            off_n += 1
    downbeats = _downsample(downbeats, MAX_ACCENTS_PER_SECTION)         # keep downbeats first
    budget = max(0, MAX_ACCENTS_PER_SECTION - len(downbeats))
    out = downbeats + _downsample(offbeats, budget)

    # hero onset layer: a feature prop pulses on the prominent stem's real attacks — energy-scaled
    # (quiet sections get few/none) and capped so it stays a tasteful accent, not a strobe.
    hero_cap = round(HERO_MAX_ONSETS * (getattr(section, "intensity", 0.8) or 0.8))
    if onsets and hero_cap > 0:
        hero = (HERO_GROUP if HERO_GROUP in available_groups else None) \
            or (section.target_groups[0] if section.target_groups else None)
        if hero:
            htimes = _downsample(sorted(onsets), hero_cap)
            out += [_mk(hero, t, e) for i, t in enumerate(htimes) if (e := _end(htimes, i, t)) > t]
    return out


BED_INTENSITY = 0.7                       # high-energy sections carry a whole-yard bed
BED_BRIGHTNESS_FACTOR = 0.6               # the bed sits UNDER the features

# Peak escalation: the show's payoff section(s) must read as the BIGGEST moment, not a busier
# verse — full display, full brightness, regardless of how narrowly the brief targeted them.
PEAK_BAND = 0.12                          # sections within this of max intensity = the peak
PEAK_FLOOR = 0.66                         # ...and at least this loud (a quiet show has no peak)
PEAK_BROAD_GROUPS = ("SEM_ALL", "SEM_BAND_GROUND")   # broadest available ensemble, preferred order


def peak_sections(show_plan, band: float = PEAK_BAND, floor: float = PEAK_FLOOR) -> set[int]:
    """Indices of the show's PEAK section(s): within `band` of the max section intensity AND
    ≥ `floor`. Relative, so it works at any absolute energy; {} when nothing clears the floor."""
    secs = list(getattr(show_plan, "sections", None) or [])
    if not secs:
        return set()
    peak = max((getattr(s, "intensity", 0.0) or 0.0) for s in secs)
    if peak < floor:
        return set()
    return {i for i, s in enumerate(secs)
            if (getattr(s, "intensity", 0.0) or 0.0) >= peak - band}


PEAK_BED_SPAN = 0.7                       # an existing wash this long already IS the lit yard


def peak_fill(section, intensity: float, available_groups: list[str],
              existing_instrs=None) -> EffectInstruction | None:
    """A FULL-brightness whole-display bed for a peak section — the lit yard the payoff needs
    (vs `ensemble_bed`'s dim frame for merely-high sections). Placed first → lowest layer; the
    weave/accents ride on top.

    `existing_instrs` = the section's placements so far: skip a broad target only when it ALREADY
    carries a section-spanning wash (a 0.3s Strobe on SEM_ALL is punctuation, not a bed — the
    old 'any instruction on the target' guard let narrow peaks stay dark)."""
    span = (section.end_ms - section.start_ms) * PEAK_BED_SPAN
    bedded = {ins.target for ins in (existing_instrs or [])
              if ins.effect_type in ("On", "Color Wash") and ins.end_ms - ins.start_ms >= span}
    target = next((g for g in PEAK_BROAD_GROUPS if g in available_groups and g not in bedded), None)
    if not target:
        return None
    ins = EffectInstruction(target=target, effect_type="On", look_id=candidate_look_ids("On")[0],
                            palette_colors=effect_palette(section.palette, "On", 0) or list(section.palette),
                            start_ms=section.start_ms, end_ms=section.end_ms)
    ins.extra_settings.update(brightness_setting(wash_brightness(intensity)))   # FULL, not 0.6×
    return ins


def ensemble_bed(section, intensity: float, available_groups: list[str], existing_targets) -> EffectInstruction | None:
    """A low-brightness ensemble bed for high-energy sections ('the frame holds the bed') —
    so a peak never reads as a quarter-lit yard behind one blinking group."""
    if intensity < BED_INTENSITY:
        return None
    target = next((g for g in ("SEM_BAND_GROUND", "SEM_ALL") if g in available_groups), None)
    if not target or target in (existing_targets or set()):
        return None
    ins = EffectInstruction(target=target, effect_type="On", look_id=candidate_look_ids("On")[0],
                            palette_colors=effect_palette(section.palette, "On", 1) or list(section.palette),
                            start_ms=section.start_ms, end_ms=section.end_ms)
    ins.extra_settings.update(brightness_setting(wash_brightness(intensity) * BED_BRIGHTNESS_FACTOR))
    return ins


# -- atmosphere readability --------------------------------------------------------------------
# Sprite/particle features render on a TRANSPARENT background: an opaque bed below bleeds through
# the gaps and drowns them. Dim such a bed to a glow so the feature reads (the brief's "still glow
# + falling snow"). Ordering can't fix this — the feature is already the top layer.
ATMOSPHERIC = {"Snowflakes", "Snowstorm", "Meteors", "Twinkle", "Fireworks"}
BED_EFFECTS = {"On", "Color Wash", "Fill"}
GLOW_BRIGHTNESS = 30.0                    # 0–400 scale (100=normal): a dim base the sprites pop against


def _slider_brightness(ins: EffectInstruction):
    """The bed's current static brightness (0–400, 100=normal), or None if only a curve/default."""
    raw = ins.extra_settings.get("C_SLIDER_Brightness")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _time_overlaps(a: EffectInstruction, b: EffectInstruction) -> bool:
    return a.start_ms < b.end_ms and b.start_ms < a.end_ms


def dim_beds_under_atmosphere(instructions: list[EffectInstruction]) -> list[EffectInstruction]:
    """Cap an opaque wash bed (On/Color Wash/Fill) at a glow level when a sparse atmospheric
    feature coexists on the SAME element and overlaps it in time — so the feature reads against a
    glow instead of a full wash. Mutates in place; returns the list.

    Caps, never brightens: a bed already dimmer than the glow is left as-is. We cap rather than
    skip-on-brightness because EVERY section wash already carries an intensity-keyed
    `wash_brightness` — there is no "bare" bed to detect; the bug is that wash level (e.g. 76 on a
    calm intro) is still bright enough to drown transparent sprites. A glow (30) lets them read.

    Skipped: beds with a blend mode set → already composited (e.g. a Max-blend beat accent), not an
    occluding Normal-blend wash.

    Coexistence (not a layer comparison) is the trigger: on-disk layers are assigned by stream
    order at emit, so the bed's `.layer` hint is unreliable here — but a Normal-blend wash sharing
    an element with an atmospheric feature drowns it whether it lands above or below.

    Same-element only: cross-group occlusion already resolves via render order (the accent group
    wins overlaps over SEM_ALL), and a group's own bed is what bleeds through its own feature."""
    by_target: dict[str, list[EffectInstruction]] = {}
    for ins in instructions:
        by_target.setdefault(ins.target, []).append(ins)
    for items in by_target.values():
        features = [i for i in items if i.effect_type in ATMOSPHERIC]
        if not features:
            continue
        for bed in items:
            if bed.effect_type not in BED_EFFECTS:
                continue
            if "T_CHOICE_LayerMethod" in bed.extra_settings:     # composited add, not a wash
                continue
            if not any(_time_overlaps(f, bed) for f in features):
                continue
            cur = _slider_brightness(bed)
            if cur is None or cur > GLOW_BRIGHTNESS:
                bed.extra_settings.pop("C_VALUECURVE_Brightness", None)   # a static glow wins
                bed.extra_settings.update(brightness_setting(GLOW_BRIGHTNESS))
    return instructions


HIT_CELL_MS = 1200                        # a hit effect cell is at most this long


def _bar_ms(rhythm: dict) -> float:
    tempo = rhythm.get("tempo")
    if tempo:
        return BEATS_PER_BAR * 60000.0 / tempo
    beats = rhythm.get("beats_ms") or []
    if len(beats) > 4:
        deltas = [b - a for a, b in zip(beats, beats[1:])]
        deltas.sort()
        return BEATS_PER_BAR * deltas[len(deltas) // 2]
    return BEATS_PER_BAR * 2000.0


def normalize_durations(instructions: list, rhythm: dict) -> list:
    """Enforce duration classes (catalog §2.1 v0.3): a HIT-class effect spanning bars becomes
    per-bar short cells (the section PULSES with it instead of smearing one slow gesture); a
    PHRASE-class effect is clamped to ~8 bars; a CELL-ABLE motion effect left long is chopped
    into contiguous 2-bar cells (community medians: even Spirals/Wave run 0.3–0.9s) unless it
    sits on a bed row (SEM_BAND_*/SEM_ALL — the explicit long-bed exception)."""
    from ..qa.rules import (CELL_BARS, DURATION_CELLABLE, DURATION_HIT, DURATION_PHRASE,
                            PHRASE_BARS, _BED_TARGET_PREFIXES, _BED_TARGETS)
    bar = _bar_ms(rhythm)
    out: list = []
    for ins in instructions:
        dur = ins.end_ms - ins.start_ms
        if ins.effect_type in DURATION_HIT and dur > 1.5 * bar:
            cell = int(min(HIT_CELL_MS, bar * 0.75))
            t = float(ins.start_ms)
            while t < ins.end_ms:
                c = ins.model_copy(deep=True)
                c.start_ms, c.end_ms = int(t), int(min(t + cell, ins.end_ms))
                if c.end_ms > c.start_ms:
                    out.append(c)
                t += bar                              # one pulse per bar
        elif ins.effect_type in DURATION_PHRASE and dur > PHRASE_BARS * bar:
            c = ins.model_copy(deep=True)
            c.end_ms = int(ins.start_ms + PHRASE_BARS * bar)
            out.append(c)
        elif (ins.effect_type in DURATION_CELLABLE and dur > 2 * CELL_BARS * bar
              and not ins.target.startswith(_BED_TARGET_PREFIXES)
              and ins.target not in _BED_TARGETS):
            cell = CELL_BARS * bar                    # contiguous cells — motion, not pulses
            t = float(ins.start_ms)
            while t < ins.end_ms:
                c = ins.model_copy(deep=True)
                c.start_ms, c.end_ms = int(t), int(min(t + cell, ins.end_ms))
                if c.end_ms - c.start_ms > cell * 0.25:   # trailing sliver merges by dropping
                    out.append(c)
                elif out and out[-1].effect_type == ins.effect_type:
                    out[-1].end_ms = int(ins.end_ms)      # ...into the previous cell
                t += cell
        else:
            out.append(ins)
    return out
