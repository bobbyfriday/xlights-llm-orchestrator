"""The generate stage: ShowPlan section directions -> placeable EffectInstruction[].

The LLM generator designs each section (effects + a cell-weave recipe); deterministic
code here realizes it — energy-gated coverage, palette/brightness/speed settings, the
ensemble bed / peak fill, the woven cell fabric, beat accents, curated triggers, climax
flashes and feature-prop contrast. Pulled out of run_pipeline so the orchestration hub
reads as a stage skeleton; caching stays with the caller.
"""

from __future__ import annotations

from .. import telemetry
from ..agents import generator as generator_mod
from ..agents.guide import load_guide
from ..models.registry import run_agent
from ..qa.rules import clamp_hard_caps
from ..show_plan import EffectInstruction, KeyMoment, SectionEffects
from .phrasing import tail_fade_settings
from xlights_core.audio import song_tail_envelope

from .beats import (
    effective_intensity,
    effect_palette,
    effect_speed_setting,
    ensemble_bed,
    feature_prop_contrast,
    key_moment_flashes,
    label_palette_offset,
    normalize_durations,
    occurrence_ordinal,
    peak_fill,
    peak_sections,
    place_beat_accents,
    place_vu_meter,
    resolve_treatment,
    section_energy_shape,
    section_identity,
    section_is_rhythmic,
    section_rhythm,
    trim_coverage,
    wash_brightness,
)
from .features import instrument_entrances
from .meter import resolve_beats_per_bar
from .state import State, require
from .triggers import place_triggers
from .semantic_groups import ACCENT_GROUPS, DEFAULT_VOCAB, HERO_GROUP
from .weave import (
    canon_effect_type,
    carrier_covers,
    curated_composite,
    diversify_carrier,
    expand_composite,
    expand_weave,
    fallback_weave,
    label_seed,
    section_carrier,
)

# Curated composite stacks rotated across the show's peak(s) — a rich, kaleidoscopic feature
# look on the hero that one effect can't give (see weave.CURATED_COMPOSITES).
_PEAK_COMPOSITES = ("kaleidoscope", "swirl", "bloom", "ember")
_FINAL_SPARKLE_EFFECT = "Twinkle"    # the extra contrast layer the LAST chorus gains (accent-prop pop)
_BED_WASH_EFFECTS = {"On", "Color Wash", "Fill", "Plasma"}   # sustained bases that carry phrase curves
_PHRASE_MIN_BARS = 2                  # only beds/washes ≥ this many bars get an energy-shaped curve


def _phrase_brightness(ins, shape: str, wash_b: float, bar_ms: float) -> dict[str, str]:
    """The brightness setting for a bed/wash, shaped by the section's energy slice (Phase 3):
    rising → an upward ramp (swell), falling → a downward ramp (decay), flat → a constant level
    (today's behavior). Only for sustained bed/wash effects spanning ≥ 2 bars; anything shorter or a
    non-bed effect gets a crisp constant level so features/accents stay punchy."""
    from xlights_core.knowledge.value_curves import brightness_ramp, brightness_setting
    long_enough = (ins.end_ms - ins.start_ms) >= _PHRASE_MIN_BARS * bar_ms
    if ins.effect_type not in _BED_WASH_EFFECTS or not long_enough:
        return brightness_setting(wash_b)
    if shape == "rising":
        return brightness_ramp(0.5 * wash_b, wash_b)     # swells with the music
    if shape == "falling":
        return brightness_ramp(wash_b, 0.5 * wash_b)     # decays with it
    return brightness_setting(wash_b)                    # flat → constant (unchanged behavior)

# Treatment → which realization LAYERS are included (withheld, not merely dimmed). See design table.
#   bed: "full" (energy bed / peak fill) | "dim" (a low ≤2-group bed) | "" (none)
_TREATMENT_LAYERS: dict[str, dict] = {
    "full":    {"bed": "full", "weave": True,  "accents": "full",   "extras": True,  "feature": True},
    "pulse":   {"bed": "full", "weave": False, "accents": "full",   "extras": False, "feature": True},
    "feature": {"bed": "dim",  "weave": False, "accents": "sparse", "extras": False, "feature": True},
    "gesture": {"bed": "",     "weave": "solo", "accents": "none",  "extras": False, "feature": False},
    "rest":    {"bed": "dim",  "weave": False, "accents": "none",   "extras": False, "feature": False},
}
_SPARSE_TREATMENTS = ("feature", "gesture", "rest")   # not full/pulse → no reliable base bed
_GESTURE_MAX_GROUPS = 2       # gesture/rest touch at most this many groups
_DIM_BED_BRIGHTNESS = 55.0    # the injected minimal bed for rest / the bed floor (dim, present)


