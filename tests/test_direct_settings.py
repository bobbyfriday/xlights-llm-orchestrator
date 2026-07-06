"""F-B asset-bound placement: the code-owned Text/Faces settings templates and `place_direct`.

Hermetic — no live xLights. The runtime "valid by construction" half (xLights accepts + renders
the template) is `editing.validate_direct`, a separate `-m live` probe.
"""
from __future__ import annotations

import asyncio

import pytest

from xlights_core.knowledge.constants import classify_kind
from xlights_core.knowledge.direct_settings import (
    DIRECT_TYPES,
    build_faces_settings,
    build_text_settings,
)
from xlights_core.knowledge.settings import parse_settings, serialize_settings


# -- build_text_settings -------------------------------------------------------

def test_text_settings_round_trips():
    s = build_text_settings("MERRY", movement="left", speed=8, font_size=14, bold=True)
    assert serialize_settings(parse_settings(s)) == s
    keys = [k for k, _ in parse_settings(s)]
    assert keys == list(dict.fromkeys(keys))                 # unique keys
    assert dict(parse_settings(s))["E_TEXTCTRL_Text"] == "MERRY"
    assert dict(parse_settings(s))["E_CHOICE_Text_Dir"] == "left"


def test_text_settings_key_kind_audit():
    # every key classifies to a known control kind, except the audited font-picker key.
    s = build_text_settings("HELLO")
    for k, _ in parse_settings(s):
        kind = classify_kind(k)
        if k == "E_FONTPICKER_Text_Font":
            assert kind == "other"                           # the single audited exception
        else:
            assert kind != "other", f"{k} classified as other"


def test_text_settings_center_toggle():
    on = dict(parse_settings(build_text_settings("X", center=True)))
    off = dict(parse_settings(build_text_settings("X", center=False)))
    assert on["E_CHECKBOX_TextToCenter"] == "1"
    assert off["E_CHECKBOX_TextToCenter"] == "0"


def test_text_settings_rejects_bad_inputs():
    with pytest.raises(ValueError):
        build_text_settings("X", movement="sideways")        # unknown movement
    with pytest.raises(ValueError):
        build_text_settings("X", font_size=0)                # non-positive size
    with pytest.raises(ValueError):
        build_text_settings("a,b")                           # comma in glyphs breaks parsing
    with pytest.raises(ValueError):
        build_text_settings("k=v")                           # equals in glyphs breaks parsing


def test_faces_settings_is_a_raising_skeleton():
    with pytest.raises(NotImplementedError):
        build_faces_settings(timing_track="Phonemes", face_definition="Face1")


def test_direct_types_allowlist():
    assert DIRECT_TYPES == frozenset({"Text", "Faces"})


# -- place_direct (fake client) ------------------------------------------------

class _FakeClient:
    """Records the add_effect call; models are a fixed layout."""

    def __init__(self, models, worked=True):
        self.models = list(models)
        self.worked = worked
        self.calls = []

    async def get_models(self):
        return list(self.models)

    async def add_effect(self, target, effect, settings, palette, *, layer, start_ms, end_ms):
        self.calls.append(dict(target=target, effect=effect, settings=settings, palette=palette,
                               layer=layer, start_ms=start_ms, end_ms=end_ms))
        return self.worked

    # no-op lifecycle methods the emitter drives (unused by the place_direct unit tests)
    async def close_sequence(self, *, force=False, quiet=False):
        return None

    async def new_sequence(self, *, duration_secs, frame_ms=50, force=False, view=None):
        return None

    async def render_all(self):
        return None


def test_place_direct_sends_exact_settings_and_palette():
    from xlights_core.editing import place_direct
    c = _FakeClient(["Panel Matrix"])
    s = build_text_settings("HO HO HO")
    merged = asyncio.run(place_direct(
        c, "Panel Matrix", "Text", s,
        palette_colors=["#FF0000", "#00FF00"], layer=0, start_ms=0, end_ms=2000,
    ))
    assert len(c.calls) == 1
    call = c.calls[0]
    assert call["effect"] == "Text" and call["target"] == "Panel Matrix"
    assert call["settings"] == merged == s                    # no extra_settings → unchanged
    assert call["palette"], "palette_colors should resolve to a palette string"


