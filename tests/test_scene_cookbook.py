"""Tests for scene-cookbook wiring."""
from xlights_orchestrator.pipeline.cookbook import load_guide, scene_ids


def test_cookbook_loads():
    assert "Scene & Combination Cookbook" in load_guide("scenes")
    assert "SC-01" in scene_ids()


def test_subtractive_groups():
    from xlights_core.knowledge.layout_semantics import Prop, build_sem_groups
    props = [Prop(name="Tree", display_as="Tree 360", role="MEGA_TREE", focal=True),
             Prop(name="Arch1", display_as="Arches", role="ARCH"),
             Prop(name="Flake", display_as="Custom", role="SNOWFLAKE")]
    g = build_sem_groups(props)
    assert g["SEM_ALL_LESS_FOCAL"] == ["Arch1", "Flake"]
    assert g["SEM_ALL_LESS_FOCAL_RHYTHM"] == ["Flake"]