def _dim_bed(section, available_groups: list[str], existing_targets, pal_offset: int):
    """A minimal, DIM base bed for feature/rest treatments (and the bed floor): one broad group lit
    low so the section reads as present-but-restrained rather than pitch-black. None when no broad
    group is free or the section already beds it."""
    from .beats import effect_palette
    from .semantic_groups import BED_PREFERENCE
    from ..agents.catalog import candidate_look_ids
    from xlights_core.knowledge.value_curves import brightness_setting
    target = next((g for g in BED_PREFERENCE
                   if g in (available_groups or []) and g not in (existing_targets or set())), None)
    if target is None:
        return None
    ins = EffectInstruction(
        target=target, effect_type="On", look_id=candidate_look_ids("On")[0],
        palette_colors=effect_palette(getattr(section, "palette", None) or [], "On", 1, pal_offset)
        or list(getattr(section, "palette", None) or []),
        start_ms=section.start_ms, end_ms=section.end_ms)
    ins.extra_settings.update(brightness_setting(_DIM_BED_BRIGHTNESS))
    return ins


def _gesture_weave(section, available_groups: list[str], carrier: str):
    """A `gesture` treatment's single held motion: ONE carrier recipe on ≤2 groups, nothing else."""
    from ..show_plan import CellRecipe, SectionWeave
    from .weave import rhythm_pool
    groups = [g for g in (section.target_groups or []) if g in (available_groups or [])] \
        or rhythm_pool(section, available_groups)
    groups = groups[:_GESTURE_MAX_GROUPS]
    if not groups:
        return None
    return SectionWeave(cells=[CellRecipe(
        effect_type=carrier, role="carrier", cell_beats=2, alternation="chase",
        direction="bounce", groups=groups)])


def _consecutive_bedless_run(plan, si: int, peaks: set[int], has_focal: bool) -> int:
    """How many consecutive BEDLESS sections (gesture, which carries no base bed) end AT `si`,
    inclusive. feature/rest already keep a dim bed; only `gesture` truly goes dark.

    Used for the bed floor: at most 2 consecutive sections may go without a base bed; the 3rd gets a
    minimal one injected so the show never fades to black for a whole stretch. Resolves each prior
    section's treatment the same way realize_section does (explicit → energy fallback)."""
    from .beats import resolve_treatment as _rt
    secs = list(getattr(plan, "sections", None) or [])
    run = 0
    for k in range(si, -1, -1):
        if _TREATMENT_LAYERS.get(_rt(secs[k], k in peaks, has_focal), {}).get("bed") == "":
            run += 1
        else:
            break
    return run


def _final_occurrence_layer(section, intensity: float, available_groups: list[str]):
    """The one EXTRA layer the FINAL occurrence of a recurring label gains (Phase 1 escalation):
    a bright sparkle pop on a dedicated accent prop group, in the section's lightest color, so the
    last chorus reads as the biggest. None when the layout has no accent prop group — the design's
    'when the layout has accent props' guard, keeping non-accent layouts unchanged."""
    from ..agents.catalog import candidate_look_ids
    from .beats import _lightest_hex
    from xlights_core.knowledge.value_curves import brightness_setting
    from .tuning import FEATURE_PROP_BRIGHTNESS
    target = next((g for g in ACCENT_GROUPS if g in (available_groups or [])), None)
    if target is None:
        return None
    looks = candidate_look_ids(_FINAL_SPARKLE_EFFECT)
    if not looks:
        return None
    light = _lightest_hex(getattr(section, "palette", None) or []) or "#FFFFFF"
    ins = EffectInstruction(
        target=target, effect_type=_FINAL_SPARKLE_EFFECT, look_id=looks[0],
        render_style="Per Model Default", palette_colors=[light],
        start_ms=section.start_ms, end_ms=section.end_ms)
    ins.extra_settings.update(brightness_setting(FEATURE_PROP_BRIGHTNESS))
    ins.extra_settings.setdefault("T_CHOICE_LayerMethod", "Max")   # pops over the bed, never occludes
    return ins
