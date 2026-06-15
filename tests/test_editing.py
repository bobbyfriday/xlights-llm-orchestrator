"""Tests for the xLights write path (sequence editing + preset placement/validation).

Unit tests use httpx.MockTransport (hermetic). Live tests need a running xLights with
no user sequence open, and are opt-in via -m live.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from xlights_core import (
    XLightsClient,
    XLightsNotImplemented,
    XLightsResponseError,
    XLightsTargetMissing,
    XLightsUnsavedChanges,
)
from xlights_core.editing import PresetPlacementError, place_preset, validate_preset
from xlights_core.knowledge import get_library
from xlights_core.knowledge.validators import KnobValueError

lib = get_library()


def make_client(handler) -> XLightsClient:
    return XLightsClient(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://xlights.test",
        headers={"Accept": "application/json"}))


def run(coro):
    return asyncio.run(coro)


# -- error taxonomy (the overloaded 504 + target-missing 503) ------------------

def _resp(status, msg):
    return httpx.Response(status, json={"msg": msg})


def test_add_effect_no_sequence_open():
    c = make_client(lambda r: _resp(503, "Sequence not open."))
    with pytest.raises(XLightsResponseError) as ei:
        run(c.add_effect("Tree", "On", start_ms=0, end_ms=100))
    assert not isinstance(ei.value, XLightsTargetMissing)


def test_add_effect_target_missing():
    c = make_client(lambda r: _resp(503, "target element doesn't exists."))
    with pytest.raises(XLightsTargetMissing):
        run(c.add_effect("Ghost", "On", start_ms=0, end_ms=100))


def test_close_unsaved_is_unsaved_changes_not_not_implemented():
    c = make_client(lambda r: _resp(504, "Sequence has unsaved changes."))
    with pytest.raises(XLightsUnsavedChanges):
        run(c.close_sequence())


def test_504_not_implemented_still_maps_to_not_implemented():
    c = make_client(lambda r: _resp(504, "Not implemented."))
    with pytest.raises(XLightsNotImplemented):
        run(c.render_all())


# -- worked flag --------------------------------------------------------------

def test_new_sequence_force_is_optin():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["params"] = dict(req.url.params)
        return _resp(200, "Sequence created.")

    run(make_client(handler).new_sequence(duration_secs=10))
    assert "force" not in seen["params"]            # never forced by default
    run(make_client(handler).new_sequence(duration_secs=10, force=True))
    assert seen["params"].get("force") == "true"    # only when explicit


def test_close_defaults_non_force():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["params"] = dict(req.url.params)
        return _resp(200, "Sequence closed.")

    run(make_client(handler).close_sequence())
    assert "force" not in seen["params"]


def test_add_effect_worked_true_false():
    c_ok = make_client(lambda r: httpx.Response(200, json={"msg": "Added Effects.", "worked": "true"}))
    c_no = make_client(lambda r: httpx.Response(200, json={"msg": "Added Effects.", "worked": "false"}))
    assert run(c_ok.add_effect("Tree", "On", start_ms=0, end_ms=100)) is True
    assert run(c_no.add_effect("Tree", "On", start_ms=0, end_ms=100)) is False


# -- write-lock serializes mutations ------------------------------------------

def test_write_lock_serializes():
    c = make_client(lambda r: _resp(200, "ok"))
    active = max_active = 0

    async def fake(cmd, params=None, timeout=None, method="GET"):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return {"msg": "ok"}

    c._request = fake  # type: ignore[assignment]

    async def go():
        await asyncio.gather(*(c._mutate("x") for _ in range(6)))

    run(go())
    assert max_active == 1


# -- place_preset validation --------------------------------------------------

def _layout_and_addeffect(worked="true", models=("Tree",)):

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/getModels":
            return httpx.Response(200, json={"models": list(models)})
        if req.url.path == "/addEffect":
            return httpx.Response(200, json={"msg": "Added Effects.", "worked": worked})
        return httpx.Response(404, json={"msg": "no route"})

    return handler


def _first_look(effect_type):
    looks = lib.get_looks(effect_type)
    assert looks, f"no looks for {effect_type}"
    return looks[0]


def test_place_preset_happy_path():
    look = _first_look("On")
    c = make_client(_layout_and_addeffect())
    settings = run(place_preset(c, "Tree", "On", look.look_id, start_ms=0, end_ms=1000))
    assert isinstance(settings, str)


def test_place_preset_unknown_target():
    look = _first_look("On")
    c = make_client(_layout_and_addeffect())
    with pytest.raises(ValueError):
        run(place_preset(c, "NotAModel", "On", look.look_id, start_ms=0, end_ms=1000))


def test_place_preset_bad_timing():
    look = _first_look("On")
    c = make_client(_layout_and_addeffect())
    with pytest.raises(ValueError):
        run(place_preset(c, "Tree", "On", look.look_id, start_ms=500, end_ms=100))


def test_place_preset_worked_false_raises():
    look = _first_look("On")
    c = make_client(_layout_and_addeffect(worked="false"))
    with pytest.raises(PresetPlacementError):
        run(place_preset(c, "Tree", "On", look.look_id, start_ms=0, end_ms=1000))


def test_place_preset_bad_knob_value():
    # find a look with a numeric slider knob and push out of range
    for look in lib.get_looks("Shockwave"):
        nk = next((k for k in look.knobs if k.numeric and k.min is not None), None)
        if nk:
            c = make_client(_layout_and_addeffect())
            with pytest.raises(KnobValueError):
                run(place_preset(c, "Tree", "Shockwave", look.look_id,
                                 knob_values={nk.key: str((nk.max or 0) + 1e6)},
                                 start_ms=0, end_ms=1000))
            return
    pytest.skip("no numeric Shockwave knob")


# -- live validation (closes effect-presets 6.6) ------------------------------

LIVE_BASE = "http://127.0.0.1:49913"


def _xlights_up() -> bool:
    try:
        httpx.get(f"{LIVE_BASE}/getVersion", timeout=2)
        return True
    except Exception:
        return False


live = pytest.mark.skipif(not _xlights_up(), reason="xLights not reachable")


@pytest.mark.live
@live
def test_live_validate_presets_sample():
    async def go():
        async with XLightsClient() as c:
            # a default preset and a tuned (novel knob combo) one
            on = lib.get_looks("On")[0]
            r1 = await validate_preset(c, "On", on.look_id)
            assert r1["accepted"], r1

            tuned = None
            for look in lib.get_looks("Shockwave"):
                nk = next((k for k in look.knobs if k.numeric and k.min != k.max), None)
                if nk:
                    mid = str(int((nk.min + nk.max) / 2))
                    tuned = (look, {nk.key: mid})
                    break
            if tuned:
                look, kv = tuned
                r2 = await validate_preset(c, "Shockwave", look.look_id, knob_values=kv)
                assert r2["accepted"], r2

    run(go())
