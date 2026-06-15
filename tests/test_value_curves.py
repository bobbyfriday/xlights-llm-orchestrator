"""Tests for value-curve synthesis + the extra_settings attach path."""

from __future__ import annotations

import asyncio

from xlights_core.editing import place_preset
from xlights_core.knowledge.preset_library import get_library
from xlights_core.knowledge.settings import (
    classify_value_curve,
    parse_value_curve,
    value_curve_is_active,
)
from xlights_core.knowledge.value_curves import brightness_ramp, value_curve_setting


def run(c):
    return asyncio.run(c)


def test_synthesized_curve_is_valid_parametric():
    """CANONICAL format (live round-trip verified): Min/Max = the PARAM's range, P1/P2 = the
    ramp endpoints as real values, RV=TRUE. (Endpoints-in-Min/Max made xLights rescale them —
    our old 84→120 ramp round-tripped as 1027→-84, a flash-to-black crash.)"""
    v = value_curve_setting("Brightness", 0, 100)["C_VALUECURVE_Brightness"]
    assert value_curve_is_active(v) and classify_value_curve(v) == "parametric"
    f = parse_value_curve(v)
    assert f["Type"] == "Ramp" and f["Min"] == "0.00" and f["Max"] == "400.00"
    assert f["P1"] == "0.00" and f["P2"] == "100.00" and f["RV"] == "TRUE"


def test_descending_ramp_keeps_endpoints():
    v = value_curve_setting("Brightness", 200, 50)["C_VALUECURVE_Brightness"]
    f = parse_value_curve(v)
    assert f["P1"] == "200.00" and f["P2"] == "50.00"      # direction lives in P1>P2, not RV
    assert f["Min"] == "0.00" and f["Max"] == "400.00"


def test_brightness_ramp_key():
    assert set(brightness_ramp(0, 100)) == {"C_VALUECURVE_Brightness"}


class _FakeClient:
    def __init__(self): self.settings = None
    async def get_models(self): return ["G1"]
    async def add_effect(self, target, effect, settings, palette, *, layer, start_ms, end_ms):
        self.settings = settings
        return True


def test_extra_settings_appended_to_placement():
    get_library()
    c = _FakeClient()
    run(place_preset(c, "G1", "On", "On#0", extra_settings=brightness_ramp(0, 100),
                     start_ms=0, end_ms=1000))
    assert "C_VALUECURVE_Brightness=Active=TRUE" in c.settings        # appended onto the look's settings
    assert c.settings.count("C_VALUECURVE_Brightness=") == 1
    # value-curve value has no comma → still a clean key=value list
    assert parse_value_curve(c.settings.split("C_VALUECURVE_Brightness=")[1].split(",")[0])["Type"] == "Ramp"


def test_no_extra_settings_unchanged():
    get_library()
    c = _FakeClient()
    run(place_preset(c, "G1", "On", "On#0", start_ms=0, end_ms=1000))
    assert "C_VALUECURVE" not in (c.settings or "")