_MIN_EFFECT_MS = 50          # one render frame (seqStepTime); shorter effects snap away and drop
_OPAQUE_WASH = {"On", "Color Wash", "Fill"}   # solid fills that occlude unless they sit at the bottom
_WASH_SPAN_MS = 3000         # only a sustained wash counts as a "bed" for occlusion ordering


def _guard_wash_occlusion(instrs: list[EffectInstruction]) -> list[EffectInstruction]:
    """Stop opaque washes from cancelling features on the same group (the 2:15 bug, generalized).

    The emitter assigns layers by list order + each effect's start layer (later/higher = on top).
    So for every sustained opaque wash on a target: (a) overlapping features blend Max (neither the
    opaque bed nor a feature's black background occludes the other), and (b) a plain Normal bed has
    its layer reset to 0 and is emitted first, landing it on the BOTTOM under the features.
    Intentional blended washes (a Subtractive envelope, etc.) keep their layer and order."""
    by: dict[str, list[EffectInstruction]] = {}
    for i in instrs:
        by.setdefault(i.target, []).append(i)

    def is_wash(e):
        return e.effect_type in _OPAQUE_WASH and e.end_ms - e.start_ms >= _WASH_SPAN_MS

    sink: set[int] = set()
    for effs in by.values():
        washes = [e for e in effs if is_wash(e)]
        if not washes:
            continue
        for f in effs:
            if not is_wash(f) and any(not (f.end_ms <= w.start_ms or f.start_ms >= w.end_ms)
                                      for w in washes):
                f.extra_settings.setdefault("T_CHOICE_LayerMethod", "Max")
        for w in washes:
            if not w.extra_settings.get("T_CHOICE_LayerMethod"):   # a plain Normal bed
                w.layer = 0
                sink.add(id(w))
    return sorted(instrs, key=lambda e: 0 if id(e) in sink else 1)


def _merge_fade_out(ins: EffectInstruction, fade_s: float) -> None:
    """Merge a song-end fade-out into an effect, keeping the LONGER of any existing fade-out."""
    for k, v in tail_fade_settings(ins.effect_type, fade_s).items():
        if k == "T_TEXTCTRL_Fadeout":
            try:
                if float(ins.extra_settings.get(k, 0)) >= float(v):
                    continue                          # an existing longer fade already covers it
            except (TypeError, ValueError):
                pass
        ins.extra_settings[k] = v


def apply_song_end_fade(
    instrs: list[EffectInstruction], fade_start_ms: int, music_end_ms: int,
    *, final_section_start_ms: int | None = None,
) -> list[EffectInstruction]:
    """Trim effects to the music's end and fade the song tail (deterministic, idempotent).

    Effects past `music_end_ms` are trimmed there (lights stop when the music stops); those left
    below one render frame are dropped. Effects overlapping `[fade_start_ms, music_end_ms]` get an
    opacity fade-out scaled to their portion of that region (lights dim with the music). `music_end`
    is floored so it can never collapse the final section below a frame.
    """
    music_end_ms, fade_start_ms = int(music_end_ms), int(fade_start_ms)
    if final_section_start_ms is not None:
        music_end_ms = max(music_end_ms, int(final_section_start_ms) + _MIN_EFFECT_MS)
    out: list[EffectInstruction] = []
    for ins in instrs:
        if ins.start_ms >= music_end_ms:                  # entirely in the silent tail → drop
            continue
        if ins.end_ms > music_end_ms:                     # overshoots the music → trim to its end
            ins.end_ms = music_end_ms
        if ins.end_ms - ins.start_ms < _MIN_EFFECT_MS:    # collapsed below a frame → drop
            continue
        if ins.end_ms > fade_start_ms:                    # overlaps the trailing region → fade out
            fade_s = (ins.end_ms - max(ins.start_ms, fade_start_ms)) / 1000.0
            fade_s = min(fade_s, (ins.end_ms - ins.start_ms) / 1000.0)
            if fade_s > 0:
                _merge_fade_out(ins, fade_s)
        out.append(ins)
    return out


def song_end_fade(st: State, instrs: list[EffectInstruction]) -> list[EffectInstruction]:
    """Apply the song-end envelope fade for a State (envelope → trim + fade). Idempotent."""
    sa = st.song_analysis
    fade_start_s, music_end_s = song_tail_envelope(
        getattr(sa, "energy_arc", None), getattr(sa, "duration_s", 0.0))
    final_start = (st.show_plan.sections[-1].start_ms
                   if (st.show_plan and st.show_plan.sections) else None)
    return apply_song_end_fade(instrs, int(fade_start_s * 1000), int(music_end_s * 1000),
                               final_section_start_ms=final_start)


