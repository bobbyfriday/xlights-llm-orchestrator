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


def make_client(handler) -> XLightsClient:
    transport = httpx.MockTransport(handler)
    ac = httpx.AsyncClient(
        transport=transport,
        base_url="http://xlights.test",
        headers={"Accept": "application/json"},
    )
    return XLightsClient(client=ac)


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
