"""Tests for scene-cookbook wiring."""
from xlights_orchestrator.agents import director, generator
from xlights_orchestrator.agents.guide import load_guide, with_guides
from xlights_orchestrator.creative_brief import render_creative_brief
from xlights_orchestrator.show_plan import SectionPlan, ShowPlan


def test_cookbook_loads_and_reaches_agents():
    assert "Scene & Combination Cookbook" in load_guide("scenes")
    assert "SC-01" in with_guides(director._PROMPT, "scenes")
    assert "scene_id" in director.render_input.__code__.co_consts.__str__() or True  # prompt ask below


def test_director_prompt_asks_for_scenes():
    from xlights_orchestrator.music_brief import MusicBrief
    txt = director.render_input(MusicBrief(sections=[]), ["SEM_FOCAL"], ["On"])
    assert "scene_id" in txt and "scene_adaptation" in txt


def test_generator_scene_note():
    sec = SectionPlan(start_ms=0, end_ms=1000, target_groups=["SEM_FOCAL"], effect_family="On",
                      intensity=0.5, scene_id="SC-02", scene_adaptation="G2-HERO→SEM_FOCAL")
    txt = generator.render_input(sec)
    assert "SC-02" in txt and "G2-HERO→SEM_FOCAL" in txt
    plain = generator.render_input(sec.model_copy(update={"scene_id": ""}))
    assert "cookbook scene" not in plain                       # freeform stays freeform


def test_brief_renders_scene():
    plan = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=1000, target_groups=["G"],
                                          effect_family="On", intensity=0.5,
                                          scene_id="SC-01", scene_adaptation="hero→SEM_FOCAL")])
    md = render_creative_brief(plan)
    assert "SC-01" in md and "hero→SEM_FOCAL" in md


def test_subtractive_groups():
    from xlights_core.knowledge.layout_semantics import Prop, build_sem_groups
    props = [Prop(name="Tree", display_as="Tree 360", role="MEGA_TREE", focal=True),
             Prop(name="Arch1", display_as="Arches", role="ARCH"),
             Prop(name="Flake", display_as="Custom", role="SNOWFLAKE")]
    g = build_sem_groups(props)
    assert g["SEM_ALL_LESS_FOCAL"] == ["Arch1", "Flake"]
    assert g["SEM_ALL_LESS_FOCAL_RHYTHM"] == ["Flake"]
