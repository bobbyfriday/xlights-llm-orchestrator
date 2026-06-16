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

def test_meter_walk_advances_through_the_ring():
    sec = _sec(palette=["Gold"], intensity=0.9)
    rhythm = {"beats_ms": [i * 500 for i in range(16)], "beats_per_bar": 4, "prominent_stem": None,
              "melodic_stem": None, "onsets_by_stem": {}, "onset_mag_by_stem": {},
              "chords_ms": [], "tempo": 120}
    ring = ["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"]      # a 3-group layout → a 3-beat wrap
    acc = place_beat_accents(sec, rhythm, ring)
    by_t = {a.start_ms: a.target for a in acc if a.target in ring}
    # the bar WALKS FORWARD: downbeat → ring[0]; each off-beat → the next ring family (i % len)
    assert by_t[0] == "SEM_ARCHES"          # downbeat anchor
    assert by_t[500] == ring[1 % 3]         # SEM_CANES
    assert by_t[1000] == ring[2 % 3]        # SEM_MINITREES
    assert by_t[1500] == ring[3 % 3]        # SEM_ARCHES (wrapped, still forward)
    assert by_t[2000] == "SEM_ARCHES"       # next bar's downbeat anchor


# -- counter-phase weaving -----------------------------------------------------

def _dirs_by_layerorder(out, n_recipes=2):
    """Per-recipe direction sequences (cells interleave in output; split by emit order)."""
    seqs = {}
    for c in out:
        k = c.extra_settings.get("E_CHOICE_Chase_Type1")
        seqs.setdefault((c.start_ms, ), []).append(k)
    return seqs


def test_opposite_pair_counterphases_per_bar():
    """ltr + rtl on the same groups = the LLM's crossing-chase habit → upgraded to a woven
    figure: both flip per bar, in opposite phase (cross, bounce, cross back)."""
    w = SectionWeave(cells=[
        CellRecipe(effect_type="SingleStrand", role="carrier", direction="ltr",
                   cell_beats=2, groups=["SEM_ARCHES"]),
        CellRecipe(effect_type="SingleStrand", role="texture", direction="rtl",
                   cell_beats=2, groups=["SEM_ARCHES"]),
    ])
    out = expand_weave(_sec(end_ms=16000), w, _rhythm(32), 0.8, GROUPS)
    by_time = {}
    for c in out:
        by_time.setdefault(c.start_ms, []).append(c.extra_settings["E_CHOICE_Chase_Type1"])
    times = sorted(by_time)
    # every moment has BOTH directions (still crossing)...
    assert all(sorted(by_time[t]) == ["Left-Right", "Right-Left"] for t in times)
    # ...and each layer SWAPS at the bar boundary: the pair order flips between bars
    bar0 = by_time[times[0]]                      # 2-beat cells → 2 cells/bar
    bar1 = by_time[times[2]]                      # first cell of bar 1
    assert bar0 == bar1[::-1]                     # layer 1 and 2 traded directions


def test_explicit_alternate_staggers():
    w = SectionWeave(cells=[
        CellRecipe(effect_type="SingleStrand", role="carrier", direction="alternate",
                   cell_beats=2, groups=["SEM_ARCHES"]),
        CellRecipe(effect_type="SingleStrand", role="texture", direction="alternate",
                   cell_beats=2, groups=["SEM_ARCHES"]),
    ])
    out = expand_weave(_sec(end_ms=16000), w, _rhythm(32), 0.8, GROUPS)
    by_time = {}
    for c in out:
        by_time.setdefault(c.start_ms, []).append(c.extra_settings["E_CHOICE_Chase_Type1"])
    assert all(sorted(v) == ["Left-Right", "Right-Left"] for v in by_time.values())


def test_single_static_recipe_unchanged():
    w = SectionWeave(cells=[CellRecipe(effect_type="SingleStrand", role="carrier",
                                       direction="ltr", cell_beats=2, groups=["SEM_ARCHES"])])
    out = expand_weave(_sec(end_ms=16000), w, _rhythm(32), 0.8, GROUPS)
    assert all(c.extra_settings["E_CHOICE_Chase_Type1"] == "Left-Right" for c in out)


def test_opposite_pair_on_different_groups_untouched():
    w = SectionWeave(cells=[
        CellRecipe(effect_type="SingleStrand", role="carrier", direction="ltr",
                   cell_beats=2, groups=["SEM_ARCHES"]),
        CellRecipe(effect_type="SingleStrand", role="texture", direction="rtl",
                   cell_beats=2, groups=["SEM_CANES"]),
    ])
    out = expand_weave(_sec(end_ms=16000), w, _rhythm(32), 0.8, GROUPS)
    arches = {c.extra_settings["E_CHOICE_Chase_Type1"] for c in out if c.target == "SEM_ARCHES"}
    canes = {c.extra_settings["E_CHOICE_Chase_Type1"] for c in out if c.target == "SEM_CANES"}
    assert arches == {"Left-Right"} and canes == {"Right-Left"}   # no shared groups → static


def test_look_implied_opposite_pair_counterphases():
    """The LLM builds crossing chases by picking two OPPOSED LOOKS with empty direction
    fields (live run 8) — the pair detector must read the look's own chase-type value."""
    # within the CANDIDATE looks (what placement actually resolves): #0 = Left-Right,
    # #2 = Right-Left (corpus facts)
    w = SectionWeave(cells=[
        CellRecipe(effect_type="SingleStrand", role="carrier", look_id="SingleStrand#0",
                   cell_beats=2, groups=["SEM_ARCHES"]),
        CellRecipe(effect_type="SingleStrand", role="texture", look_id="SingleStrand#2",
                   cell_beats=2, groups=["SEM_ARCHES"]),
    ])
    out = expand_weave(_sec(end_ms=16000), w, _rhythm(32), 0.8, GROUPS)
    by_time = {}
    for c in out:
        by_time.setdefault(c.start_ms, []).append(c.extra_settings.get("E_CHOICE_Chase_Type1"))
    times = sorted(by_time)
    assert all(sorted(v) == ["Left-Right", "Right-Left"] for v in by_time.values())
    assert by_time[times[0]] == by_time[times[2]][::-1]   # layers swap at the bar boundary
