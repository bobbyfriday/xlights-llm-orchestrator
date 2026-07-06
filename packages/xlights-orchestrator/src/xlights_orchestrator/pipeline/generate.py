"""The generate stage: ShowPlan section directions -> placeable EffectInstruction[].

The LLM generator designs each section (effects + a cell-weave recipe); deterministic
code here realizes it — energy-gated coverage, palette/brightness/speed settings, the
ensemble bed / peak fill, the woven cell fabric, beat accents, curated triggers, climax
flashes and feature-prop contrast. Pulled out of run_pipeline so the orchestration hub
reads as a stage skeleton; caching stays with the caller.
"""

from __future__ import annotations

from ..agents import generator as generator_mod
from ..agents.guide import load_guide
from ..qa.rules import clamp_hard_caps
from ..show_plan import EffectInstruction, KeyMoment, SectionEffects
from .phrasing import tail_fade_settings
from xlights_core.audio import song_tail_envelope
from xlights_core.knowledge.value_curves import brightness_ramp, brightness_setting

from .beats import (
    effective_intensity,
    effect_palette,
    effect_speed_setting,
    ensemble_bed,
    feature_prop_contrast,
    key_moment_flashes,
    normalize_durations,
    peak_fill,
    peak_sections,
    place_beat_accents,
    place_vu_meter,
    section_is_rhythmic,
    section_rhythm,
    trim_coverage,
    wash_brightness,
)
from .features import instrument_entrances
from .meter import resolve_beats_per_bar
from .state import State
from .triggers import place_triggers
from .semantic_groups import HERO_GROUP
from .weave import (
    canon_effect_type,
    carrier_covers,
    curated_composite,
    diversify_carrier,
    expand_composite,
    expand_weave,
    fallback_weave,
    section_carrier,
)

# Curated composite stacks rotated across the show's peak(s) — a rich, kaleidoscopic feature
# look on the hero that one effect can't give (see weave.CURATED_COMPOSITES).
_PEAK_COMPOSITES = ("kaleidoscope", "swirl", "bloom", "ember")
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
    section = st.show_plan.sections[si]
    _peaks = peak_sections(st.show_plan)         # the show's payoff section(s)
    bpb = resolve_beats_per_bar(st.song_analysis, st.music_brief)   # the song's meter (default 4/4)
    motifs = {g: st.show_plan.group_motifs[g]
              for g in section.target_groups if g in st.show_plan.group_motifs}
    out: SectionEffects = (await agent.run(generator_mod.render_input(
        section, revision=revision, concept=st.show_plan.concept, motifs=motifs))).output
    _rm = st.music_brief.repetition_map if st.music_brief else None
    _si = effective_intensity(getattr(section, "intensity", 0.5), si, _rm)  # + escalation
    wash_b = wash_brightness(_si)            # energy → wash brightness
    rhythm = section_rhythm(st.song_analysis, section, bpb)
    kept = trim_coverage(list(out.instructions), _si)   # energy-gated coverage (quiet = fewer lit props)
    for ins in kept:
        ins.effect_type = canon_effect_type(ins.effect_type)   # 'Single Strand' → placeable
    kept = normalize_durations(kept, rhythm)      # hit effects pulse per bar, not smear
    for j, ins in enumerate(kept):
        ins.section_index = si              # tag for scoped regen / per-section QA
        if section.palette and not ins.palette_colors:   # LLM's explicit color (feature props) wins
            ins.palette_colors = effect_palette(section.palette, ins.effect_type, j)
        if _si >= 0.7 and ins.end_ms - ins.start_ms > 15000:   # long energetic wash BUILDS
            ins.extra_settings.update(brightness_ramp(0.7 * wash_b, wash_b))
        else:
            ins.extra_settings.update(brightness_setting(wash_b))
        ins.extra_settings.update(effect_speed_setting(ins.effect_type, _si))
    # the peak gets a FULL-bright whole-display fill (the lit payoff); merely-high
    # sections get the dim frame bed — the contrast is the escalation.
    bed = (peak_fill(section, _si, st.available_groups, kept) if si in _peaks
           else ensemble_bed(section, _si, st.available_groups, {k.target for k in kept}))
    if bed is not None:
        bed.section_index = si
        kept.append(bed)                 # occlusion order/blend handled by finalize_effects
    carrier = section_carrier(si)                # rotate the carrier so the show isn't all one effect
    weave_obj = getattr(out, "weave", None) or fallback_weave(section, st.available_groups,
                                                              carrier=carrier)
    diversify_carrier(weave_obj, carrier)        # vary an LLM weave's default carrier too
    woven = expand_weave(section, weave_obj, rhythm, _si, st.available_groups,
                         based_targets={k.target for k in kept})  # cells blend over washes
    for ins in woven:
        ins.section_index = si
    kept.extend(woven)                          # the cell fabric (LLM recipes or fallback)
    # composite stacks: LLM-designed multi-effect blended layers, plus a curated stack on the
    # hero at the peak — effects COMBINED on layers (e.g. counter-Morphs + Max) for a rich look.
    comp_recipes = list(getattr(out, "composites", None) or [])
    if si in _peaks and HERO_GROUP in st.available_groups:
        cc = curated_composite(_PEAK_COMPOSITES[si % len(_PEAK_COMPOSITES)], [HERO_GROUP])
        if cc is not None:
            comp_recipes.append(cc)
    for comp in comp_recipes:
        for ins in expand_composite(comp, section, _si, st.available_groups):
            ins.section_index = si
            kept.append(ins)
    vu = place_vu_meter(section, st.available_groups, _si, seed=si)   # music-reactive feature layer
    if vu is not None:
        vu.section_index = si
        kept.append(vu)
    clamp_hard_caps(kept, getattr(st.song_analysis, "tempo_overall", None))
    accents = place_beat_accents(            # beat layer over the wash; the weave's carrier
        section, rhythm, st.available_groups,  # owns the chase. Only when the brief is rhythmic —
        carrier_covers=carrier_covers(weave_obj, section, st.available_groups)) \
        if section_is_rhythmic(section) else []   # a still section stays still
    under = {k.target for k in kept}
    for ins in accents:
        ins.section_index = si
        if ins.target in under:                 # a pulse ADDS over its base, not occludes
            ins.extra_settings.setdefault("T_CHOICE_LayerMethod", "Max")
    kept.extend(accents)
    return kept


