"""Tests for direction variety (pipeline/motion): directional effects turn on the beat grid."""

from __future__ import annotations

from xlights_orchestrator.pipeline.motion import (
    effect_axes,
    resolve_direction_change,
    vary_directions,
)
from xlights_orchestrator.pipeline.validate_brief import validate_brief
from xlights_orchestrator.show_plan import EffectInstruction, SectionFabric, SectionPlan

BAR_MS = 2000.0                                   # 120 BPM, 4/4: a beat every 500 ms


def _sec(fabric=None, start=0, end=32000, intensity=0.7):
    return SectionPlan(start_ms=start, end_ms=end, target_groups=["SEM_FOCAL"],
                       effect_family="Bars", intensity=intensity, fabric=fabric)


def _rhythm(start=0, end=32000):
    return {"beats_ms": list(range(start, end, 500)), "beats_per_bar": 4}


def _row(target="SEM_FOCAL", et="Bars", start=0, end=32000, **kw):
    return EffectInstruction(target=target, effect_type=et, look_id=f"{et}#0",
                             start_ms=start, end_ms=end, **kw)


def _vary(instrs, sec, *, treatment="pulse", is_peak=False, seed=0):
    return vary_directions(instrs, sec, _rhythm(sec.start_ms, sec.end_ms), bar_ms=BAR_MS,
                           intensity=sec.intensity, treatment=treatment, is_peak=is_peak,
                           seed=seed)


def _dirs(out, key="E_CHOICE_Bars_Direction"):
    return [(o.start_ms, o.extra_settings[key]) for o in out]


def test_axes_follow_the_knobs_and_skip_vertical_on_line_props():
    assert effect_axes("Bars") == [("ltr", "rtl"), ("up", "down"), ("center_out", "center_in")]
    assert effect_axes("Bars", "SEM_ARCHES") == [("ltr", "rtl"), ("center_out", "center_in")]
    assert effect_axes("SingleStrand") == [("ltr", "rtl"), ("center_out", "center_in"), ("bounce",)]
    assert effect_axes("Pinwheel") == [("ltr", "rtl")]
    assert effect_axes("Plasma") == []


def test_cadence_by_energy_and_brief():
    assert resolve_direction_change(_sec(), 0.7, "pulse", False) == "bar"
    assert resolve_direction_change(_sec(), 0.2, "pulse", False) == "phrase"
    assert resolve_direction_change(_sec(), 0.7, "gesture", False) == "phrase"
    assert resolve_direction_change(_sec(), 0.2, "rest", True) == "bar"     # the peak
    held = _sec(SectionFabric(direction_change="hold"))
    assert resolve_direction_change(held, 0.9, "full", True) == "hold"


def test_bar_cadence_cuts_each_bar_and_changes_axis_each_phrase():
    out = _vary([_row()], _sec())                 # 16 bars of Bars on the hero
    assert [o.start_ms for o in out] == list(range(0, 32000, 2000))
    assert out[0].end_ms == 2000 and out[-1].end_ms == 32000
    d = [v for _, v in _dirs(out)]
    # the hero runs one axis ahead (up/down first), flips per bar, next axis per 4-bar phrase
    assert d[:4] == ["up", "down", "up", "down"]
    assert d[4:8] == ["H-expand", "H-compress", "H-expand", "H-compress"]
    assert d[8:12] == ["Right", "Left", "Right", "Left"]


def test_hold_keeps_one_direction_and_does_not_cut():
    out = _vary([_row(target="SEM_ALL_LESS_FOCAL")], _sec(SectionFabric(direction_change="hold")))
    assert len(out) == 1 and out[0].extra_settings["E_CHOICE_Bars_Direction"] == "Right"


def test_mirror_sends_the_right_side_the_other_way():
    sec = _sec(SectionFabric(direction_change="phrase"))
    left = _vary([_row(target="SEM_SIDE_LEFT")], sec)
    right = _vary([_row(target="SEM_SIDE_RIGHT")], sec)
    assert _dirs(left)[0][1] == "Right" and _dirs(right)[0][1] == "Left"
    unmirrored = _sec(SectionFabric(direction_change="phrase", mirror=False))
    assert _dirs(_vary([_row(target="SEM_SIDE_RIGHT")], unmirrored))[0][1] == "Right"


def test_sweeps_never_flip_faster_than_two_beats():
    out = _vary([_row(target="SEM_ARCHES", end=8000)], _sec(SectionFabric(direction_change="beat")))
    assert [o.start_ms for o in out] == [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000]


def test_spirals_reverse_spin_on_every_downbeat_at_their_own_speed():
    key = "E_TEXTCTRL_Spirals_Movement"
    row = _row(et="Spirals", end=8000, extra_settings={key: "2.5"})
    out = _vary([row], _sec())
    assert [o.start_ms for o in out] == [0, 2000, 4000, 6000]
    assert [o.extra_settings[key] for o in out] == ["2.5", "-2.5", "2.5", "-2.5"]
    assert all(o.directed for o in out)