async def realize_section(st: State, si: int, *, agent,
                          revision=None) -> list[EffectInstruction]:
    """The deterministic per-section realization — generator design → energy-gated coverage,
    palette/brightness/speed, bed or peak fill, carrier-rotated weave, composite stacks, VU
    meter, hard caps, beat accents. SHARED by first-pass generation, the refine loop, and
    `xlo regen`, so a regenerated section is realized exactly like a first-pass one.
    Every instruction is tagged with `si`."""
    plan = require(st.show_plan, "show_plan")
    section = plan.sections[si]
    _peaks = peak_sections(plan)         # the show's payoff section(s)
    bpb = resolve_beats_per_bar(st.song_analysis, st.music_brief)   # the song's meter (default 4/4)
    motifs = {g: plan.group_motifs[g]
              for g in section.target_groups if g in plan.group_motifs}
    _gen_res = await run_agent(agent, generator_mod.render_input(
        section, revision=revision, concept=plan.concept, motifs=motifs),
        role="generator", attempts=3)
    telemetry.record("generator", _gen_res)
    out: SectionEffects = _gen_res.output
    _rm = st.music_brief.repetition_map if st.music_brief else None
    _si = effective_intensity(getattr(section, "intensity", 0.5), si, _rm)  # + escalation
    _label = section_identity(si, _rm)       # the section's musical identity (chorus/verse/…) or None
    _ordinal, _count = occurrence_ordinal(si, _rm)   # which occurrence this is (0-based) + how many
    _is_final = _count > 1 and _ordinal == _count - 1  # the last chorus is the biggest
    _pal_offset = label_palette_offset(_label)   # a chorus rhymes its palette ORDER across occurrences
    # TREATMENT (Phase 2): the texture archetype deciding which LAYERS run (withheld, not dimmed).
    _has_focal = HERO_GROUP in st.available_groups
    _treatment = resolve_treatment(section, si in _peaks, _has_focal)
    _layers = _TREATMENT_LAYERS[_treatment]
    wash_b = wash_brightness(_si)            # energy → wash brightness
    rhythm = section_rhythm(st.song_analysis, section, bpb)
    _shape = section_energy_shape(st.song_analysis, section)   # rising/falling/flat → phrase curves
    from .beats import _bar_ms as _bar_ms_fn
    _bar_ms = _bar_ms_fn(rhythm)
    # STRUCTURAL escalation: each later occurrence of a recurring label lights +1 more prop group
    # (bounded by the section's own targets in coverage_cap) — the last chorus is visibly fuller.
    kept = trim_coverage(list(out.instructions), _si, _ordinal)   # energy-gated + occurrence bonus
    # sparse treatments withhold coverage: gesture/rest touch ≤2 groups, feature spotlights one hero.
    if _treatment in ("gesture", "rest"):
        _keep = {i.target for i in kept[:_GESTURE_MAX_GROUPS]}
        kept = [i for i in kept if i.target in _keep]
    for ins in kept:
        ins.effect_type = canon_effect_type(ins.effect_type)   # 'Single Strand' → placeable
    kept = normalize_durations(kept, rhythm)      # hit effects pulse per bar, not smear
    for j, ins in enumerate(kept):
        ins.section_index = si              # tag for scoped regen / per-section QA
        ins.source = "generator"            # provenance (I7; excluded from dump — report-only)
        if section.palette and not ins.palette_colors:   # LLM's explicit color (feature props) wins
            ins.palette_colors = effect_palette(section.palette, ins.effect_type, j, _pal_offset)
        # PHRASE DYNAMICS (Phase 3): a ≥2-bar bed/wash carries a brightness curve shaped by the
        # section's own energy slice (rising swells, falling decays, flat holds); features/accents
        # keep crisp constant levels. Supersedes the old ">15s energetic wash builds" special case.
        ins.extra_settings.update(_phrase_brightness(ins, _shape, wash_b, _bar_ms))
        ins.extra_settings.update(effect_speed_setting(ins.effect_type, _si))
    # BED, per treatment: full/pulse get the energy bed (or peak fill at the peak); feature/rest get
    # a dim ≤2-group bed; gesture gets none — UNLESS the bed floor trips (>2 consecutive bedless
    # sections would go dark), in which case a minimal bed is injected so the show never blacks out.
    _bed_mode = _layers["bed"]
    if _bed_mode == "" and _consecutive_bedless_run(st.show_plan, si, _peaks, _has_focal) > 2:
        _bed_mode = "dim"                    # the hard floor: at most 2 consecutive bedless sections
    if _bed_mode == "full":
        bed = (peak_fill(section, _si, st.available_groups, kept) if si in _peaks
               else ensemble_bed(section, _si, st.available_groups, {k.target for k in kept}))
    elif _bed_mode == "dim":
        bed = _dim_bed(section, st.available_groups, {k.target for k in kept}, _pal_offset)
    else:
        bed = None
    if bed is not None:
        bed.section_index = si
        bed.source = "bed"
        kept.append(bed)                 # occlusion order/blend handled by finalize_effects
    # WEAVE, per treatment: full weaves the whole fabric; gesture runs ONE carrier recipe on ≤2
    # groups (a single held motion); pulse/feature/rest withhold the fabric entirely.
    carrier = section_carrier(si, _label)   # keyed to the repetition identity (rhymes) else the index
    if _layers["weave"] is True:
        weave_obj = getattr(out, "weave", None) or fallback_weave(section, st.available_groups,
                                                                  carrier=carrier)
        diversify_carrier(weave_obj, carrier)    # vary an LLM weave's default carrier too
    elif _layers["weave"] == "solo":
        weave_obj = _gesture_weave(section, st.available_groups, carrier)
    else:
        weave_obj = None
    woven = expand_weave(section, weave_obj, rhythm, _si, st.available_groups,
                         based_targets={k.target for k in kept},   # cells blend over washes
                         bed_preference=(st.vocab or DEFAULT_VOCAB).bed_preference) if weave_obj else []
    for ins in woven:
        ins.section_index = si
        ins.source = "weave"
    kept.extend(woven)                          # the cell fabric (LLM recipes or fallback)
    # composite stacks + VU are "extras" (full only): LLM-designed multi-effect blended layers plus
    # the curated hero stack at the peak, and the music-reactive VU feature texture.
    if _layers["extras"]:
        comp_recipes = list(getattr(out, "composites", None) or [])
        if si in _peaks and HERO_GROUP in st.available_groups:
            # the peak composite is keyed to the section's identity when it recurs (every chorus-peak
            # gets the SAME curated stack), else to the index — same rhyme rule as the carrier.
            comp_seed = label_seed(_label) if _label else si
            cc = curated_composite(_PEAK_COMPOSITES[comp_seed % len(_PEAK_COMPOSITES)], [HERO_GROUP])
            if cc is not None:
                comp_recipes.append(cc)
        for comp in comp_recipes:
            for ins in expand_composite(comp, section, _si, st.available_groups):
                ins.section_index = si
                ins.source = "composite"      # provenance (report-only)
                kept.append(ins)
        vu = place_vu_meter(section, st.available_groups, _si, seed=si)   # music-reactive feature
        if vu is not None:
            vu.section_index = si
            vu.source = "vu"
            kept.append(vu)
    # the FINAL occurrence of a recurring label gains one extra layer: a sparkle-contrast pop on
    # an accent prop group (when the layout has one), so the last chorus reads as the biggest.
    if _is_final and _layers["feature"]:
        final_layer = _final_occurrence_layer(section, _si, st.available_groups)
        if final_layer is not None:
            final_layer.section_index = si
            final_layer.source = "feature"    # provenance (report-only)
            kept.append(final_layer)
    clamp_hard_caps(kept, getattr(st.song_analysis, "tempo_overall", None))
    # ACCENTS, per treatment: full/pulse get the full beat layer, feature a sparse one, gesture/rest
    # none (the held breath stays still). A still (non-rhythmic) section never gets accents either.
    _accent_mode = _layers["accents"]
    if _accent_mode != "none" and section_is_rhythmic(section):
        accents = place_beat_accents(
            section, rhythm, st.available_groups,
            carrier_covers=carrier_covers(weave_obj, section, st.available_groups),
            stride_step=_ordinal if _accent_mode == "full" else -1,   # -1 sparsens a feature
            vocab=st.vocab or DEFAULT_VOCAB)
    else:
        accents = []
    under = {k.target for k in kept}
    for ins in accents:
        ins.section_index = si
        ins.source = "accents"
        if ins.target in under:                 # a pulse ADDS over its base, not occludes
            ins.extra_settings.setdefault("T_CHOICE_LayerMethod", "Max")
    kept.extend(accents)
    return kept


