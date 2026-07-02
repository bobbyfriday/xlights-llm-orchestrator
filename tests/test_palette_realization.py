"""Tests for realizing the creative brief's colors as effect palettes."""

from __future__ import annotations

import asyncio

from xlights_core.editing import place_preset
from xlights_core.knowledge.colors import palette_from_colors
from xlights_core.knowledge.preset_library import get_library
from xlights_core.knowledge.xsq_extractor import _palette_colors
from xlights_orchestrator.show_plan import EffectInstruction


def run(c):
    return asyncio.run(c)


# -- palette_from_colors ------------------------------------------------------

def test_named_and_hex_build_valid_palette():
    s = palette_from_colors(["warm white", "deep blue", "#DC143C"])
    assert s and "C_BUTTON_Palette1=#FFF1D0" in s and "C_BUTTON_Palette2=#00008B" in s
    assert "C_BUTTON_Palette3=#DC143C" in s
    assert "C_CHECKBOX_Palette1=1" in s and "C_CHECKBOX_Palette3=1" in s   # 3 active slots
    assert "C_CHECKBOX_Palette4=1" not in s                               # only the realized colors active
    # 8 slots present, fills are black
    assert s.count("C_BUTTON_Palette") == 8 and "C_BUTTON_Palette8=#000000" in s


def test_round_trips_through_mined_parser():
    s = palette_from_colors(["amber", "gold"])
    assert set(_palette_colors(s)) >= {"#FFBF00", "#FFD700"}              # same format the corpus uses


def test_hex_passthrough_and_unknown_skipped():
    assert palette_from_colors(["#ff0000", "#00FF00"]).count("C_CHECKBOX_Palette") == 2
    one = palette_from_colors(["boguscolor", "red"])                      # unknown skipped, red kept
    assert "C_BUTTON_Palette1=#FF0000" in one and one.count("C_CHECKBOX_Palette") == 1


def test_empty_or_all_unknown_is_none():
    assert palette_from_colors([]) is None
    assert palette_from_colors(["nope", "alsobad"]) is None


def test_caps_at_eight():
    many = [f"#{i:02X}0000" for i in range(1, 12)]
    s = palette_from_colors(many)
    assert s.count("C_CHECKBOX_Palette") == 8                             # capped at 8 active slots


# -- place_preset precedence: colors override palette_id, fall back cleanly ----

class _FakeClient:
    def __init__(self):
        self.palette = None

    async def get_models(self):
        return ["G1"]

    async def add_effect(self, target, effect, settings, palette, *, layer, start_ms, end_ms):
        self.palette = palette
        return True


def test_place_preset_uses_brief_colors_over_palette_id():
    lib = get_library()
    pid = lib.get_palettes(limit=1)[0].palette_id
    c = _FakeClient()
    run(place_preset(c, "G1", "On", "On#0", palette_id=pid,
                     palette_colors=["deep blue", "amber"], start_ms=0, end_ms=500))
    assert "#00008B" in c.palette and "#FFBF00" in c.palette              # the brief's colors, not the mined one


def test_place_preset_falls_back_to_mined_when_colors_unrealizable():
    lib = get_library()
    mined = lib.get_palette(lib.get_palettes(limit=1)[0].palette_id).palette_string
    c = _FakeClient()
    run(place_preset(c, "G1", "On", "On#0", palette_id=lib.get_palettes(limit=1)[0].palette_id,
                     palette_colors=["bogus", "nope"], start_ms=0, end_ms=500))   # nothing realizes
    assert c.palette == mined                                              # → fell back to the mined palette


# -- EffectInstruction back-compat --------------------------------------------

def test_effect_instruction_palette_colors_defaults():
    ins = EffectInstruction(target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=1000)
    assert ins.palette_colors == []                                       # additive, defaulted