def test_place_direct_extra_settings_parity_with_place_preset():
    """place_direct's extra_settings merge uses the SAME shared helper as place_preset."""
    from xlights_core.editing import _merge_extra_settings
    base = build_text_settings("X")
    extra = {"B_CHOICE_BufferStyle": "Per Model Default", "E_SLIDER_Text_Speed": "99"}
    merged = _merge_extra_settings(base, extra)
    d = dict(parse_settings(merged))
    assert d["E_SLIDER_Text_Speed"] == "99"                   # overrides the base occurrence
    assert d["B_CHOICE_BufferStyle"] == "Per Model Default"   # appended
    # first-occurrence-wins: the overridden key is not duplicated
    assert [k for k, _ in parse_settings(merged)].count("E_SLIDER_Text_Speed") == 1


def test_place_direct_rejects_bad_timing_and_target():
    from xlights_core.editing import place_direct
    c = _FakeClient(["Panel Matrix"])
    s = build_text_settings("X")
    with pytest.raises(ValueError):
        asyncio.run(place_direct(c, "Panel Matrix", "Text", s, start_ms=100, end_ms=100))
    with pytest.raises(ValueError):
        asyncio.run(place_direct(c, "No Such Model", "Text", s, start_ms=0, end_ms=100))


def test_place_direct_raises_on_worked_false():
    from xlights_core.editing import PresetPlacementError, place_direct
    c = _FakeClient(["Panel Matrix"], worked=False)
    s = build_text_settings("X")
    with pytest.raises(PresetPlacementError):
        asyncio.run(place_direct(c, "Panel Matrix", "Text", s, start_ms=0, end_ms=100))


def test_place_direct_rejects_non_round_tripping_settings():
    from xlights_core.editing import place_direct
    c = _FakeClient(["Panel Matrix"])
    with pytest.raises(ValueError):
        # a raw comma in a value corrupts the parse → rejected before any add_effect
        asyncio.run(place_direct(c, "Panel Matrix", "Text", "E_TEXTCTRL_Text=a,b,c",
                                 start_ms=0, end_ms=100))
    assert c.calls == []


# -- emitter branch + back-compat ----------------------------------------------

def test_emitter_branches_to_direct_placement():
    from xlights_orchestrator.effect_emitter import apply_instructions
    from xlights_orchestrator.show_plan import EffectInstruction

    c = _FakeClient(["Panel Matrix"])
    ins = EffectInstruction(target="Panel Matrix", effect_type="Text", look_id="",
                            direct_settings=build_text_settings("NOEL"), start_ms=0, end_ms=2000)
    result = asyncio.run(apply_instructions(c, [ins], duration_secs=10))
    assert len(c.calls) == 1
    d = dict(parse_settings(c.calls[0]["settings"]))
    assert c.calls[0]["effect"] == "Text"
    assert d["E_TEXTCTRL_Text"] == "NOEL"          # the code-built settings reached add_effect
    assert "B_CHOICE_BufferStyle" in d             # buffer-style key still carried on the direct path
    assert result["placed"] and result["placed"][0]["effect"] == "Text"


def test_emitter_direct_skip_on_failure_parity():
    from xlights_orchestrator.effect_emitter import apply_instructions
    from xlights_orchestrator.show_plan import EffectInstruction

    c = _FakeClient(["Panel Matrix"], worked=False)   # xLights refuses → PresetPlacementError → skipped
    ins = EffectInstruction(target="Panel Matrix", effect_type="Text", look_id="",
                            direct_settings=build_text_settings("X"), start_ms=0, end_ms=2000)
    result = asyncio.run(apply_instructions(c, [ins], duration_secs=10))
    assert result["placed"] == [] and len(result["skipped"]) == 1


def test_back_compat_instruction_without_direct_settings():
    from xlights_orchestrator.show_plan import EffectInstruction
    # a pre-change cached instruction JSON has no direct_settings key
    old = {"target": "SEM_ALL", "effect_type": "Twinkle", "look_id": "L1",
           "start_ms": 0, "end_ms": 1000}
    ins = EffectInstruction(**old)
    assert ins.direct_settings == ""               # defaulted → old caches load unchanged


# -- guard rail: direct types never enter the LLM's free-choice menu -----------

def test_direct_types_are_not_placeable():
    from xlights_orchestrator.agents.catalog import placeable_effect_types
    assert DIRECT_TYPES.isdisjoint(set(placeable_effect_types()))
