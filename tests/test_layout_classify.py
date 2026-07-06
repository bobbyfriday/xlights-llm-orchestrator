"""F-E slice 1 — classifier + spatial derivation (spec §3/§4).

Table-driven against authored fixtures (layout_basic.xml, layout_tricky.xml), never from memory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xlights_core.knowledge.layout_classify import (
    capability,
    classify,
    derive_spatial,
    parse_props,
)
from xlights_core.knowledge.layout_semantics import Prop

FIX = Path(__file__).parent / "fixtures"


def _by_name(props):
    return {p.name: p for p in props}


# -- parse_props --------------------------------------------------------------------------------
def test_parse_props_basic_counts_and_fields():
    props = parse_props(FIX / "layout_basic.xml")
    assert len(props) == 15   # 1 tree + 6 arches + 4 canes + 2 outline + 1 window + 1 snowflake
    by = _by_name(props)
    # node count: Tree 360 → parm1*parm2 = 16*100 = 1600
    assert by["Mega Tree"].nodes == 1600
    # Custom → grid max token
    assert by["Snowflake 1"].nodes == 9
    # group membership reverse-indexed (SEM_ groups would be excluded, none here)
    assert by["Arch L1"].groups == ["All Arches"]
    # StringType captured
    assert by["Mega Tree"].string_type == "RGB Nodes"


def test_parse_props_excludes_non_default_layout_group():
    props = parse_props(FIX / "layout_tricky.xml")
    assert "Garage Preview" not in _by_name(props)      # LayoutGroup="Garage" excluded (spec §8)
    assert "Yard Tree" in _by_name(props)


# -- classify: step 1 DisplayAs map -------------------------------------------------------------
@pytest.mark.parametrize("display_as,role", [
    ("Arches", "ARCH"), ("Icicles", "ICICLES"), ("Candy Canes", "CANE"), ("Star", "STAR"),
    ("Spinner", "SPINNER"), ("Matrix", "MATRIX"), ("Horiz Matrix", "MATRIX"),
    ("Vert Matrix", "MATRIX"), ("Window Frame", "WINDOW"),
])
def test_displayas_map(display_as, role):
    p = Prop(name="x", display_as=display_as, nodes=50)
    res = classify([p])
    assert res.props[0].role == role and res.props[0].confidence == 1.0


# -- classify: step 2 tree threshold ------------------------------------------------------------
@pytest.mark.parametrize("nodes,expect", [(599, "MINI_TREE"), (600, "MEGA_TREE"), (601, "MEGA_TREE")])
def test_tree_threshold(nodes, expect):
    # two trees present so the "sole-largest" rule doesn't kick in for the small one
    trees = [Prop(name="A", display_as="Tree 360", nodes=nodes),
             Prop(name="B", display_as="Tree 360", nodes=700)]
    res = classify(trees)
    assert res.props[0].role == expect


def test_sole_small_tree_is_mega():
    res = classify([Prop(name="Only", display_as="Tree Flat", nodes=400),
                    Prop(name="Arch", display_as="Arches", nodes=25)])
    assert _by_name(res.props)["Only"].role == "MEGA_TREE"      # sole tree + largest → mega


# -- classify: step 3 name heuristics -----------------------------------------------------------
@pytest.mark.parametrize("name,role", [
    ("Roof Line", "OUTLINE"), ("Gutter", "OUTLINE"), ("Garage Door Frame", "OUTLINE"),
    ("Front Window", "WINDOW"), ("Flood 1", "FLOOD"), ("Up Light", "FLOOD"),
    ("Singing Tree", "SINGING_FACE"), ("Tune To Sign", "SIGN"), ("Driveway", "PATH"),
    ("Big Flake", "SNOWFLAKE"),
])
def test_name_heuristics(name, role):
    p = Prop(name=name, display_as="Single Line", nodes=20)
    res = classify([p])
    assert res.props[0].role == role and res.props[0].confidence == 0.9


def test_group_hint_inheritance():
    p = Prop(name="Unclear", display_as="Single Line", nodes=20, groups=["All Outline"])
    res = classify([p])
    assert res.props[0].role == "OUTLINE" and res.props[0].confidence == 0.85


def test_unresolved_defaults_to_custom_prop_for_review():
    p = Prop(name="Weird Thing", display_as="Poly Line", nodes=15)
    res = classify([p])
    assert res.props[0].role == "CUSTOM_PROP" and res.props[0].confidence == 0.5
    assert res.unresolved == [res.props[0]]


# -- capability matrix --------------------------------------------------------------------------
@pytest.mark.parametrize("role,nodes,st,expect", [
    ("MATRIX", 1000, "RGB Nodes", "2D_SURFACE"),
    ("MEGA_TREE", 1600, "RGB Nodes", "2D_RADIAL"),
    ("SPINNER", 100, "RGB Nodes", "2D_RADIAL"),
    ("STAR", 50, "RGB Nodes", "2D_RADIAL"),
    ("OUTLINE", 100, "RGB Nodes", "LINEAR_HIGH"),      # cut at 100
    ("OUTLINE", 99, "RGB Nodes", "LINEAR_LOW"),
    ("PATH", 150, "RGB Nodes", "LINEAR_HIGH"),
    ("ARCH", 25, "RGB Nodes", "LINEAR_LOW"),
    ("CANE", 30, "RGB Nodes", "LINEAR_LOW"),
    ("SINGING_FACE", 50, "RGB Nodes", "SPECIAL"),
    ("FLOOD", 3, "RGB Nodes", "POINT"),
    ("CUSTOM_PROP", 10, "RGB Nodes", "POINT"),
    ("CUSTOM_PROP", 500, "RGB Nodes", "2D_SURFACE"),   # dense Custom → matrix
    ("OUTLINE", 200, "Single Color Red", "POINT"),     # non-RGB override
    ("MATRIX", 1000, "Single Color White", "POINT"),   # override beats role
])
def test_capability_matrix(role, nodes, st, expect):
    assert capability(role, nodes, st) == expect


# -- fixture end-to-end classification ----------------------------------------------------------
def test_layout_basic_classification():
    props = parse_props(FIX / "layout_basic.xml")
    classify(props)
    by = _by_name(props)
    assert by["Mega Tree"].role == "MEGA_TREE"
    assert by["Arch L1"].role == "ARCH"
    assert by["Cane 1"].role == "CANE"
    assert by["Roof Left"].role == "OUTLINE"      # name heuristic
    assert by["Front Window"].role == "WINDOW"    # DisplayAs map
    assert by["Snowflake 1"].role == "SNOWFLAKE"  # name heuristic


def test_layout_tricky_edge_cases():
    props = parse_props(FIX / "layout_tricky.xml")
    res = classify(props)
    by = _by_name(props)
    assert by["Yard Tree"].role == "MEGA_TREE"                    # sole 400-node tree → mega
    assert by["House Mesh"].res == "2D_SURFACE"                   # dense Custom → matrix
    assert by["Roof Mono"].res == "POINT"                        # non-RGB override
    assert by["Prop X7"].role == "OUTLINE"                       # group hint "All Outline"
    assert "Garage Preview" not in by                            # non-Default preview excluded
    # Parked Prop (plain Single Line, no name/group clue) + House Mesh (bare Custom) are the tail
    assert {p.name for p in res.unresolved} == {"Parked Prop", "House Mesh"}
    assert all(p.role == "CUSTOM_PROP" and p.confidence == 0.5 for p in res.unresolved)


# -- derive_spatial -----------------------------------------------------------------------------
def test_spatial_bands_sides_and_sweep_order():
    props = parse_props(FIX / "layout_basic.xml")
    classify(props)
    derive_spatial(props)
    by = _by_name(props)
    # arches span left→right and get sweep_order 1..6
    arches = sorted((p for p in props if p.role == "ARCH"), key=lambda q: q.sweep_order or 0)
    assert [a.name for a in arches] == ["Arch L3", "Arch L2", "Arch L1", "Arch R1", "Arch R2", "Arch R3"]
    assert [a.sweep_order for a in arches] == [1, 2, 3, 4, 5, 6]
    # bands: the roof outline sits at the top → ROOF; canes at ground
    assert by["Roof Left"].band == "ROOF"
    assert by["Cane 1"].band == "GROUND"
    # sides: leftmost arch is LEFT, rightmost RIGHT
    assert arches[0].side == "LEFT" and arches[-1].side == "RIGHT"


def test_spatial_mirror_pairs_both_ways():
    props = parse_props(FIX / "layout_basic.xml")
    classify(props)
    derive_spatial(props)
    by = _by_name(props)
    # Arch L1 (-6) mirrors Arch R1 (6) about the centerline; recorded both ways
    assert by["Arch L1"].mirror_of == "Arch R1"
    assert by["Arch R1"].mirror_of == "Arch L1"


def test_spatial_outlier_excluded_before_normalization():
    props = parse_props(FIX / "layout_tricky.xml")
    classify(props)
    summary = derive_spatial(props)
    names_excluded = {p.name for p in summary.excluded}
    assert "Parked Prop" in names_excluded             # X=-900 parked → excluded
    # the parked model did not stretch normalization: the kept props still span 0..1
    kept = [p for p in props if p.name not in names_excluded and p.nodes > 0]
    assert min(p.x for p in kept) == pytest.approx(0.0)
    assert max(p.x for p in kept) == pytest.approx(1.0)


def test_spatial_invert_x_flips_sweep_and_mirror():
    props = parse_props(FIX / "layout_basic.xml")
    classify(props)
    derive_spatial(props, invert_x=True)
    by = _by_name(props)
    # with x flipped, the physically-leftmost arch (L3) becomes sweep_order N, not 1
    arches = {p.name: p.sweep_order for p in props if p.role == "ARCH"}
    assert arches["Arch L3"] == 6 and arches["Arch R3"] == 1
    # mirror pairs still hold (symmetric under the flip)
    assert by["Arch L1"].mirror_of == "Arch R1"


def test_spatial_focal_flag_on_mega_tree():
    props = parse_props(FIX / "layout_basic.xml")
    classify(props)
    derive_spatial(props)
    assert _by_name(props)["Mega Tree"].focal is True


def test_side_cut_boundaries():
    # x exactly at 0.449 → LEFT, 0.451 → CENTER (cut at 0.45); 0.55 → CENTER, >0.55 → RIGHT
    from xlights_core.knowledge.layout_classify import derive_spatial as ds
    # build a synthetic spread so normalization puts specific props at the boundary
    props = [Prop(name="lo", display_as="Arches", role="ARCH", nodes=10, wx=0.0, wy=0.0),
             Prop(name="edge", display_as="Arches", role="ARCH", nodes=10, wx=44.9, wy=0.0),
             Prop(name="hi", display_as="Arches", role="ARCH", nodes=10, wx=100.0, wy=0.0)]
    ds(props)
    assert props[1].x == pytest.approx(0.449, abs=1e-6)
    assert props[1].side == "LEFT"
