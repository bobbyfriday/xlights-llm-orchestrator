"""Integrity guard for the consolidated per-effect metadata table (I3).

`EFFECT_META` is the single source of truth; the historical names (`SPEED_KEYS`,
`DIRECTION_KNOBS`, `ENERGY_BAND`, `DURATION_*`, `MOTION_EFFECTS`) are derived views over it.
This pins the derivation and a few transcribed anchor values so a later edit to a row that
diverges a derived view fails here (locally) rather than only as a golden-snapshot diff.
"""
from __future__ import annotations

from xlights_orchestrator.pipeline.effect_meta import (
    DIRECTION_KNOBS,
    DURATION_CELLABLE,
    DURATION_HIT,
    DURATION_PHRASE,
    EFFECT_META,
    ENERGY_BAND,
    MOTION_EFFECTS,
    SPEED_KEYS,
    duration_class,
)


def test_derived_views_are_consistent_with_the_table():
    # every derived-view key is a real row, and its value equals that row's field
    for et, spec in SPEED_KEYS.items():
        assert EFFECT_META[et].speed == spec
    for et, band in ENERGY_BAND.items():
        assert EFFECT_META[et].energy_band == band
    assert DURATION_HIT == {et for et, m in EFFECT_META.items() if m.duration_class == "hit"}
    assert DURATION_PHRASE == {et for et, m in EFFECT_META.items() if m.duration_class == "phrase"}
    assert DURATION_CELLABLE == {et for et, m in EFFECT_META.items() if m.duration_class == "cellable"}


def test_duration_classes_are_disjoint():
    assert DURATION_HIT.isdisjoint(DURATION_PHRASE)
    assert DURATION_HIT.isdisjoint(DURATION_CELLABLE)
    assert DURATION_PHRASE.isdisjoint(DURATION_CELLABLE)


def test_motion_effects_derivation():
    # community fabric = cell-able types plus the two banded-motion textures
    assert MOTION_EFFECTS == DURATION_CELLABLE | {"Fire", "Galaxy"}


def test_duration_class_helper_defaults_to_free():
    assert duration_class("definitely-not-a-real-effect") == "free"
    for et in DURATION_HIT:
        assert duration_class(et) == "hit"


def test_energy_band_anchor_values():
    # anchors transcribed from the pre-consolidation qa/rules.py table
    assert ENERGY_BAND["Twinkle"] == (1, 3)
    assert ENERGY_BAND["Shape"] == (1, 4)
    assert ENERGY_BAND["VU Meter"] == (2, 5)


def test_derived_views_non_empty():
    assert SPEED_KEYS and ENERGY_BAND and DURATION_CELLABLE and MOTION_EFFECTS


def test_spirals_direction_knobs():
    # Corpus-observed: 84 looks carry E_SLIDER_Spirals_Rotation, 16 negative → ltr=+20, rtl=-20
    assert DIRECTION_KNOBS["Spirals"]["ltr"] == ("E_SLIDER_Spirals_Rotation", "20")
    assert DIRECTION_KNOBS["Spirals"]["rtl"] == ("E_SLIDER_Spirals_Rotation", "-20")


def test_ripple_direction_knobs():
    # Corpus-observed: 22 looks carry E_SLIDER_Ripple_Rotation (13 more via value-curve)
    assert DIRECTION_KNOBS["Ripple"]["ltr"] == ("E_SLIDER_Ripple_Rotation", "20")
    assert DIRECTION_KNOBS["Ripple"]["rtl"] == ("E_SLIDER_Ripple_Rotation", "-20")
