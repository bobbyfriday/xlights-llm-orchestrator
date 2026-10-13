"""Scene casting on the brief-only path (`pipeline/scenes.py` + its `generate.py` wiring): the
cookbook's stack tables parse into archetype rows (layers, blends, brightness), an explicit
`scene_cast` or the role default casts them onto real groups, the realized section carries the
layered stack with the cookbook blend on the right layer, and an unknown / prose-only scene falls
back to the generic base rows. Hermetic — reads the repo's own cookbook."""

from __future__ import annotations

from xlights_orchestrator.brief_schema import build_brief_schema
from xlights_orchestrator.pipeline.generate import realize_section_from_brief
from xlights_orchestrator.pipeline.scenes import (
    StackRow,
    cast_scene,
    default_cast,
    parse_scene_stack,
    scene_archetypes,
)
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.pipeline.validate_brief import validate_brief
from xlights_orchestrator.show_plan import SectionPlan, ShowPlan

from test_golden_pipeline import GROUPS, _analysis


def _section(**kw) -> SectionPlan:
    base = dict(start_ms=12000, end_ms=24000, label="chorus",
                target_groups=["SEM_ALL", "SEM_FOCAL", "SEM_ARCHES", "SEM_CANES"],
                effect_family="Bars", intensity=0.9, palette=["Blue", "Red", "White"],
                effect_types=["Spirals", "Fireworks"], pulse_groups=["SEM_ARCHES", "SEM_CANES"])
    base.update(kw)
    return SectionPlan(**base)


def _state(*sections: SectionPlan) -> State:
    st = State(song_path="song.mp3")
    st.song_analysis = _analysis()
    st.available_groups = list(GROUPS)
    st.show_plan = ShowPlan(concept="scenes", sections=list(sections))
    return st


# -- parsing ------------------------------------------------------------------------------------

def test_parse_sc01_standard_stack():
    rows = parse_scene_stack("SC-01")
    assert [r.archetype for r in rows] == ["G0-ALL-LESS-HERO", "G2-HERO", "G2-HERO", "G2-HERO",
                                           "G2-RHYTHM"]                 # blank Row carries down
    bed, hero_wash, hero_feature, hero_sparkle, rhythm = rows
    assert (bed.layer, bed.effect_type, bed.blend, bed.brightness) == (0, "Color Wash", "", 0.35)
    assert bed.render_style == "Default"                                 # "Default (canvas)"
    assert (hero_wash.layer, hero_wash.effect_type, hero_wash.brightness) == (2, "Color Wash", 0.25)
    assert hero_feature.layer == 1 and hero_feature.feature             # "*Feature effect* (…)"
    assert (hero_sparkle.layer, hero_sparkle.effect_type, hero_sparkle.blend) == (0, "Twinkle", "Max")
    assert hero_sparkle.brightness is None
    assert (rhythm.layer, rhythm.effect_type, rhythm.render_style) == \
        (0, "SingleStrand", "Per Model Default")                       # 'Single Strand' canonical


def test_parse_sc04_timeline_table():
    rows = parse_scene_stack("SC-04")
    assert len(rows) == 6 and all(r.layer == 0 for r in rows)           # no Layer column → single
    assert [r.effect_type for r in rows] == ["Off", "On", "Shockwave", "Spirals", "SingleStrand",
                                             "Strobe"]
    assert rows[1].brightness == 1.0 and rows[0].brightness is None     # "On, white, 100%"
    assert all(r.blend == "" for r in rows)                             # no Blend column
    assert rows[0].phase.startswith("Build") and rows[2].phase.startswith("Release")
    assert rows[4].archetype == "G2-RHYTHM" and rows[4].render_style == "Per Model Default"
    assert scene_archetypes("SC-04") == ["G0-ALL", "G2-HERO", "G2-RHYTHM", "G9-STROBE-OVERLAY"]


def test_parse_blend_vocabulary_and_prose_scenes():
    sc02 = parse_scene_stack("SC-02")
    assert [r.blend for r in sc02] == ["", "Average", ""]               # "Average (try Max)"
    sc05 = parse_scene_stack("SC-05")
    assert sc05[1].blend == "1 is Mask"                                 # "**1 is Mask**"
    assert parse_scene_stack("SC-09") == []                             # prose-only stack
    assert parse_scene_stack("SC-99") == [] and parse_scene_stack("") == []