def test_spiral_shape_changes_each_phrase_and_stays_thin_enough():
    out = _vary([_row(et="Spirals", end=32000)], _sec())
    shapes = [(o.extra_settings["E_SLIDER_Spirals_Count"],
               o.extra_settings["E_SLIDER_Spirals_Thickness"],
               o.extra_settings["E_SLIDER_Spirals_Rotation"]) for o in out]
    assert shapes[0] == shapes[3] and shapes[0] != shapes[4]          # one shape per phrase
    assert len(set(shapes)) == 2
    assert all(int(c) <= 2 for c, _, _ in shapes)                     # never a wall of stripes
    assert all(int(t) <= 40 and int(r) >= 200 for _, t, r in shapes)  # never fat flat bars
    pinned = _row(et="Spirals", end=8000, extra_settings={"E_SLIDER_Spirals_Thickness": "70"})
    assert _vary([pinned], _sec())[0].extra_settings["E_SLIDER_Spirals_Thickness"] == "70"


def test_stacked_spirals_turn_together_but_stay_opposed():
    key = "E_TEXTCTRL_Spirals_Movement"
    a = _row(et="Spirals", end=8000, extra_settings={key: "2.0"})
    b = _row(et="Spirals", end=8000, layer=1, extra_settings={key: "2.0"})
    out = _vary([a, b], _sec())
    low = [o for o in out if o.layer == 0]
    high = [o for o in out if o.layer == 1]
    assert len(low) == len(high) == 4
    for x, y in zip(low, high):
        assert float(x.extra_settings[key]) == -float(y.extra_settings[key])
        assert x.extra_settings["E_SLIDER_Spirals_Thickness"] != \
            y.extra_settings["E_SLIDER_Spirals_Thickness"]              # thick vs thin pair
        assert int(x.extra_settings["E_SLIDER_Spirals_Rotation"]) > 0 > \
            int(y.extra_settings["E_SLIDER_Spirals_Rotation"])          # crossed twist


def test_phrase_class_effects_pick_a_direction_without_being_cut():
    out = _vary([_row(et="Fill", end=16000)], _sec())
    assert len(out) == 1 and "E_CHOICE_Fill_Direction" in out[0].extra_settings


def test_explicit_directions_are_left_alone():
    pinned = _row(extra_settings={"E_CHOICE_Bars_Direction": "Left"})
    spun = _row(et="Spirals", directed=True, extra_settings={"E_TEXTCTRL_Spirals_Movement": "-3.0"})
    out = _vary([pinned, spun], _sec())
    assert len(out) == 2
    assert out[0].extra_settings == {"E_CHOICE_Bars_Direction": "Left"}
    assert out[1].extra_settings == {"E_TEXTCTRL_Spirals_Movement": "-3.0"}


def test_entrance_stays_on_the_first_piece_and_exit_on_the_last():
    row = _row(end=8000, extra_settings={"T_TEXTCTRL_Fadein": "0.5", "T_TEXTCTRL_Fadeout": "1"})
    out = _vary([row], _sec())
    assert "T_TEXTCTRL_Fadein" in out[0].extra_settings
    assert "T_TEXTCTRL_Fadeout" not in out[0].extra_settings
    assert "T_TEXTCTRL_Fadeout" in out[-1].extra_settings
    assert all("T_TEXTCTRL_Fadein" not in o.extra_settings for o in out[1:])


def test_woven_cells_are_turned_but_never_cut():
    cell = _row(target="SEM_ARCHES", end=4000, source="weave")
    out = _vary([cell], _sec())
    assert len(out) == 1 and "E_CHOICE_Bars_Direction" in out[0].extra_settings


def test_turns_count_from_the_section_start():
    sec = _sec(start=1000, end=17000)
    out = vary_directions([_row(start=1000, end=17000)], sec, _rhythm(1000, 17000),
                          bar_ms=BAR_MS, intensity=0.7, treatment="pulse", is_peak=False, seed=0)
    assert [o.start_ms for o in out] == [1000, 3000, 5000, 7000, 9000, 11000, 13000, 15000]


def test_validator_checks_the_new_fabric_fields():
    def brief(fab):
        return {"sections": [{"start_ms": 0, "end_ms": 10000, "target_groups": ["SEM_ALL"],
                              "effect_family": "Bars", "intensity": 0.5, "fabric": fab}]}
    vocab = {"groups": ["SEM_ALL"], "effect_types": ["Bars"], "cellable": ["Bars"]}
    ok = validate_brief(brief({"direction_change": "bar", "mirror": False}), vocab=vocab,
                        duration_ms=10000)
    assert ok.ok
    bad = validate_brief(brief({"direction_change": "sometimes", "mirror": "yes"}), vocab=vocab,
                         duration_ms=10000)
    paths = {e.path for e in bad.errors}
    assert {"sections[0].fabric.direction_change", "sections[0].fabric.mirror"} <= paths