def finalize_effects(st: State, instrs: list[EffectInstruction]) -> list[EffectInstruction]:
    """Whole-list passes needed after ANY generation or section splice (idempotent):
    wash-occlusion layering (the 2:15 bug guard), sub-frame stretch (xLights silently
    drops effects shorter than a render frame), song-end stop+fade."""
    instrs = _guard_wash_occlusion(instrs)   # opaque washes sit under features; features blend Max
    for ins in instrs:
        if ins.end_ms - ins.start_ms < _MIN_EFFECT_MS:
            ins.end_ms = ins.start_ms + _MIN_EFFECT_MS
    # song-end: stop + fade the lights WITH the music (don't run past it to the file end)
    return song_end_fade(st, instrs)


async def generate_instructions(st: State, *, generator=None) -> list[EffectInstruction]:
    """Run the generator per section + the deterministic realization layers → instructions."""
    agent = generator or generator_mod.generator_agent()
    instrs: list[EffectInstruction] = []
    _peaks = peak_sections(st.show_plan)         # the show's payoff section(s)
    for i in range(len(st.show_plan.sections)):
        instrs.extend(await realize_section(st, i, agent=agent))
    # guarantee the climax SIGNAL lands at the peak: a peak section with no climax/accent
    # key-moment inside it gets one synthesized at its downbeat (drives key_moment_flashes).
    for pi in _peaks:
        sec = st.show_plan.sections[pi]
        if not any(sec.start_ms <= m.at_ms < sec.end_ms
                   and any(k in (m.kind or "").lower() for k in ("climax", "accent", "drop"))
                   for m in st.show_plan.key_moments):
            st.show_plan.key_moments.append(
                KeyMoment(at_ms=sec.start_ms, kind="climax", treatment="peak payoff"))
    # mid-section instrument entrances → surfaced as key moments + featured on the focal prop
    for _t, _stem in instrument_entrances(st.song_analysis):
        st.show_plan.key_moments.append(KeyMoment(at_ms=_t, kind="entrance",
                                                  treatment=f"{_stem} enters — feature it"))
    # curated trigger effects (cookbook-defined; folds in the entrance feature as the
    # `instrument_entrance` trigger — replaces the old instrument_feature_layer call).
    instrs += place_triggers(st.song_analysis, st.show_plan.sections, st.available_groups,
                             load_guide("triggers"))
    instrs += key_moment_flashes(st.show_plan, st.available_groups)   # white flash at climaxes
    for _i, _sec in enumerate(st.show_plan.sections):       # feature sparkle/snow props pop (white-on-bed)
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
