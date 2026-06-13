"""Tests for atmosphere readability: a bare opaque bed under a sparse feature is dimmed to a glow."""

from __future__ import annotations

from xlights_orchestrator.pipeline.beats import (
    GLOW_BRIGHTNESS,
    dim_beds_under_atmosphere,
)
from xlights_orchestrator.show_plan import EffectInstruction


def _ins(effect_type, target, *, start=0, end=100000, extra=None):
    return EffectInstruction(target=target, effect_type=effect_type, look_id="",
                             start_ms=start, end_ms=end, extra_settings=extra or {})


def _brightness(ins):
    return ins.extra_settings.get("C_SLIDER_Brightness")


def test_bare_on_under_snowflakes_is_dimmed():
    bed = _ins("On", "SEM_SNOWFLAKES")
    feat = _ins("Snowflakes", "SEM_SNOWFLAKES")
    dim_beds_under_atmosphere([bed, feat])
    assert _brightness(bed) == str(int(GLOW_BRIGHTNESS))


def test_glow_is_dim():
    assert 0 < GLOW_BRIGHTNESS < 50            # a glow, not a wash (100 = normal)


def test_color_wash_and_fill_beds_also_dimmed():
    for bed_type in ("Color Wash", "Fill"):
        bed = _ins(bed_type, "SEM_ALL")
        feat = _ins("Meteors", "SEM_ALL")
        dim_beds_under_atmosphere([bed, feat])
        assert _brightness(bed) == str(int(GLOW_BRIGHTNESS)), bed_type


def test_a_bright_wash_is_capped_to_glow():
    bed = _ins("On", "SEM_SNOWFLAKES", extra={"C_SLIDER_Brightness": "76"})  # the real intro wash level
    feat = _ins("Snowflakes", "SEM_SNOWFLAKES")
    dim_beds_under_atmosphere([bed, feat])
    assert _brightness(bed) == str(int(GLOW_BRIGHTNESS))


def test_an_already_dim_bed_is_left_alone():
    bed = _ins("On", "SEM_SNOWFLAKES", extra={"C_SLIDER_Brightness": "15"})  # already below the glow
    feat = _ins("Snowflakes", "SEM_SNOWFLAKES")
    dim_beds_under_atmosphere([bed, feat])
    assert _brightness(bed) == "15"


def test_value_curve_brightness_is_replaced_with_static_glow():
    bed = _ins("On", "SEM_SNOWFLAKES", extra={"C_VALUECURVE_Brightness": "Active=TRUE|..."})
    feat = _ins("Snowflakes", "SEM_SNOWFLAKES")
    dim_beds_under_atmosphere([bed, feat])
    assert _brightness(bed) == str(int(GLOW_BRIGHTNESS))
    assert "C_VALUECURVE_Brightness" not in bed.extra_settings


def test_blended_accent_is_left_alone():
    accent = _ins("On", "SEM_SNOWFLAKES", extra={"T_CHOICE_LayerMethod": "Max"})  # a pulse adds over its base
    feat = _ins("Snowflakes", "SEM_SNOWFLAKES")
    dim_beds_under_atmosphere([accent, feat])
    assert _brightness(accent) is None


def test_bed_without_atmosphere_is_left_alone():
    bed = _ins("On", "SEM_ALL")
    other = _ins("Bars", "SEM_ALL")
    dim_beds_under_atmosphere([bed, other])
    assert _brightness(bed) is None


def test_bed_on_different_target_is_left_alone():
    bed = _ins("On", "SEM_ARCHES")            # snow is on SEM_SNOWFLAKES, not here
    feat = _ins("Snowflakes", "SEM_SNOWFLAKES")
    dim_beds_under_atmosphere([bed, feat])
    assert _brightness(bed) is None


def test_non_overlapping_in_time_is_left_alone():
    bed = _ins("On", "SEM_SNOWFLAKES", start=0, end=10000)
    feat = _ins("Snowflakes", "SEM_SNOWFLAKES", start=20000, end=40000)  # a later section
    dim_beds_under_atmosphere([bed, feat])
    assert _brightness(bed) is None
