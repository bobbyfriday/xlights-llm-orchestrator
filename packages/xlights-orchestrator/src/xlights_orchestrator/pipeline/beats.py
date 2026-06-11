"""Beat-aware accent layer: deterministic per-section rhythm + beat-synced accent placement.

Timing is code-owned (beats / the prominent stem's onsets from SongAnalysis); the creative
choices (which groups, which stem, what accent) come from the brief with sensible defaults. The
accents are a SECOND layer added over the section washes, chasing across the rhythm groups.
"""

from __future__ import annotations

import bisect

from xlights_core.knowledge.colors import _brighten, _luminance, _resolve, expand_palette
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


SPEED_MIN, SPEED_MAX = 8, 40              # effect speed slider range by energy


def effect_speed_setting(effect_type: str, intensity: float) -> dict[str, str]:
    """`{E_SLIDER_<Effect>_Speed: val}` keyed to energy (slow quiet → fast loud). Appended;
    a key an effect doesn't use is ignored by xLights, so this is safe for any effect."""
    i = max(0.0, min(1.0, intensity or 0.0))
    val = round(SPEED_MIN + (SPEED_MAX - SPEED_MIN) * i)
    return {f"E_SLIDER_{effect_type}_Speed": str(val)}


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


def place_beat_accents(section: SectionPlan, rhythm: dict, available_groups: list[str]
                       ) -> list[EffectInstruction]:
    """Accents on ~every beat, chasing the rhythm groups, in a CONTRASTING accent color, with a
    bigger all-groups hit on each bar start (downbeat). Onset mode keeps the simple rotating chase."""
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
    # The wash keeps the full (bright) palette; the beats are BRIGHTENED palette colors so they pop
    # by luminance while staying colorful, cycling through the harmony's colors on chord changes.
    hexes: list[str] = []
    for c in section.palette or []:
        h = _resolve(c)
        if h and h not in hexes:
            hexes.append(h)
    cycle: list[str] = []
    for h in sorted(hexes, key=_luminance, reverse=True):     # brightest first
        bh = _brighten(h)
        if bh not in cycle:
            cycle.append(bh)
    accent_colors = [cycle[0]] if cycle else list(section.palette)   # default beat = brightened-brightest
    chords_ms = rhythm.get("chords_ms") or []

    def _color_at(t: int) -> list[str]:
        c = _chord_color(t, chords_ms, cycle)                 # step color with the harmony
        return [c] if c else list(accent_colors)

    def _mk(target: str, t: int, end: int) -> EffectInstruction:
        return EffectInstruction(target=target, effect_type=eff, look_id=look,
                                 palette_colors=_color_at(t), start_ms=int(t), end_ms=int(end))

    def _end(times: list[int], i: int, t: int) -> int:
        nxt = times[i + 1] if i + 1 < len(times) else section.end_ms
        return min(nxt, t + ACCENT_MS, section.end_ms)

    pulse_on = section.pulse_on or "beat"
    stem = section.follow_stem or rhythm["prominent_stem"]
    onsets = rhythm["onsets_by_stem"].get(stem, []) if stem else []
    if pulse_on == "onset" and onsets:                 # explicit override: ride the stem's hits
        times = _downsample(sorted(onsets), MAX_ACCENTS_PER_SECTION)
        out = [_mk(groups[i % len(groups)], t, e)
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
            downbeats.extend(_mk(g, t, e) for g in groups)
            downbeats.extend(_mk(g, t, e) for g in accent_hits)   # snowflakes/spinners fire on the bar
        else:                                           # off-beat → single rotating group (energy-gated)
            if stride is not None and off_n % stride == 0:
                offbeats.append(_mk(groups[i % len(groups)], t, e))
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
    """Enforce duration classes (catalog §2.1): a HIT-class effect spanning bars becomes per-bar
    short cells (the section PULSES with it instead of smearing one slow gesture); a PHRASE-class
    effect is clamped to ~8 bars; SUSTAINED passes through."""
    from ..qa.rules import DURATION_HIT, DURATION_PHRASE, PHRASE_BARS
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
        else:
            out.append(ins)
    return out