# -- casting ------------------------------------------------------------------------------------

def test_cast_with_explicit_scene_cast():
    sec = _section(scene_id="SC-01",
                   scene_cast={"G0-ALL-LESS-HERO": "SEM_BAND_GROUND", "G2-HERO": "SEM_FOCAL",
                               "G2-RHYTHM": "SEM_CANES"})
    rows = cast_scene(sec, parse_scene_stack("SC-01"), GROUPS)
    assert [(r.target, r.effect_type, r.layer) for r in rows] == [
        ("SEM_BAND_GROUND", "Color Wash", 0),
        ("SEM_FOCAL", "Color Wash", 2), ("SEM_FOCAL", "Bars", 1), ("SEM_FOCAL", "Twinkle", 0),
        ("SEM_CANES", "SingleStrand", 0)]
    assert all(r.source == "scene" and r.look_id for r in rows)
    assert all(r.start_ms == 12000 and r.end_ms == 24000 for r in rows)
    assert rows[0].extra_settings["C_SLIDER_Brightness"] == "35"       # 30–40% → midpoint
    assert rows[1].extra_settings["C_SLIDER_Brightness"] == "25"
    assert rows[3].extra_settings["T_CHOICE_LayerMethod"] == "Max"
    assert "T_CHOICE_LayerMethod" not in rows[0].extra_settings        # Normal → unset
    assert rows[2].effect_type == "Bars"                                # feature → effect_family
    assert rows[4].render_style == "Per Model Default"
    assert all(r.palette_colors for r in rows)                          # section palette applied


def test_cast_skips_uncastable_and_unavailable_rows():
    sec = _section(scene_id="SC-01", scene_cast={"G2-HERO": "SEM_FOCAL", "G2-RHYTHM": "NOPE"})
    rows = cast_scene(sec, parse_scene_stack("SC-01"), GROUPS)
    assert {r.target for r in rows} == {"SEM_FOCAL"}                    # bed uncast, rhythm missing
    # a row naming no catalog type is skipped; a feature row without a family is skipped too
    stack = [StackRow(archetype="G2-HERO", effect_type=""),
             StackRow(archetype="G2-HERO", feature=True)]
    assert cast_scene(_section(effect_family="NotAnEffect"), stack, GROUPS,
                      cast={"G2-HERO": "SEM_FOCAL"}) == []


def test_default_cast_by_role():
    sec = _section()
    cast = default_cast(scene_archetypes("SC-01"), sec, GROUPS)
    assert cast == {"G0-ALL-LESS-HERO": "SEM_BAND_GROUND",     # no subtractive group → the bed group
                    "G2-HERO": "SEM_FOCAL",
                    "G2-RHYTHM": "SEM_ARCHES"}                 # the section's rhythm pool, first
    with_sub = GROUPS + ["SEM_ALL_LESS_FOCAL", "SEM_ALL_LESS_FOCAL_RHYTHM", "SEM_OUTLINE", "Matrixes"]
    full = default_cast(["G0-ALL", "G0-ALL-LESS-HERO", "G0-ALL-LESS-HERO-RHYTHM", "G1-LEFT",
                         "G1-RIGHT", "G2-HERO", "G2-RHYTHM", "G2-FRAME", "G2-ACCENT", "G2-CANVAS",
                         "G9-STROBE-OVERLAY"], sec, with_sub)
    assert full == {"G0-ALL": "SEM_ALL", "G0-ALL-LESS-HERO": "SEM_ALL_LESS_FOCAL",
                    "G0-ALL-LESS-HERO-RHYTHM": "SEM_ALL_LESS_FOCAL_RHYTHM",
                    "G1-LEFT": "SEM_SIDE_LEFT", "G1-RIGHT": "SEM_SIDE_RIGHT",
                    "G2-HERO": "SEM_FOCAL", "G2-RHYTHM": "SEM_ARCHES", "G2-FRAME": "SEM_OUTLINE",
                    "G2-ACCENT": "SEM_SNOWFLAKES", "G2-CANVAS": "Matrixes"}
    assert "G9-STROBE-OVERLAY" not in full                              # code's flashes play it
    assert default_cast(["G2-CANVAS"], sec, GROUPS) == {}               # no matrix → uncast
    # the default casting is what cast_scene uses when scene_cast is empty
    rows = cast_scene(_section(scene_id="SC-01"), parse_scene_stack("SC-01"), GROUPS)
    assert [r.target for r in rows] == ["SEM_BAND_GROUND", "SEM_FOCAL", "SEM_FOCAL", "SEM_FOCAL",
                                        "SEM_ARCHES"]


