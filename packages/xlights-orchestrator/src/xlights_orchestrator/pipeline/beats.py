"""Beat-aware accent layer: deterministic per-section rhythm + beat-synced accent placement.

Timing is code-owned (beats / the prominent stem's onsets from SongAnalysis); the creative
choices (which groups, which stem, what accent) come from the brief with sensible defaults. The
accents are a SECOND layer added over the section washes, chasing across the rhythm groups.
"""

from __future__ import annotations

import bisect
from typing import NamedTuple

from xlights_core.knowledge.colors import _luminance, _resolve, contrast_anchors, expand_palette
from xlights_core.knowledge.value_curves import brightness_setting

from ..agents.catalog import candidate_look_ids, placeable_effect_types
from ..show_plan import EffectInstruction, SectionPlan

# SEM_ semantic groups (xlights-layout-semantics-spec): the beat chase sweeps L→C→R spatially,
# the hero onset layer rides the focal props, flashes hit the whole display. Group vocabulary in
# semantic_groups; the show-feel dials (brightness/energy/density) live in tuning.
from .phrasing import resolve_phrasing, soft_edge_settings
from .semantic_groups import (
    ACCENT_GROUPS,
    BACKBEAT_GROUP_PREFERENCE,
    BASS_BAND_GROUP,
    BED_PREFERENCE,
    FULL_DISPLAY,
    HERO_GROUP,
    MELODIC_STEMS,
    METRIC_RING,
    PEAK_BROAD_GROUPS,
    RHYTHM_GROUPS,
    RHYTHM_POOL,
)
from .tuning import (
    ACCENT_MS,
    BACKBEAT_MIN_DRUM_ONSETS,
    BASS_MAX_ONSETS,
    BED_BRIGHTNESS_FACTOR,
    BED_INTENSITY,
    ESCALATION_BOOST,
    FEATURE_PROP_BRIGHTNESS,
    FLASH_BRIGHTNESS,
    FLASH_MS,
    HERO_MAX_ONSETS,
    HIT_CELL_MS,
    LEGATO_ACCENT_MS,
    LEGATO_ACCENT_SPARSEN,
    MAX_ACCENTS_PER_SECTION,
    MIN_LIT_GROUPS,
    PALETTE_DEPTH,
    PEAK_BAND,
    PEAK_BED_SPAN,
    PEAK_FLOOR,
    RHYTHM_FLOOR,
    SPARKLE_TOP_N,
    WASH_MAX_B,
    WASH_MIN_B,
)

BEATS_PER_BAR = 4                  # derived 4/4 (downbeat = every 4th beat)


def wash_brightness(intensity: float) -> float:
    """Section wash brightness level (0–400 scale) keyed to energy."""
    i = max(0.0, min(1.0, intensity or 0.0))
    return WASH_MIN_B + (WASH_MAX_B - WASH_MIN_B) * i


SIMPLE_COLOR = {"On", "Off", "Strobe", "Lightning", "Fill"}   # 1-2 colors read best


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


def section_rhythm(sa, section: SectionPlan, beats_per_bar: int = BEATS_PER_BAR) -> dict:
    """Per-section beats + each stem's onsets in-window (ms) + the prominent stem.

    Prominent stem = the non-"other" stem with the most onsets in the section window (so it's
    derived from the audio, not a brief field). The brief's `follow_stem` can override it.
    `beats_per_bar` is the song's resolved meter (see meter.resolve_beats_per_bar); it rides the
    rhythm dict so the accent/weave/duration layers grid to the real time signature, not always 4/4.
    """
    s, e = section.start_ms, section.end_ms
    beats = [int(b.time * 1000) for b in (getattr(sa, "beats", None) or [])
             if s <= b.time * 1000 < e]
    onsets_by_stem: dict[str, list[int]] = {}
    onset_mag_by_stem: dict[str, list[float]] = {}    # each onset's normalized strength (0–1)
    for f in getattr(sa, "stems", None) or []:
        arc = getattr(f, "energy_arc", None) or []
        pk = max((p.rms for p in arc), default=0.0) or 1.0
        pairs = sorted((int(t * 1000), _onset_energy(arc, t, pk))
                       for t in (f.onsets or []) if s <= t * 1000 < e)
        if pairs:
            onsets_by_stem[f.stem] = [t for t, _ in pairs]
            onset_mag_by_stem[f.stem] = [m for _, m in pairs]
    cand = {k: len(v) for k, v in onsets_by_stem.items() if k != "other"}
    prominent = max(cand, key=cand.get) if cand else None
    mel = {k: len(v) for k, v in onsets_by_stem.items() if k in MELODIC_STEMS}
    melodic = max(mel, key=mel.get) if mel else None      # the lead the hero prop follows
    chords = sorted((int(c.time * 1000), c.label) for c in (getattr(sa, "chords", None) or [])
                    if s <= c.time * 1000 < e)
    return {"beats_ms": sorted(beats), "prominent_stem": prominent, "melodic_stem": melodic,
            "onsets_by_stem": onsets_by_stem, "onset_mag_by_stem": onset_mag_by_stem,
            "chords_ms": chords, "beats_per_bar": beats_per_bar,
            "tempo": getattr(sa, "tempo_overall", None)}


