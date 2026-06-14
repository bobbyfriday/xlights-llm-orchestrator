"""The director/generator prompts steer featured sparkle/snow props to pop (white-on-blue)."""

from __future__ import annotations

from xlights_orchestrator.agents import director, generator
from xlights_orchestrator.music_brief import MusicBrief
from xlights_orchestrator.show_plan import SectionPlan


def test_director_prompt_steers_feature_props_to_pop():
    txt = director.render_input(MusicBrief(sections=[]), ["SEM_SNOWFLAKES", "SEM_ALL"], ["On", "Twinkle"])
    assert "FEATURE PROPS POP" in txt
    assert "white snowflakes on a blue house" in txt


def test_generator_prompt_steers_feature_props_and_particle_caveat():
    sec = SectionPlan(start_ms=0, end_ms=1000, target_groups=["SEM_SNOWFLAKES"],
                      effect_family="On", intensity=0.3)
    txt = generator.render_input(sec)
    assert "FEATURE PROPS POP" in txt
    assert "light the PROPS directly" in txt            # the particle-effect caveat
    assert "Snowflakes/Snowstorm/Meteors" in txt
    assert "palette_colors" in txt                       # pin-the-color instruction


def test_run_color_pass_respects_explicit_palette_colors():
    """run.py fills palette_colors from the section family ONLY when the instruction left it empty,
    so an LLM-pinned feature color (white snow) survives the override."""
    from xlights_orchestrator.pipeline.beats import effect_palette
    from xlights_orchestrator.show_plan import EffectInstruction

    section_palette = ["deep blue", "cool white", "silver"]
    pinned = EffectInstruction(target="SEM_SNOWFLAKES", effect_type="On", look_id="",
                               start_ms=0, end_ms=1000, palette_colors=["white"])
    unpinned = EffectInstruction(target="SEM_ALL", effect_type="On", look_id="",
                                 start_ms=0, end_ms=1000)

    # the exact run.py guard: `if section.palette and not ins.palette_colors:`
    for j, ins in enumerate([unpinned, pinned]):
        if section_palette and not ins.palette_colors:
            ins.palette_colors = effect_palette(section_palette, ins.effect_type, j)

    assert pinned.palette_colors == ["white"]            # LLM's pin survives
    assert unpinned.palette_colors and unpinned.palette_colors != ["white"]   # took the section family


def test_feature_prop_floor_recolors_snow_to_lightest_and_brightens():
    from xlights_orchestrator.pipeline.beats import feature_prop_contrast, FEATURE_PROP_BRIGHTNESS
    from xlights_core.knowledge.colors import _resolve, _luminance
    from xlights_orchestrator.show_plan import EffectInstruction

    sec = SectionPlan(start_ms=0, end_ms=1000, target_groups=["SEM_ALL", "SEM_SNOWFLAKES"],
                      effect_family="On", intensity=0.2, palette=["deep blue", "cool white", "silver"])
    snow = EffectInstruction(target="SEM_SNOWFLAKES", effect_type="On", look_id="",
                             start_ms=0, end_ms=1000)
    bed = EffectInstruction(target="SEM_ALL", effect_type="On", look_id="",
                            start_ms=0, end_ms=1000, palette_colors=["#00008B"])
    feature_prop_contrast([snow, bed], sec)

    lightest = max((_resolve(c) for c in sec.palette), key=_luminance)
    assert snow.palette_colors == [lightest]                     # the whitest section color
    assert float(snow.extra_settings["C_SLIDER_Brightness"]) >= FEATURE_PROP_BRIGHTNESS
    assert bed.palette_colors == ["#00008B"]                     # the bed (not an accent group) is untouched


def test_feature_prop_floor_noop_without_accent_group():
    from xlights_orchestrator.pipeline.beats import feature_prop_contrast
    from xlights_orchestrator.show_plan import EffectInstruction

    sec = SectionPlan(start_ms=0, end_ms=1000, target_groups=["SEM_ALL", "SEM_ARCHES"],
                      effect_family="On", intensity=0.8, palette=["red", "white"])
    ins = EffectInstruction(target="SEM_ARCHES", effect_type="On", look_id="", start_ms=0, end_ms=1000)
    feature_prop_contrast([ins], sec)
    assert not ins.palette_colors                                # no accent group featured → untouched
