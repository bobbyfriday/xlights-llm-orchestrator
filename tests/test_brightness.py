"""Tests for energy-scaled wash brightness."""
from xlights_orchestrator.pipeline.beats import wash_brightness, WASH_MIN_B, WASH_MAX_B
from xlights_core.knowledge.value_curves import brightness_setting


def test_wash_brightness_monotonic():
    assert wash_brightness(0.0) == WASH_MIN_B
    assert wash_brightness(1.0) == WASH_MAX_B
    assert wash_brightness(0.2) < wash_brightness(0.8)


def test_brightness_as_static_slider():
    lvl = wash_brightness(0.9)
    s = brightness_setting(lvl)
    assert s == {"C_SLIDER_Brightness": str(int(round(lvl)))}   # static slider, not a degenerate curve