def finalize_effects(st: State, instrs: list[EffectInstruction]) -> list[EffectInstruction]:
    """Whole-list passes needed after ANY generation or section splice (idempotent):
    boundary transitions (risers/blackouts/sweeps), wash-occlusion layering (the 2:15 bug guard),
    sub-frame stretch (xLights silently drops effects shorter than a render frame), song-end
    stop+fade.

    Transitions run FIRST (before the occlusion guard sees final geometry) and are idempotent, so a
    regenerated section that re-runs finalize replaces its boundary transitions rather than stacking
    them — the pass owns the OUTGOING section's time range, so regenerating the incoming section
    never orphans them."""
    from .transitions import place_transitions
    instrs = place_transitions(st, instrs)   # composed section joins from energy arc + downbeats + cues
    instrs = _guard_wash_occlusion(instrs)   # opaque washes sit under features; features blend Max
    for ins in instrs:
        if ins.end_ms - ins.start_ms < _MIN_EFFECT_MS:
            ins.end_ms = ins.start_ms + _MIN_EFFECT_MS
    # song-end: stop + fade the lights WITH the music (don't run past it to the file end)
    return song_end_fade(st, instrs)


async def generate_instructions(st: State, *, generator=None) -> list[EffectInstruction]:
    """Run the generator per section + the deterministic realization layers → instructions."""
    agent = generator or generator_mod.generator_agent()
    plan = require(st.show_plan, "show_plan")
    instrs: list[EffectInstruction] = []
    _peaks = peak_sections(plan)         # the show's payoff section(s)
    for i in range(len(plan.sections)):
        instrs.extend(await realize_section(st, i, agent=agent))
    # guarantee the climax SIGNAL lands at the peak: a peak section with no climax/accent
    # key-moment inside it gets one synthesized at its downbeat (drives key_moment_flashes).
    for pi in _peaks:
        sec = plan.sections[pi]
        if not any(sec.start_ms <= m.at_ms < sec.end_ms
                   and any(k in (m.kind or "").lower() for k in ("climax", "accent", "drop"))
                   for m in plan.key_moments):
            plan.key_moments.append(
                KeyMoment(at_ms=sec.start_ms, kind="climax", treatment="peak payoff"))
    # mid-section instrument entrances → surfaced as key moments + featured on the focal prop
    for _t, _stem in instrument_entrances(st.song_analysis):
        plan.key_moments.append(KeyMoment(at_ms=_t, kind="entrance",
                                          treatment=f"{_stem} enters — feature it"))
    # curated trigger effects (cookbook-defined; folds in the entrance feature as the
    # `instrument_entrance` trigger — replaces the old instrument_feature_layer call).
    _triggers = place_triggers(st.song_analysis, plan.sections, st.available_groups,
                               load_guide("triggers"))
    for ins in _triggers:
        ins.source = ins.source or "triggers"        # provenance (I7; report-only)
    instrs += _triggers
    _flashes = key_moment_flashes(plan, st.available_groups)   # white flash at climaxes
    for ins in _flashes:
        ins.source = ins.source or "flash"
    instrs += _flashes
    for _i, _sec in enumerate(plan.sections):       # feature sparkle/snow props pop (white-on-bed)
        feature_prop_contrast([x for x in instrs if x.section_index == _i], _sec)
    instrs = place_matrix_narrative(st, instrs)             # sparse narrative Text on the matrix (F-C)
    return finalize_effects(st, instrs)


def place_matrix_narrative(st: State, instrs: list[EffectInstruction]) -> list[EffectInstruction]:
    """Append F-C narrative Text on the matrix model to `instrs` (idempotent: drops any prior
    matrix-text before re-placing, so refine/regen splices reproduce exactly one copy per moment).

    `place_matrix_text` reads/dims the existing matrix background in `st.instructions`, so point
    that at the working list for the duration of the pass. No matrix / no grounded text → no-op."""
    from .matrix_text import find_matrix, place_matrix_text, strip_matrix_text
    instrs = strip_matrix_text(instrs)
    matrix = find_matrix(getattr(st, "model_names", None))
    if matrix is None:
        return instrs
    prior = st.instructions
    st.instructions = instrs
    try:
        text = place_matrix_text(st, matrix)
    finally:
        st.instructions = prior
    return instrs + text
