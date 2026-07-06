"""Unit tests for the shared retry primitive + the two transient predicates (I2).

Hermetic and fast: retry tests use ``base_delay=0`` and patch ``random.uniform`` /
``asyncio.sleep`` so there is no real backoff wall time.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

from xlights_core.exceptions import (
    XLightsConnectionError,
    XLightsNotImplemented,
    XLightsResponseError,
    XLightsTargetMissing,
    XLightsTimeout,
    XLightsTransportError,
    XLightsUnsavedChanges,
)
from xlights_core.retry import with_retry, xlights_transient
from xlights_orchestrator.models.registry import llm_transient


def run(coro):
    return asyncio.run(coro)


# -- with_retry ---------------------------------------------------------------

def test_success_first_call_no_sleep(monkeypatch):
    calls = {"n": 0}
    slept = []
    monkeypatch.setattr(asyncio, "sleep", lambda d: slept.append(d) or _noop())

    async def fn():
        calls["n"] += 1
        return "ok"

    assert run(with_retry(fn, retryable=lambda e: True, attempts=3, base_delay=0)) == "ok"
    assert calls["n"] == 1 and slept == []          # one call, no backoff


def test_transient_twice_then_success(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(asyncio, "sleep", lambda d: _noop())

    async def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise XLightsConnectionError("blip")
        return "recovered"

    out = run(with_retry(fn, retryable=xlights_transient, attempts=3, base_delay=0))
    assert out == "recovered" and calls["n"] == 3   # three calls, value returned


def test_non_retryable_propagates_first_try():
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        raise XLightsResponseError(status_code=503, message="Unknown model.")

    with pytest.raises(XLightsResponseError):
        run(with_retry(fn, retryable=xlights_transient, attempts=3, base_delay=0))
    assert calls["n"] == 1                            # not retried, original type


def test_exhaustion_keeps_type(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(asyncio, "sleep", lambda d: _noop())

    async def fn():
        calls["n"] += 1
        raise XLightsTimeout("always slow")

    with pytest.raises(XLightsTimeout):
        run(with_retry(fn, retryable=xlights_transient, attempts=3, base_delay=0))
    assert calls["n"] == 3                            # attempts calls, last exception unchanged


def test_backoff_monotone_and_capped(monkeypatch):
    slept: list[float] = []

    async def _sleep(d):
        slept.append(d)

    monkeypatch.setattr(asyncio, "sleep", _sleep)
    monkeypatch.setattr("xlights_core.retry.random.uniform", lambda a, b: 0.0)  # no jitter

    async def fn():
        raise XLightsConnectionError("nope")

    with pytest.raises(XLightsConnectionError):
        run(with_retry(fn, retryable=xlights_transient, attempts=4,
                       base_delay=1.0, factor=2.0, max_delay=3.0))
    # 1.0, 2.0, capped 3.0 (would be 4.0) across the 3 backoffs before the 4th attempt
    assert slept == [1.0, 2.0, 3.0]
    assert all(slept[i] <= slept[i + 1] for i in range(len(slept) - 1))   # monotone


def test_attempts_one_disables(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(asyncio, "sleep", lambda d: _noop())

    async def fn():
        calls["n"] += 1
        raise XLightsConnectionError("x")

    with pytest.raises(XLightsConnectionError):
        run(with_retry(fn, retryable=xlights_transient, attempts=1))
    assert calls["n"] == 1                            # 0/1 disables → one attempt


# -- predicates ---------------------------------------------------------------

def test_llm_transient_true_on_overload_and_ratelimit():
    for code in (408, 429, 500, 502, 503, 529):
        assert llm_transient(ModelHTTPError(code, "m")) is True


def test_llm_transient_false_on_client_errors():
    for code in (400, 401, 403, 404, 413, 422):
        assert llm_transient(ModelHTTPError(code, "m")) is False


def test_llm_transient_false_on_validation():
    assert llm_transient(UnexpectedModelBehavior("schema")) is False


def test_llm_transient_true_on_escaping_transport():
    req = httpx.Request("POST", "http://x")
    assert llm_transient(httpx.ReadTimeout("slow", request=req)) is True
    assert llm_transient(httpx.ConnectError("refused", request=req)) is True


def test_xlights_transient_over_taxonomy():
    assert xlights_transient(XLightsConnectionError("x")) is True
    assert xlights_transient(XLightsTransportError("x")) is True       # subclass of connection
    assert xlights_transient(XLightsTimeout("x")) is True
    assert xlights_transient(XLightsNotImplemented("x")) is False
    assert xlights_transient(XLightsTargetMissing(status_code=503, message="t")) is False
    assert xlights_transient(XLightsUnsavedChanges(status_code=504, message="u")) is False
    assert xlights_transient(XLightsResponseError(status_code=503, message="busy")) is False


async def _noop():
    return None