def test_timeline_scene_casts_only_its_final_phase_and_never_off():
    rows = cast_scene(_section(scene_id="SC-04"), parse_scene_stack("SC-04"), GROUPS)
    assert [(r.target, r.effect_type) for r in rows] == [
        ("SEM_ALL", "Shockwave"), ("SEM_FOCAL", "Spirals"), ("SEM_ARCHES", "SingleStrand")]


# -- realization ------------------------------------------------------------------------------

def test_realized_section_carries_the_layered_stack_with_the_blend_on_the_right_layer():
    # a non-peak full section (the peak is the hotter section after it, whose peak fill would
    # otherwise add its own broad SEM_ALL bed over the scene's)
    sec = _section(scene_id="SC-01", treatment="full", intensity=0.75)
    peak = _section(start_ms=24000, end_ms=36000, label="peak", intensity=0.95)
    rows = realize_section_from_brief(_state(sec, peak), 0)
    scene = [r for r in rows if r.source == "scene"]
    assert scene and all(r.section_index == 0 for r in scene)
    # the five cookbook rows, by (target, layer, effect); the downstream duration-class pass chops
    # the long cellable rows (Bars, SingleStrand) into contiguous 2-bar cells that tile the section
    stack = sorted({(r.target, r.layer, r.effect_type) for r in scene})
    assert stack == [("SEM_ARCHES", 0, "SingleStrand"), ("SEM_BAND_GROUND", 0, "Color Wash"),
                     ("SEM_FOCAL", 0, "Twinkle"), ("SEM_FOCAL", 1, "Bars"),
                     ("SEM_FOCAL", 2, "Color Wash")]
    bars = sorted((r for r in scene if r.effect_type == "Bars"), key=lambda r: r.start_ms)
    assert bars[0].start_ms == 12000 and bars[-1].end_ms == 24000
    assert all(a.end_ms == b.start_ms for a, b in zip(bars, bars[1:]))
    focal = {(r.layer, r.effect_type): r for r in scene if r.target == "SEM_FOCAL"}
    assert focal[(0, "Twinkle")].extra_settings["T_CHOICE_LayerMethod"] == "Max"   # L1 → layer 0
    assert "T_CHOICE_LayerMethod" not in focal[(1, "Bars")].extra_settings
    assert "T_CHOICE_LayerMethod" not in focal[(2, "Color Wash")].extra_settings
    # the cookbook level survives the phrase-dynamics pass (flat energy → a constant level)
    assert focal[(2, "Color Wash")].extra_settings["C_SLIDER_Brightness"] == "25"
    bed = next(r for r in scene if r.target == "SEM_BAND_GROUND")
    assert bed.extra_settings["C_SLIDER_Brightness"] == "35"
    # no generic base row was synthesized (the stack REPLACED it) and the code bed stood down,
    # yet the downstream layers still ran over the stack
    assert not any(r.source == "generator" for r in rows)
    assert not any(r.source == "bed" for r in rows)
    assert any(r.source == "weave" for r in rows) and any(r.source == "accents" for r in rows)
    # every scene row passed the coverage gate untouched (the scene is the coverage decision)
    assert {r.target for r in scene} == {"SEM_BAND_GROUND", "SEM_FOCAL", "SEM_ARCHES"}


