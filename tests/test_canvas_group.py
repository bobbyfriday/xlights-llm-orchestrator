"""The hero is the mega tree; matrixes form SEM_CANVAS (a tree + eight screens is not one hero)."""

from __future__ import annotations

from xlights_core.knowledge.layout_classify import derive_spatial
from xlights_core.knowledge.layout_semantics import Prop, build_sem_groups, canonical_order


def _props(with_tree: bool):
    ps = [Prop(name=f"Matrix {i}", display_as="Matrix", role="MATRIX", res="2D_SURFACE",
               nodes=4000 + i, wx=100.0 * i, wy=50.0) for i in range(3)]
    ps += [Prop(name="Arch 1", display_as="Arches", role="ARCH", nodes=50, wx=0.0, wy=0.0),
           Prop(name="Arch 2", display_as="Arches", role="ARCH", nodes=50, wx=300.0, wy=0.0)]
    if with_tree:
        ps.append(Prop(name="Tree", display_as="Tree 360", role="MEGA_TREE", res="2D_RADIAL",
                       nodes=3000, wx=150.0, wy=100.0))
    return ps


def test_mega_tree_is_the_hero_and_matrixes_are_the_canvas():
    ps = _props(with_tree=True)
    derive_spatial(ps)
    g = build_sem_groups(ps)
    assert g["SEM_FOCAL"] == ["Tree"]                      # the densest matrix is not a hero
    assert g["SEM_CANVAS"] == ["Matrix 0", "Matrix 1", "Matrix 2"]
    assert set(g["SEM_CANVAS"]) <= set(g["SEM_ALL_LESS_FOCAL"])
    assert not set(g["SEM_CANVAS"]) & set(g["SEM_ACCENTS"])   # screens are not sparkle props


def test_without_a_tree_the_matrixes_are_the_hero():
    ps = _props(with_tree=False)
    derive_spatial(ps)
    g = build_sem_groups(ps)
    assert g["SEM_FOCAL"] == g["SEM_CANVAS"] == ["Matrix 0", "Matrix 1", "Matrix 2"]


def test_canvas_renders_with_the_focal_tier():
    order = canonical_order(["SEM_CANVAS", "SEM_ALL", "SEM_ARCHES", "SEM_SNOWFLAKES"])
    assert order == ["SEM_ALL", "SEM_ARCHES", "SEM_CANVAS", "SEM_SNOWFLAKES"]


def test_scene_canvas_casts_to_sem_canvas():
    from xlights_orchestrator.pipeline.scenes import default_cast
    cast = default_cast(["G2-HERO", "G2-CANVAS"], None, ["SEM_FOCAL", "Matrixes", "SEM_CANVAS"])
    assert cast == {"G2-HERO": "SEM_FOCAL", "G2-CANVAS": "SEM_CANVAS"}
    assert default_cast(["G2-CANVAS"], None, ["Matrixes"]) == {"G2-CANVAS": "Matrixes"}


def test_hero_scene_echoes_one_layer_on_the_canvas():
    from xlights_orchestrator.pipeline.scenes import cast_scene, parse_scene_stack
    from xlights_orchestrator.show_plan import SectionPlan
    groups = ["SEM_FOCAL", "SEM_CANVAS", "SEM_ALL_LESS_FOCAL"]
    sec = SectionPlan(start_ms=0, end_ms=8000, target_groups=["SEM_FOCAL", "SEM_CANVAS"],
                      effect_family="Spirals", intensity=0.7, scene_id="SC-02",
                      palette=["crimson", "orange", "royal purple"])
    rows = cast_scene(sec, parse_scene_stack("SC-02"), groups)
    hero = [r for r in rows if r.target == "SEM_FOCAL"]
    canvas = [r for r in rows if r.target == "SEM_CANVAS"]
    assert len(hero) == 2 and len(canvas) == 1                 # the pair on the tree, one echo
    assert canvas[0].effect_type == "Spirals" and canvas[0].render_style == "Per Model Default"
    assert "T_CHOICE_LayerMethod" not in canvas[0].extra_settings
    quiet = sec.model_copy(update={"target_groups": ["SEM_FOCAL"]})
    assert not [r for r in cast_scene(quiet, parse_scene_stack("SC-02"), groups)
                if r.target == "SEM_CANVAS"]                    # opt-in via target_groups
