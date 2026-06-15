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
    section_is_rhythmic,
    section_rhythm,
    trim_coverage,
    wash_brightness,
)
from .features import instrument_entrances
from .state import State
from .triggers import place_triggers
from .weave import canon_effect_type, carrier_covers, expand_weave, fallback_weave


async def generate_instructions(st: State, *, generator=None) -> list[EffectInstruction]:
    """Run the generator per section + the deterministic realization layers → instructions."""
    agent = generator or generator_mod.generator_agent()
    instrs: list[EffectInstruction] = []
    _peaks = peak_sections(st.show_plan)         # the show's payoff section(s)
    for i, section in enumerate(st.show_plan.sections):
        motifs = {g: st.show_plan.group_motifs[g]
                  for g in section.target_groups if g in st.show_plan.group_motifs}
        out: SectionEffects = (await agent.run(generator_mod.render_input(
            section, concept=st.show_plan.concept, motifs=motifs))).output
        _rm = st.music_brief.repetition_map if st.music_brief else None
        _si = effective_intensity(getattr(section, "intensity", 0.5), i, _rm)  # + escalation
        wash_b = wash_brightness(_si)            # energy → wash brightness
        rhythm = section_rhythm(st.song_analysis, section)
        kept = trim_coverage(out.instructions, _si)   # energy-gated coverage (quiet = fewer lit props)
        for ins in kept:
            ins.effect_type = canon_effect_type(ins.effect_type)   # 'Single Strand' → placeable
        kept = normalize_durations(kept, rhythm)      # hit effects pulse per bar, not smear
        for j, ins in enumerate(kept):
            ins.section_index = i               # tag for scoped regen / per-section QA
            if section.palette and not ins.palette_colors:   # LLM's explicit color (feature props) wins
                ins.palette_colors = effect_palette(section.palette, ins.effect_type, j)
            if _si >= 0.7 and ins.end_ms - ins.start_ms > 15000:   # long energetic wash BUILDS
                ins.extra_settings.update(brightness_ramp(0.7 * wash_b, wash_b))
            else:
                ins.extra_settings.update(brightness_setting(wash_b))
            ins.extra_settings.update(effect_speed_setting(ins.effect_type, _si))
        # the peak gets a FULL-bright whole-display fill (the lit payoff); merely-high
        # sections get the dim frame bed — the contrast is the escalation.
        bed = (peak_fill(section, _si, st.available_groups, kept) if i in _peaks
               else ensemble_bed(section, _si, st.available_groups, {k.target for k in kept}))
        if bed is not None:
            bed.section_index = i
            kept.append(bed)
        weave_obj = getattr(out, "weave", None) or fallback_weave(section, st.available_groups)
        woven = expand_weave(section, weave_obj, rhythm, _si, st.available_groups,
                             based_targets={k.target for k in kept})  # cells blend over washes
        for ins in woven:
            ins.section_index = i
        kept.extend(woven)                          # the cell fabric (LLM recipes or fallback)
        clamp_hard_caps(kept, getattr(st.song_analysis, "tempo_overall", None))
        instrs.extend(kept)
        accents = place_beat_accents(            # beat layer over the wash; the weave's carrier
            section, rhythm, st.available_groups,  # owns the chase. Only when the brief is rhythmic —
            carrier_covers=carrier_covers(weave_obj, section, st.available_groups)) \
            if section_is_rhythmic(section) else []   # a still section stays still
        under = {k.target for k in kept}
        for ins in accents:
            ins.section_index = i
            if ins.target in under:                 # a pulse ADDS over its base, not occludes
                ins.extra_settings.setdefault("T_CHOICE_LayerMethod", "Max")
        instrs.extend(accents)
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
    return instrs
