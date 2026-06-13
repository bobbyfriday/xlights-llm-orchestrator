"""Tests for direction realization via effect-native settings (no grouping changes)."""

from __future__ import annotations

from xlights_orchestrator.pipeline.beats import place_beat_accents
from xlights_orchestrator.pipeline.weave import (
    direction_setting,
    expand_weave,
    fallback_weave,
)
from xlights_orchestrator.show_plan import CellRecipe, SectionPlan, SectionWeave

GROUPS = ["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_YARD",
          "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT"]


def _sec(**kw):
    kw.setdefault("start_ms", 0); kw.setdefault("end_ms", 8000)
    kw.setdefault("target_groups", ["SEM_YARD"]); kw.setdefault("effect_family", "On")
    kw.setdefault("intensity", 0.8); kw.setdefault("palette", ["Gold"])
    return SectionPlan(**kw)


def _rhythm(n=16, step=500):
    return {"beats_ms": [i * step for i in range(n)], "prominent_stem": None,
            "onsets_by_stem": {}, "chords_ms": [], "tempo": 120}


# -- direction_setting ---------------------------------------------------------

def test_direction_knobs_per_effect():
    assert direction_setting("SingleStrand", "ltr", 0) == {"E_CHOICE_Chase_Type1": "Left-Right"}
    assert direction_setting("SingleStrand", "center_out", 0) == {"E_CHOICE_Chase_Type1": "From Middle"}
    assert direction_setting("Bars", "center_in", 0) == {"E_CHOICE_Bars_Direction": "H-compress"}
    assert direction_setting("Meteors", "center_out", 0) == {"E_CHOICE_Meteors_Effect": "Explode"}
    assert direction_setting("Fill", "up", 0) == {"E_CHOICE_Fill_Direction": "Up"}
    assert direction_setting("Pinwheel", "rtl", 0) == {"E_CHECKBOX_Pinwheel_Rotation": "0"}


def test_bounce_native_vs_bar_flip():
    # native bounce: constant regardless of bar
    assert direction_setting("SingleStrand", "bounce", 0) == \
           direction_setting("SingleStrand", "bounce", 1) == \
           {"E_CHOICE_Chase_Type1": "Dual Bounce"}
    # static-direction effect: value flips at bar boundaries
    assert direction_setting("Wave", "bounce", 0) == {"E_CHOICE_Wave_Direction": "Left to Right"}
    assert direction_setting("Wave", "bounce", 1) == {"E_CHOICE_Wave_Direction": "Right to Left"}
    # vertical-natured fallback pair
    assert direction_setting("Meteors", "bounce", 0) == {"E_CHOICE_Meteors_Effect": "Up"}
    assert direction_setting("Meteors", "bounce", 1) == {"E_CHOICE_Meteors_Effect": "Down"}


def test_unknown_pairs_noop():
    assert direction_setting("On", "ltr", 0) == {}
    assert direction_setting("SingleStrand", "up", 0) == {}      # no vertical chase type
    assert direction_setting("SingleStrand", "", 0) == {}
    assert direction_setting("Spirals", "sideways", 0) == {}


# -- weaver integration --------------------------------------------------------

def test_cells_carry_direction_and_flip_per_bar():
    w = SectionWeave(cells=[CellRecipe(effect_type="Wave", role="carrier", cell_beats=1,
                                       direction="bounce", groups=["SEM_YARD"])])
    out = expand_weave(_sec(), w, _rhythm(16), 0.8, GROUPS)
    # sweep cells floor to 2 beats (dwell time), 4/4 → 2 cells = bar 0 (ltr), next 2 = bar 1 (rtl)
    dirs = [c.extra_settings["E_CHOICE_Wave_Direction"] for c in out]
    assert dirs[:2] == ["Left to Right"] * 2
    assert dirs[2:4] == ["Right to Left"] * 2


def test_empty_direction_is_backcompat():
    plain = SectionWeave(cells=[CellRecipe(effect_type="SingleStrand", role="carrier",
                                           cell_beats=1, groups=["SEM_ARCHES"])])
    out = expand_weave(_sec(), plain, _rhythm(8), 0.8, GROUPS)
    assert all("E_CHOICE_Chase_Type1" not in c.extra_settings for c in out)
    assert all(c.target == "SEM_ARCHES" for c in out)            # no target changes, ever


def test_fallback_weave_bounces():
    w = fallback_weave(_sec(), GROUPS)
    assert w.cells[0].direction == "bounce"
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    carriers = [c for c in out if c.effect_type == "SingleStrand"]
    assert carriers and all(c.extra_settings.get("E_CHOICE_Chase_Type1") == "Dual Bounce"
                            for c in carriers)


# -- beat-accent bounce --------------------------------------------------------

def test_accent_chase_reverses_on_odd_bars():
    sec = _sec(palette=["Gold"], intensity=0.9)
    rhythm = {"beats_ms": [i * 500 for i in range(16)], "prominent_stem": None,
              "onsets_by_stem": {}, "chords_ms": [], "tempo": 120}
    acc = place_beat_accents(sec, rhythm, GROUPS)
    pool = ["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"]
    offbeats = [a for a in acc if a.target in pool and a.start_ms % 2000 != 0]
    bar0 = [a.target for a in offbeats if a.start_ms < 2000]
    bar1 = [a.target for a in offbeats if 2000 <= a.start_ms < 4000]
    # bar 0 walks forward (beat 1,2,3 → idx 1,2,0), bar 1 walks backward (idx 1,0,2)
    assert bar0 == [pool[1], pool[2], pool[0]]
    assert bar1 == [pool[1], pool[0], pool[2]]