def _onset_energy(arc, t_s: float, peak: float) -> float:
    """The stem's normalized RMS at an onset (nearest ~0.5s sample) — a small/big-hit magnitude."""
    if not arc:
        return 0.0
    nearest = min(arc, key=lambda p: abs(p.time - t_s))
    return max(0.0, min(1.0, nearest.rms / (peak or 1.0)))


FLASH_KINDS = ("climax", "accent", "drop", "hit")


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


class RhythmRoles(NamedTuple):
    ring: list[str]               # the metric ring (one group per beat, in order)
    sparkle: list[str]            # accent/point props that ride the strongest drum hits
    hero: str | None              # the focal prop the melodic lead drives
    bass_band: str | None         # the low band the bass foundation rides
    backbeat: str | None          # the contrasting group that answers on 2 & 4


def select_rhythm_groups(section: SectionPlan, available_groups: list[str]) -> RhythmRoles:
    """Pick each rhythm sublayer's groups from the layout's classified groups (not a flat tuple).
    The brief's pulse_groups seed/override the metric ring; a missing category disables only its
    own sublayer (graceful)."""
    avail = list(available_groups or [])
    ring = [g for g in (section.pulse_groups or []) if g in avail]
    if len(ring) < 2:                          # a meter walk needs ≥2 prop families — extend a thin brief
        for g in (METRIC_RING + RHYTHM_POOL + RHYTHM_GROUPS):
            if g in avail and g not in ring:
                ring.append(g)
            if len(ring) >= 4:                 # a full bar's worth of distinct families
                break
    ring = ring or [g for g in (section.target_groups or []) if g in avail]
    sparkle = [g for g in ACCENT_GROUPS if g in avail and g not in ring]
    hero = HERO_GROUP if HERO_GROUP in avail else \
        (section.target_groups[0] if section.target_groups else None)
    bass_band = BASS_BAND_GROUP if BASS_BAND_GROUP in avail else None
    # the backbeat answers on a contrasting group — prefer a non-ring, non-sparkle group; when
    # none is free (the ring consumed the side groups), fall back to a ring family OTHER than the
    # downbeat anchor (ring[0]) so the backbeat still reads on most drum sections.
    backbeat = next((g for g in BACKBEAT_GROUP_PREFERENCE
                     if g in avail and g not in ring and g not in sparkle), None)
    if backbeat is None and len(ring) >= 2:
        backbeat = ring[len(ring) // 2]        # a different prop family than the anchor ring[0]
    return RhythmRoles(ring, sparkle, hero, bass_band, backbeat)


def _backbeat_positions(bpb: int) -> set[int]:
    """The weak-strong beats of the bar (0-indexed). 4/4 → {1, 3} = beats 2 & 4 (the snare)."""
    if bpb >= 4:
        return {i for i in range(1, bpb, 2)}     # 2 & 4 (& 6 …)
    if bpb == 3:
        return {1}                               # beat 2 lift in 3/4
    return set()


def place_beat_accents(section: SectionPlan, rhythm: dict, available_groups: list[str],
                       *, carrier_covers: bool = False) -> list[EffectInstruction]:
    """The deterministic rhythm = a METER BACKBONE (each beat of the bar lights the next ring group,
    so the bar walks across prop families) + an instrument-mapped GROOVE OVERLAY (backbeat on 2&4,
    sparkle on the strongest drum hits, the melodic lead on the hero, bass on the ground band), all
    phrasing-modulated (legato lengthens/fades/sparsens; staccato crisp).

    `carrier_covers=True` (a weave carrier already rides the rhythm pool): the backbone defers (the
    carrier IS the beat now); the overlay still places, so the beat is carried once, not doubled."""
    beats = sorted(rhythm.get("beats_ms") or [])
    if not beats:
        return []
    bpb = rhythm.get("beats_per_bar") or BEATS_PER_BAR    # the song's meter, not always 4/4
    roles = select_rhythm_groups(section, available_groups)
    intensity = getattr(section, "intensity", 0.8) or 0.8
    legato = resolve_phrasing(getattr(section, "phrasing", ""), intensity) == "legato"
    accent_ms = LEGATO_ACCENT_MS if legato else ACCENT_MS
    eff, look = _accent_look(section.accent_effect)
    # beats use the CONTRAST anchors (the two most hue-distant colors) — pixels render hue contrast,
    # not the wash's family. Chord changes step the pair.
    a, b = contrast_anchors(section.palette)
    cycle = [b, a]
    chords_ms = rhythm.get("chords_ms") or []

    def _color_at(t: int) -> list[str]:
        c = _chord_color(t, chords_ms, cycle)
        return [c] if c else [cycle[0]]

    def _mk(target: str, t: int, end: int, *, boost: float | None = None) -> EffectInstruction:
        extra: dict[str, str] = {}
        if legato:                                       # legato accents breathe + soft-fade
            extra.update(soft_edge_settings(eff, end - t, "legato"))
        if boost is not None:
            extra.update(brightness_setting(boost))      # the downbeat anchor reads bigger
        return EffectInstruction(target=target, effect_type=eff, look_id=look,
                                 render_style="Per Model Default", palette_colors=_color_at(t),
                                 extra_settings=extra, start_ms=int(t), end_ms=int(end))

    def _end_at(t: int, nxt: int | None) -> int:
        cap = nxt if nxt is not None else section.end_ms
        return min(cap, t + accent_ms, section.end_ms)

    out: list[EffectInstruction] = []

    # -- METER BACKBONE: beat i → ring[i % len(ring)]; downbeat is the brighter anchor -----------
    if not carrier_covers and roles.ring:
        n = len(roles.ring)
        stride = _off_beat_stride(intensity)             # energy-gated off-beat density
        anchor_b = wash_brightness(min(1.0, intensity + 0.2))    # downbeat reads bigger
        for i, t in enumerate(beats):
            end = _end_at(t, beats[i + 1] if i + 1 < len(beats) else None)
            if end <= t:
                continue
            is_down = (i % bpb == 0)
            if is_down:
                out.append(_mk(roles.ring[0], t, end, boost=anchor_b))   # the bar anchor
                continue
            if stride is None or (i % stride):           # off-beat density gate
                continue
            if legato and (i % LEGATO_ACCENT_SPARSEN):   # legato is sparser still
                continue
            out.append(_mk(roles.ring[i % n], t, end))   # the walk across prop families

    # -- BACKBEAT (2 & 4): a contrasting answer, only with drums present -------------------------
    drum_onsets = rhythm.get("onsets_by_stem", {}).get("drums", [])
    if roles.backbeat and len(drum_onsets) >= BACKBEAT_MIN_DRUM_ONSETS and not legato:
        bpos = _backbeat_positions(bpb)
        n = len(roles.ring)
        for i, t in enumerate(beats):
            if i % bpb not in bpos:
                continue
            # skip when a ring-fallback backbeat would double the backbone's own group this beat
            if not carrier_covers and n and roles.ring[i % n] == roles.backbeat:
                continue
            end = _end_at(t, beats[i + 1] if i + 1 < len(beats) else None)
            if end > t:
                out.append(_mk(roles.backbeat, t, end))

    # -- SPARKLE: the strongest drum hits (not every bar) ----------------------------------------
    if roles.sparkle and drum_onsets:
        mags = rhythm.get("onset_mag_by_stem", {}).get("drums", [])
        ranked = sorted(zip(drum_onsets, mags or [0.0] * len(drum_onsets)),
                        key=lambda tm: -tm[1])[:SPARKLE_TOP_N]
        for t, _m in sorted(ranked):
            end = min(t + accent_ms, section.end_ms)
            if end > t:
                out.extend(_mk(g, t, end) for g in roles.sparkle)

    # -- HERO: the melodic lead (guitar/piano/vocals) on the focal prop, on its real onsets -------
    mel_stem = section.follow_stem or rhythm.get("melodic_stem")
    mel_onsets = rhythm.get("onsets_by_stem", {}).get(mel_stem, []) if mel_stem else []
    hero_cap = round(HERO_MAX_ONSETS * intensity)
    if roles.hero and mel_onsets and hero_cap > 0:
        htimes = _downsample(sorted(mel_onsets), hero_cap)
        for i, t in enumerate(htimes):
            end = _end_at(t, htimes[i + 1] if i + 1 < len(htimes) else None)
            if end > t:
                out.append(_mk(roles.hero, t, end))

    # -- BASS foundation: a sparse low pulse on the ground band -----------------------------------
    bass_onsets = rhythm.get("onsets_by_stem", {}).get("bass", [])
    if roles.bass_band and bass_onsets:
        btimes = _downsample(sorted(bass_onsets), BASS_MAX_ONSETS)
        for i, t in enumerate(btimes):
            end = _end_at(t, btimes[i + 1] if i + 1 < len(btimes) else None)
            if end > t:
                out.append(_mk(roles.bass_band, t, end))

    return _cap_accents(out)


def _cap_accents(accents: list[EffectInstruction]) -> list[EffectInstruction]:
    """Bound the per-section accent count, keeping an even temporal spread (downsample by time)."""
    if len(accents) <= MAX_ACCENTS_PER_SECTION:
        return accents
    ordered = sorted(accents, key=lambda a: a.start_ms)
    return _downsample(ordered, MAX_ACCENTS_PER_SECTION)




def section_is_rhythmic(section) -> bool:
    """Does the brief OPT INTO a beat layer for this section? The deterministic rhythm layers
    (fallback weave, beat-accent chase) fire only when so — a deliberately quiet/still section
    (low intensity, no pulse groups, no rhythm props chosen) is realized as the brief directs,
    not buried under injected chases/pops."""
    if section is None:
        return True
    if getattr(section, "pulse_groups", None):                        # explicit beat-layer request
        return True
    targets = set(getattr(section, "target_groups", None) or [])
    if targets & (set(RHYTHM_POOL) | set(RHYTHM_GROUPS)):             # brief chose rhythm props
        return True
    return (getattr(section, "intensity", 0.0) or 0.0) >= RHYTHM_FLOOR   # energetic → rhythmic



# Peak escalation: the show's payoff section(s) must read as the BIGGEST moment, not a busier
# verse — full display, full brightness, regardless of how narrowly the brief targeted them.
# PEAK_BROAD_GROUPS / BED_PREFERENCE come from semantic_groups (orders differ on purpose).


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
    target = next((g for g in BED_PREFERENCE if g in available_groups), None)
    if not target or target in (existing_targets or set()):
        return None
    ins = EffectInstruction(target=target, effect_type="On", look_id=candidate_look_ids("On")[0],
                            palette_colors=effect_palette(section.palette, "On", 1) or list(section.palette),
                            start_ms=section.start_ms, end_ms=section.end_ms)
    ins.extra_settings.update(brightness_setting(wash_brightness(intensity) * BED_BRIGHTNESS_FACTOR))
    return ins


# -- feature-prop contrast floor --------------------------------------------------------------
# A dedicated sparkle/snow prop group, when it's a section FEATURE, must POP — light it in the
# section's LIGHTEST color (white snow) at a bright level so it reads against the bed. Deterministic
# floor UNDER the LLM steering: the LLM picks the look; this guarantees the feature isn't lost to a
# dim or same-hue color (the silver-snow-on-navy failure). Scoped to the accent prop groups only.
FEATURE_BASE_EFFECTS = {"On", "Twinkle", "SingleStrand", "Single Strand", "Fill", "Snowflakes",
                        "Snowstorm", "Strobe", "Shimmer", "Meteors"}


def _slider_brightness(ins: EffectInstruction):
    raw = ins.extra_settings.get("C_SLIDER_Brightness")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _lightest_hex(palette: list[str]) -> str | None:
    hexes = [h for h in (_resolve(c) for c in (palette or [])) if h]
    return max(hexes, key=_luminance) if hexes else None


def feature_prop_contrast(instructions: list[EffectInstruction], section: SectionPlan
                          ) -> list[EffectInstruction]:
    """Floor: when a dedicated sparkle/snow prop group (ACCENT_GROUPS) is among the section's
    targets, recolor its base-lighting effects to the section's LIGHTEST color at a bright level so
    the feature reads against the bed. Mutates in place; returns the list. No-op when no accent
    group is featured or the palette resolves to nothing."""
    featured = set(ACCENT_GROUPS) & set(section.target_groups or [])
    if not featured:
        return instructions
    light = _lightest_hex(getattr(section, "palette", None) or [])
    if not light:
        return instructions
    for ins in instructions:
        if ins.target in featured and ins.effect_type in FEATURE_BASE_EFFECTS:
            ins.palette_colors = [light]                       # the whitest section color
            cur = _slider_brightness(ins)
            if cur is None or cur < FEATURE_PROP_BRIGHTNESS:
                ins.extra_settings.update(brightness_setting(FEATURE_PROP_BRIGHTNESS))
    return instructions




def _bar_ms(rhythm: dict) -> float:
    bpb = rhythm.get("beats_per_bar") or BEATS_PER_BAR
    tempo = rhythm.get("tempo")
    if tempo:
        return bpb * 60000.0 / tempo
    beats = rhythm.get("beats_ms") or []
    if len(beats) > 4:
        deltas = [b - a for a, b in zip(beats, beats[1:])]
        deltas.sort()
        return bpb * deltas[len(deltas) // 2]
    return bpb * 2000.0


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
