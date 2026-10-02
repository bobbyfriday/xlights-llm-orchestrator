"""Tests for the xlights-mcp server tools (I6).

Hermetic: no real xLights, no network. MCPServer registers the tool functions but leaves the
module-level names as plain coroutines, so we call them directly with a duck-typed fake client
wrapped in a minimal Context. This exercises pass-through shape, error translation, timing/target
gates, and the lazy-audio fallback. We drive the coroutines with `asyncio.run` to match the repo's
async-test convention (no pytest-asyncio dependency).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

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
    with pytest.raises(ToolError) as ei:
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
    with pytest.raises(ToolError, match="bad timing"):
        run(server.xl_add_effect_raw(_ctx(c), "Tree", "On", start_ms=100, end_ms=100))


def test_add_effect_raw_rejects_target_not_in_layout():
    c = FakeClient(get_models=["Arch1"])
    with pytest.raises(ToolError, match="not in layout"):
        run(server.xl_add_effect_raw(_ctx(c), "Tree", "On", start_ms=0, end_ms=1000))


def test_add_effect_raw_worked_false_raises_placement_error():
    c = FakeClient(get_models=["Tree"], add_effect=False)
    with pytest.raises(ToolError, match="PresetPlacementError"):
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
    with pytest.raises(ToolError, match="audio extra not installed"):
        run(server.xl_analyze_song("s.mp3"))


# -- registration: drive the REAL server object, not just the coroutines ------
# Every test above calls the tool functions directly, which passes even if server
# construction or tool registration is broken — the mcp 1.x→2.x rename surfaced
# only as a module-level ImportError at collection time. These exercise the actual
# MCPServer so an SDK change that breaks registration fails as a test, not a run.

EXPECTED_TOOLS = {
    "xl_get_version", "xl_get_show_folder", "xl_get_models", "xl_get_model",
    "xl_get_controllers", "xl_new_sequence", "xl_open_sequence", "xl_save_sequence",
    "xl_close_sequence", "xl_render_all", "xl_add_effect", "xl_add_effect_raw",
    "xl_validate_preset", "xl_analyze_song", "xl_list_vamp_plugins",
}


def test_every_tool_registers_on_the_server():
    """All 15 tools reach the real MCPServer registry (no xLights, no connection)."""
    names = {t.name for t in run(server.mcp.list_tools())}
    assert names == EXPECTED_TOOLS


def test_registered_tools_are_still_directly_callable():
    """The decorator must leave module-level names as plain coroutines.

    The whole harness above depends on this; some SDK versions could wrap tools
    un-callably (a risk add-engineering-hardening flagged), which would silently
    invalidate every other test in this file rather than failing loudly.
    """
    for name in EXPECTED_TOOLS:
        fn = getattr(server, name)
        assert asyncio.iscoroutinefunction(fn), f"{name} is no longer a coroutine function"


def test_context_is_not_exposed_in_tool_schemas():
    """`ctx` is framework-injected, so it must never appear as a client parameter."""
    for tool in run(server.mcp.list_tools()):
        props = tool.input_schema.get("properties", {})
        assert "ctx" not in props, f"{tool.name} leaks ctx into its input schema"


def test_tool_descriptions_come_from_docstrings():
    """Docstrings are the tool descriptions the MCP client sees — none may be blank."""
    for tool in run(server.mcp.list_tools()):
        assert (tool.description or "").strip(), f"{tool.name} has no description"


def test_anticipated_failures_carry_their_message_to_the_client():
    """An expected failure must reach the client as ToolError WITH its message.

    This is the one guarantee the whole `_call` wrapper exists for, and mcp 2.x
    changed how it is earned: any exception that is not a ToolError is treated as
    a crash, and the client is told only "Error executing tool <name>" while the
    detail stays in the server log. Driven through the real `call_tool` because
    that is where the distinction is actually made — raising the right *type* in a
    unit test proves nothing about what the client ends up seeing.
    """
    # bad timing raises before the tool touches ctx, so no lifespan/client is needed
    with pytest.raises(ToolError) as ei:
        run(server.mcp.call_tool(
            "xl_add_effect_raw",
            {"target": "Tree", "effect": "On", "start_ms": 100, "end_ms": 100}))
    assert not isinstance(ei.value, UnexpectedToolError), \
        "raised as a crash — the message was withheld from the client"
    assert "bad timing: start=100 end=100" in str(ei.value)
