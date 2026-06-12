"""Tests for energy-driven effect speed (each effect's REAL parameter — the old blanket
`E_SLIDER_<Effect>_Speed` was a real key for only a few effects and silently no-op'd elsewhere
while logging ApplySetting errors in the xLights UI)."""

from xlights_orchestrator.pipeline.beats import SPEED_KEYS, effect_speed_setting


def test_speed_scales_with_energy():
    quiet = float(effect_speed_setting("Spirals", 0.1)["E_TEXTCTRL_Spirals_Movement"])
    loud = float(effect_speed_setting("Spirals", 0.9)["E_TEXTCTRL_Spirals_Movement"])
    assert quiet < loud
    _, lo, hi, _ = SPEED_KEYS["Spirals"]
    assert lo <= quiet and loud <= hi


def test_key_follows_effect_type():
    assert set(effect_speed_setting("Pinwheel", 0.5)) == {"E_SLIDER_Pinwheel_Speed"}
    assert set(effect_speed_setting("Color Wash", 0.5)) == {"E_TEXTCTRL_ColorWash_Cycles"}


def test_sliders_int_textctrls_float():
    assert effect_speed_setting("Meteors", 1.0)["E_SLIDER_Meteors_Speed"] == "45"
    assert effect_speed_setting("Bars", 1.0)["E_TEXTCTRL_Bars_Cycles"] == "4.0"


def test_speedless_effects_emit_nothing():
    for et in ("SingleStrand", "Twinkle", "On", "Strobe", "Lightning", "Shockwave", "NotReal"):
        assert effect_speed_setting(et, 0.8) == {}


def test_intensity_clamped():
    assert effect_speed_setting("Meteors", 5.0)["E_SLIDER_Meteors_Speed"] == "45"
    assert effect_speed_setting("Meteors", -1.0)["E_SLIDER_Meteors_Speed"] == "10"
