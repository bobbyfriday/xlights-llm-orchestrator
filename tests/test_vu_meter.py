"""The deterministic VU Meter layer: a music-reactive feature on energetic sections."""

from __future__ import annotations

from xlights_orchestrator.pipeline.beats import VU_MIN_INTENSITY, place_vu_meter
from xlights_orchestrator.show_plan import SectionPlan

WIDE = ["SEM_BAND_GROUND", "SEM_ALL", "SEM_ARCHES", "SEM_FOCAL"]


def _sec(intensity=0.8, **kw):
    kw.setdefault("target_groups", ["SEM_ARCHES"])
    kw.setdefault("effect_family", "On")
    kw.setdefault("palette", ["Red", "Green", "Blue"])
    return SectionPlan(start_ms=12000, end_ms=24000, intensity=intensity, **kw)


def test_places_vu_meter_on_wide_group_for_energetic_section():
    vu = place_vu_meter(_sec(intensity=0.9), WIDE, 0.9)
    assert vu is not None
    assert vu.effect_type == "VU Meter"
    assert vu.target == "SEM_BAND_GROUND"            # preferred wide group
    assert vu.look_id.startswith("VU Meter")
    assert (vu.start_ms, vu.end_ms) == (12000, 24000)   # spans the section
    assert vu.render_style == "Per Preview"          # bars span the group


def test_skips_quiet_sections():
    assert place_vu_meter(_sec(intensity=0.3), WIDE, 0.3) is None
    assert place_vu_meter(_sec(), WIDE, VU_MIN_INTENSITY - 0.01) is None


def test_skips_when_no_wide_group():
    assert place_vu_meter(_sec(intensity=0.9), ["SEM_ARCHES", "SEM_FOCAL"], 0.9) is None


def test_look_rotates_by_seed():
    a = place_vu_meter(_sec(intensity=0.9), WIDE, 0.9, seed=0)
    b = place_vu_meter(_sec(intensity=0.9), WIDE, 0.9, seed=1)
    assert a.look_id != b.look_id                    # different sections get different looks


def test_synthesized_meter_is_bound_to_our_beats_track():
    from xlights_orchestrator.pipeline.beats import VU_DEFAULT_TIMING_TRACK, VU_TIMING_TRACK_KEY
    vu = place_vu_meter(_sec(intensity=0.9), WIDE, 0.9)
    assert vu is not None
    # Community looks bind `Timing Event …` meters to their author's track name; ours has Beats.
    assert vu.extra_settings[VU_TIMING_TRACK_KEY] == VU_DEFAULT_TIMING_TRACK == "Beats"


def test_fill_phrase_gesture_always_carries_its_position_curve():
    from xlights_core.knowledge.preset_library import get_library
    from xlights_orchestrator.pipeline.beats import PHRASE_ROTATION, place_phrase_gesture
    lib = get_library()
    rhythm = {"tempo": 120.0, "beats_per_bar": 4}
    sec = SectionPlan(start_ms=0, end_ms=40000, intensity=0.8, target_groups=["SEM_ARCHES"],
                      effect_family="On", palette=["Red", "Green"])
    fills = []
    for seed in range(40):
        g = place_phrase_gesture(sec, rhythm, 0.8, WIDE, seed=seed)
        if g is not None and g.effect_type == "Fill":
            fills.append(g.look_id)
    assert fills, f"no Fill gesture in 40 seeds (rotation {PHRASE_ROTATION})"
    for lid in set(fills):
        assert "Active=TRUE" in lib.get_look("Fill", lid).frozen_base.get("E_VALUECURVE_Fill_Position", ""), lid
