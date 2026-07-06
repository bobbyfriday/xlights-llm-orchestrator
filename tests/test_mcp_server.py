"""Tests for the xlights-mcp server tools (I6).

Hermetic: no real xLights, no network. FastMCP registers the tool functions but leaves the
module-level names as plain coroutines, so we call them directly with a duck-typed fake client
wrapped in a minimal Context. This exercises pass-through shape, error translation, timing/target
gates, and the lazy-audio fallback. We drive the coroutines with `asyncio.run` to match the repo's
async-test convention (no pytest-asyncio dependency).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from xlights_core.exceptions import XLightsConnectionError
from xlights_core.knowledge.validators import KnobValueError

from xlights_mcp import server


def run(coro):
    return asyncio.run(coro)


# -- harness ------------------------------------------------------------------

def _ctx(client):
    """A minimal Context: server._client reads ctx.request_context.lifespan_context['client']."""
    return SimpleNamespace(
        request_context=SimpleNamespace(lifespan_context={"client": client}))


class FakeClient:
    """Duck-typed stand-in — only the methods a test drives are defined."""

    def __init__(self, **methods):
        self._methods = methods
        self.calls: dict = {}

    def __getattr__(self, name):
        methods = self.__dict__.get("_methods", {})
        if name in methods:
            impl = methods[name]

            async def _coro(*args, **kwargs):
                self.calls[name] = (args, kwargs)
                if callable(impl):
                    return impl(*args, **kwargs)
                return impl

            return _coro
        raise AttributeError(name)


# -- read tools: pass-through shape -------------------------------------------

def test_get_version_passthrough():
    c = FakeClient(get_version="9.1.0")
    assert run(server.xl_get_version(_ctx(c))) == "9.1.0"


def test_get_show_folder_passthrough():
    c = FakeClient(get_show_folder="/shows/xmas")
    assert run(server.xl_get_show_folder(_ctx(c))) == "/shows/xmas"


def test_get_models_splits_models_and_groups():
    c = FakeClient(get_model_names=["Tree", "Arch1"], get_group_names=["SEM_ALL"])
    out = run(server.xl_get_models(_ctx(c)))
    assert out == {"models": ["Tree", "Arch1"], "groups": ["SEM_ALL"]}


def test_get_model_dumps_model():
    model = SimpleNamespace(model_dump=lambda: {"name": "Tree", "type": "Tree"})
    c = FakeClient(get_model=model)
    assert run(server.xl_get_model("Tree", _ctx(c))) == {"name": "Tree", "type": "Tree"}


def test_get_controllers_dumps_each():
    ctrls = [SimpleNamespace(model_dump=lambda: {"id": 1}),
             SimpleNamespace(model_dump=lambda: {"id": 2})]
    c = FakeClient(get_controllers=ctrls)
    assert run(server.xl_get_controllers(_ctx(c))) == [{"id": 1}, {"id": 2}]


# -- _call error translation --------------------------------------------------

@pytest.mark.parametrize("exc, prefix", [
    (XLightsConnectionError("down"), "XLightsConnectionError: down"),
    (KnobValueError("bad knob"), "KnobValueError: bad knob"),
    (ValueError("nope"), "ValueError: nope"),
    (KeyError("missing"), "KeyError:"),
])
def test_call_translates_typed_errors(exc, prefix):
    def _raise(*a, **k):
        raise exc
    c = FakeClient(get_version=_raise)
    with pytest.raises(RuntimeError) as ei:
        run(server.xl_get_version(_ctx(c)))
    assert str(ei.value).startswith(prefix)


# -- write tools: verbatim forwarding -----------------------------------------

def test_new_sequence_forwards_all_kwargs_default_force_false():
    c = FakeClient(new_sequence=None)
    out = run(server.xl_new_sequence(_ctx(c), duration_secs=30, frame_ms=25, media_file="s.mp3"))
    assert out == "created"
    _, kwargs = c.calls["new_sequence"]
    assert kwargs == {"duration_secs": 30, "frame_ms": 25, "media_file": "s.mp3", "force": False}


def test_close_sequence_forwards_force_and_quiet():
    c = FakeClient(close_sequence=None)
    run(server.xl_close_sequence(_ctx(c), force=True, quiet=True))
    _, kwargs = c.calls["close_sequence"]
    assert kwargs == {"force": True, "quiet": True}


def test_save_sequence_passes_name_none_through():
    c = FakeClient(save_sequence=None)
    run(server.xl_save_sequence(_ctx(c)))
    args, _ = c.calls["save_sequence"]
    assert args == (None,)


# -- xl_add_effect_raw gates --------------------------------------------------

def test_add_effect_raw_rejects_bad_timing_before_any_client_call():
    c = FakeClient()               # no methods → any client call would AttributeError
    with pytest.raises(ValueError, match="bad timing"):
        run(server.xl_add_effect_raw(_ctx(c), "Tree", "On", start_ms=100, end_ms=100))


def test_add_effect_raw_rejects_target_not_in_layout():
    c = FakeClient(get_models=["Arch1"])
    with pytest.raises(ValueError, match="not in layout"):
        run(server.xl_add_effect_raw(_ctx(c), "Tree", "On", start_ms=0, end_ms=1000))


def test_add_effect_raw_worked_false_raises_placement_error():
    c = FakeClient(get_models=["Tree"], add_effect=False)
    with pytest.raises(RuntimeError, match="PresetPlacementError"):
        run(server.xl_add_effect_raw(_ctx(c), "Tree", "On", start_ms=0, end_ms=1000))


def test_add_effect_raw_happy_path():
    c = FakeClient(get_models=["Tree"], add_effect=True)
    out = run(server.xl_add_effect_raw(_ctx(c), "Tree", "On", start_ms=0, end_ms=1000))
    assert out == {"placed": True}


# -- xl_add_effect / xl_validate_preset forwarding (monkeypatched seams) -------

def test_add_effect_forwards_knobs_palette_layer(monkeypatch):
    captured = {}

    async def _fake_place_preset(client, target, effect_type, look_id, **kw):
        captured.update(target=target, effect_type=effect_type, look_id=look_id, **kw)
        return "settings-string"

    monkeypatch.setattr(server, "place_preset", _fake_place_preset)
    c = FakeClient()
    out = run(server.xl_add_effect(
        _ctx(c), "Tree", "On", "look-1", 0, 1000,
        knob_values={"Speed": "5"}, palette_id="P1", layer=2))
    assert out == {"placed": True, "settings": "settings-string"}
    assert captured["target"] == "Tree" and captured["look_id"] == "look-1"
    assert captured["knob_values"] == {"Speed": "5"}
    assert captured["palette_id"] == "P1" and captured["layer"] == 2


def test_validate_preset_forwards(monkeypatch):
    captured = {}

    async def _fake_validate(client, effect_type, look_id, **kw):
        captured.update(effect_type=effect_type, look_id=look_id, **kw)
        return {"ok": True}

    monkeypatch.setattr(server, "validate_preset", _fake_validate)
    c = FakeClient()
    out = run(server.xl_validate_preset(
        _ctx(c), "On", "look-1", knob_values={"Speed": "5"}, target="Tree"))
    assert out == {"ok": True}
    assert captured["effect_type"] == "On" and captured["target"] == "Tree"


# -- audio: import failure surfaces as a clean tool error ---------------------

def test_analyze_song_missing_audio_extra_clean_error(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _blocked(name, *a, **k):
        if name.startswith("xlights_core.audio"):
            raise ImportError("no audio extra")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _blocked)
    with pytest.raises(RuntimeError, match="audio extra not installed"):
        run(server.xl_analyze_song("s.mp3"))