def test_unknown_or_prose_scene_falls_back_to_generic_base_rows():
    for scene_id in ("SC-99", "SC-09"):
        rows = realize_section_from_brief(_state(_section(scene_id=scene_id)), 0)
        assert not any(r.source == "scene" for r in rows)
        base = [r for r in rows if r.source == "generator"]
        assert base and {r.effect_type for r in base} <= {"Bars", "Spirals", "Fireworks"}
    plain = realize_section_from_brief(_state(_section()), 0)
    fallback = realize_section_from_brief(_state(_section(scene_id="SC-99")), 0)
    assert [r.model_dump() for r in plain] == [r.model_dump() for r in fallback]


def test_scene_rows_rhyme_their_palette_across_recurring_labels():
    a, b = _section(label="chorus 1", scene_id="SC-01"), \
        _section(start_ms=24000, end_ms=36000, label="chorus 2", scene_id="SC-01")
    st = _state(a, b)
    first = [r for r in realize_section_from_brief(st, 0) if r.source == "scene"]
    second = [r for r in realize_section_from_brief(st, 1) if r.source == "scene"]
    assert [r.palette_colors for r in first] == [r.palette_colors for r in second]


# -- the contract: schema + validator ------------------------------------------------------------

def test_scene_cast_round_trips_and_schema_enumerates_groups():
    sec = SectionPlan.model_validate({
        "start_ms": 0, "end_ms": 1, "target_groups": ["SEM_FOCAL"], "effect_family": "On",
        "intensity": 0.5, "scene_id": "SC-01", "scene_cast": {"G2-HERO": "SEM_FOCAL"}})
    assert sec.scene_cast == {"G2-HERO": "SEM_FOCAL"}
    assert SectionPlan(start_ms=0, end_ms=1, target_groups=[], effect_family="On",
                       intensity=0.5).scene_cast == {}
    p = build_brief_schema(groups=["SEM_ALL", "SEM_FOCAL"], effect_types=["On"], scene_ids=["SC-01"],
                           stems=[], colors=[])["$defs"]["SectionPlan"]["properties"]["scene_cast"]
    assert p["additionalProperties"]["enum"] == ["SEM_ALL", "SEM_FOCAL"]


def test_validator_checks_scene_cast_values_and_keys():
    vocab = {"groups": ["SEM_ALL", "SEM_FOCAL", "SEM_ARCHES"], "effect_types": ["On"],
             "cellable": [], "scene_ids": ["SC-01", "SC-09"], "stems": [], "colors": []}
    def brief(**sec):
        s = {"start_ms": 0, "end_ms": 30_000, "target_groups": ["SEM_ALL"], "effect_family": "On",
             "intensity": 0.5}
        s.update(sec)
        return {"sections": [s]}
    r = validate_brief(brief(scene_id="SC-01", scene_cast={"G2-HERO": "SEM_FOCAL"}), vocab,
                       duration_ms=30_000)
    assert r.ok and r.warnings == []
    r = validate_brief(brief(scene_id="SC-01", scene_cast={"G2-HERO": "Megatree"}), vocab,
                       duration_ms=30_000)
    e = next(i for i in r.errors if i.path == "sections[0].scene_cast.G2-HERO")
    assert not r.ok and e.allowed == ["SEM_ALL", "SEM_FOCAL", "SEM_ARCHES"]
    r = validate_brief(brief(scene_id="SC-01", scene_cast={"G2-CANVAS": "SEM_ALL"}), vocab,
                       duration_ms=30_000)
    w = next(i for i in r.warnings if i.path == "sections[0].scene_cast.G2-CANVAS")
    assert r.ok and w.allowed == ["G0-ALL-LESS-HERO", "G2-HERO", "G2-RHYTHM"]
    r = validate_brief(brief(scene_cast={"G2-HERO": "SEM_FOCAL"}), vocab, duration_ms=30_000)
    assert r.ok and [i.path for i in r.warnings] == ["sections[0].scene_cast"]
    r = validate_brief(brief(scene_id="SC-01", scene_cast="G2-HERO→SEM_FOCAL"), vocab,
                       duration_ms=30_000)
    assert not r.ok and any(i.path == "sections[0].scene_cast" for i in r.errors)
