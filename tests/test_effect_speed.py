"""Tests for energy-driven effect speed."""
from xlights_orchestrator.pipeline.beats import effect_speed_setting, SPEED_MIN, SPEED_MAX


def test_speed_scales_with_energy():
    quiet = int(effect_speed_setting("Spirals", 0.1)["E_SLIDER_Spirals_Speed"])
    loud = int(effect_speed_setting("Spirals", 0.9)["E_SLIDER_Spirals_Speed"])
    assert quiet < loud
    assert SPEED_MIN <= quiet and loud <= SPEED_MAX


def test_key_follows_effect_type():
    assert set(effect_speed_setting("Pinwheel", 0.5)) == {"E_SLIDER_Pinwheel_Speed"}
