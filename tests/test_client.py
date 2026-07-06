"""Unit tests for XLightsClient using recorded fixtures over httpx.MockTransport.

No live xLights required. Error/timeout paths are simulated by raising the
corresponding httpx exceptions from the mock handler.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from xlights_core import (
    Controller,
    Model,
    XLightsClient,
    XLightsConnectionError,
    XLightsNotImplemented,
    XLightsResponseError,
    XLightsTimeout,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def make_client(handler, *, retry_attempts: int = 3) -> XLightsClient:
    transport = httpx.MockTransport(handler)
    ac = httpx.AsyncClient(
        transport=transport,
        base_url="http://xlights.test",
        headers={"Accept": "application/json"},
    )
    return XLightsClient(client=ac, retry_attempts=retry_attempts)


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch):
    """No real backoff wall time in the client retry tests."""
    async def _sleep(_):
        return None
    monkeypatch.setattr("xlights_core.retry.asyncio.sleep", _sleep)


def run(coro):
    return asyncio.run(coro)


def default_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    params = dict(request.url.params)
    if path == "/getVersion":
        return httpx.Response(200, json=load("getVersion.json"))
    if path == "/getShowFolder":
        return httpx.Response(200, json=load("getShowFolder.json"))
    if path == "/getModels":
        if params.get("groups") == "false":
            return httpx.Response(200, json=load("getModels.models.json"))
        if params.get("models") == "false":
            return httpx.Response(200, json=load("getModels.groups.json"))
        return httpx.Response(200, json=load("getModels.json"))
    if path == "/getModel":
        if params.get("model") == "Matrix":
            return httpx.Response(200, json=load("getModel.json"))
        return httpx.Response(503, json=load("error_unknown_model.json"))
    if path == "/getControllers":
        return httpx.Response(200, json=load("getControllers.json"))
    return httpx.Response(404, json={"msg": "no route"})


# -- happy paths ---------------------------------------------------------------

def test_get_version():
    assert run(make_client(default_handler).get_version()) == "2024.20"


def test_get_show_folder():
    assert run(make_client(default_handler).get_show_folder()) == "/Users/rob/Documents/xLights"


def test_get_models_all():
    names = run(make_client(default_handler).get_models())
    assert names == ["Arches", "Matrix", "Mega Tree", "House Outline", "All Models", "Props Group"]


def test_get_models_split():
    c = make_client(default_handler)
    assert run(c.get_model_names()) == ["Arches", "Matrix", "Mega Tree", "House Outline"]
    assert run(c.get_group_names()) == ["All Models", "Props Group"]


def test_empty_layout_returns_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    assert run(make_client(handler).get_models()) == []


def test_get_model_known():
    model = run(make_client(default_handler).get_model("Matrix"))
    assert isinstance(model, Model)
    assert model.name == "Matrix"
    # unknown/extra fields are retained
    assert model.model_dump().get("StringType") == "RGB Nodes"


def test_get_controllers():
    controllers = run(make_client(default_handler).get_controllers())
    assert [c.name for c in controllers] == ["Controller 1", "Controller 2"]
    assert all(isinstance(c, Controller) for c in controllers)


# -- error taxonomy ------------------------------------------------------------

def test_unknown_model_raises_response_error():
    with pytest.raises(XLightsResponseError) as ei:
        run(make_client(default_handler).get_model("Nope"))
    assert ei.value.status_code == 503
    assert ei.value.message == "Unknown model."


def test_not_implemented_maps_to_504_type():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(504, json={"msg": "Not implemented."})

    with pytest.raises(XLightsNotImplemented):
        run(make_client(handler).get_version())


def test_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(XLightsConnectionError):
        run(make_client(handler).get_version())


def test_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(XLightsTimeout):
        run(make_client(handler).get_version())


# -- I2: transient transport retry --------------------------------------------

def test_read_retries_connect_error_then_succeeds():
    """A read (getModels) that ConnectErrors twice then returns 200 → 3 transport calls, result."""
    n = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        n["i"] += 1
        if n["i"] <= 2:
            raise httpx.ConnectError("blip", request=request)
        return httpx.Response(200, json=load("getModels.json"))

    names = run(make_client(handler).get_models())
    assert n["i"] == 3 and names[0] == "Arches"      # retried twice, then returned


def test_read_retries_timeout():
    """A read retries a ReadTimeout too (reads retry on connection error AND timeout)."""
    n = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        n["i"] += 1
        if n["i"] <= 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json=load("getVersion.json"))

    assert run(make_client(handler).get_version()) == "2024.20"
    assert n["i"] == 2


def test_mutation_retries_connect_error_placed_once():
    """A mutation (addEffect) ConnectErrors once then 200 → placed exactly once (one 200)."""
    n = {"i": 0, "placed": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        n["i"] += 1
        if n["i"] <= 1:
            raise httpx.ConnectError("blip", request=request)
        n["placed"] += 1
        return httpx.Response(200, json={"worked": "true"})

    ok = run(make_client(handler).add_effect("G1", "On", start_ms=0, end_ms=500))
    assert ok is True and n["placed"] == 1           # retried once, applied exactly once


def test_mutation_timeout_not_retried():
    """A mutation ReadTimeout is NOT retried (post-send timeout is ambiguous → no double-apply)."""
    n = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        n["i"] += 1
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(XLightsTimeout):
        run(make_client(handler).add_effect("G1", "On", start_ms=0, end_ms=500))
    assert n["i"] == 1                                # one attempt, surfaced immediately


def test_mutation_semantic_503_not_retried():
    """A 503 'Unknown model.' on a mutation is a semantic error → immediate, no retry."""
    n = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        n["i"] += 1
        return httpx.Response(503, json={"msg": "Unknown model."})

    with pytest.raises(XLightsResponseError):
        run(make_client(handler).add_effect("G1", "On", start_ms=0, end_ms=500))
    assert n["i"] == 1


def test_retry_disabled_attempts_once():
    """retry_attempts=0/1 reproduces pre-retry behavior — one attempt, connection error surfaces."""
    n = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        n["i"] += 1
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(XLightsConnectionError):
        run(make_client(handler, retry_attempts=0).get_version())
    assert n["i"] == 1


def test_mutation_retry_holds_lock_ordering():
    """A retrying mutation holds the write lock across its backoff: a concurrent second mutation's
    transport call happens only AFTER the first completes (ordering preserved)."""
    order: list[str] = []
    first_done = {"v": False}

    def handler(request: httpx.Request) -> httpx.Response:
        which = dict(request.url.params).get("target")
        if which == "A" and not first_done["v"]:
            first_done["v"] = True
            order.append("A-attempt1")
            raise httpx.ConnectError("blip", request=request)   # forces a retry under the lock
        order.append(f"{which}-transport")
        return httpx.Response(200, json={"worked": "true"})

    c = make_client(handler)

    async def go():
        a = asyncio.create_task(c.add_effect("A", "On", start_ms=0, end_ms=1))
        await asyncio.sleep(0)                          # let A grab the lock + hit its retry
        b = asyncio.create_task(c.add_effect("B", "On", start_ms=0, end_ms=1))
        await asyncio.gather(a, b)

    run(go())
    # A's retried transport call must precede B's first transport call (lock held across backoff).
    assert order.index("A-transport") < order.index("B-transport")


# -- opt-in live smoke test ----------------------------------------------------

@pytest.mark.live
def test_live_smoke():
    async def go():
        async with XLightsClient() as client:
            version = await client.get_version()
            assert version
            await client.get_show_folder()
            await client.get_models()

    try:
        run(go())
    except XLightsConnectionError:
        pytest.skip("xLights not reachable at XLIGHTS_BASE_URL")
