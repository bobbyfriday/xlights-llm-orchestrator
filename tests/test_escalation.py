"""Tests for motif escalation across recurring sections."""
from xlights_orchestrator.pipeline.beats import escalation_level, effective_intensity, wash_brightness


def test_escalation_level_first_to_last():
    rm = {"chorus": [3, 7, 11]}
    assert escalation_level(3, rm) == 0.0       # first
    assert escalation_level(11, rm) == 1.0      # last
    assert 0 < escalation_level(7, rm) < 1      # middle
    assert escalation_level(5, rm) == 0.0       # non-recurring
    assert escalation_level(2, {"x": [2]}) == 0.0   # single occurrence


def test_later_recurrence_brighter_and_fuller():
    rm = {"chorus": [0, 4, 8]}
    first = effective_intensity(0.6, 0, rm)
    last = effective_intensity(0.6, 8, rm)
    assert last > first                          # final chorus acts more intense
    assert wash_brightness(last) > wash_brightness(first)


def test_no_brief_no_boost():
    assert effective_intensity(0.5, 3, None) == 0.5
