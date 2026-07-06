"""Tests for run-scoped LLM token telemetry (I1).

Hermetic: no API key, no network. Covers UsageLog accumulation/delta, the best-effort
duck-typed capture (a fake without usage is a no-op), the RunUsage→RoleUsage field mapping
(a real RunUsage so an upstream rename breaks a test not a run), and ContextVar isolation
including concurrent asyncio.gather tasks recording into the same run's log.
"""

from __future__ import annotations

import asyncio
import contextvars
from types import SimpleNamespace

from pydantic_ai.usage import RunUsage

from xlights_orchestrator import telemetry as tel


def _run(coro):
    return asyncio.run(coro)


# -- UsageLog accumulation ----------------------------------------------------

def test_usage_log_accumulates_and_drains():
    ul = tel.UsageLog()
    ul.add("judge", tel.RoleUsage(requests=1, input_tokens=100, output_tokens=20))
    ul.add("judge", tel.RoleUsage(requests=1, input_tokens=50, output_tokens=10))
    # totals sum across both records
    assert ul.totals["judge"].input_tokens == 150
    assert ul.totals["judge"].output_tokens == 30
    assert ul.totals["judge"].requests == 2
    # drain empties the delta WINDOW, not the totals
    d = ul.drain_delta()
    assert d["judge"].input_tokens == 150
    assert ul.snapshot()["judge"].input_tokens == 150         # totals intact
    assert ul.drain_delta() == {}                              # window emptied


def test_drain_delta_partitions_totals():
    ul = tel.UsageLog()
    ul.add("generator", tel.RoleUsage(input_tokens=100, output_tokens=10))
    d1 = ul.drain_delta()
    ul.add("generator", tel.RoleUsage(input_tokens=40, output_tokens=5))
    d2 = ul.drain_delta()
    # the per-record deltas partition the run total
    assert d1["generator"].input_tokens == 100
    assert d2["generator"].input_tokens == 40
    assert ul.snapshot()["generator"].input_tokens == 140


def test_drain_delta_omits_empty_roles():
    ul = tel.UsageLog()
    ul.add("judge", tel.RoleUsage())          # zero usage
    assert ul.drain_delta() == {}             # nothing to report


# -- RunUsage → RoleUsage field mapping (guards an upstream rename) ------------

def test_run_usage_mapping():
    u = RunUsage(input_tokens=100, output_tokens=50, cache_read_tokens=10,
                 cache_write_tokens=5, requests=2)
    r = tel._from_run_usage(u)
    assert (r.input_tokens, r.output_tokens, r.cache_read_tokens,
            r.cache_write_tokens, r.requests) == (100, 50, 10, 5, 2)


# -- best-effort capture ------------------------------------------------------

def _in_ctx(fn):
    """Run fn in a fresh copied context so a start_run() doesn't leak into other tests."""
    return contextvars.copy_context().run(fn)


def test_record_captures_property_usage():
    def body():
        ul = tel.start_run()
        res = SimpleNamespace(usage=RunUsage(input_tokens=7, output_tokens=3, requests=1))
        tel.record("judge", res)
        return ul.snapshot()
    snap = _in_ctx(body)
    assert snap["judge"].input_tokens == 7 and snap["judge"].output_tokens == 3


def test_record_captures_method_usage():
    def body():
        ul = tel.start_run()
        res = SimpleNamespace(usage=lambda: RunUsage(input_tokens=4, output_tokens=1))
        tel.record("generator", res)
        return ul.snapshot()
    snap = _in_ctx(body)
    assert snap["generator"].input_tokens == 4


def test_record_without_usage_is_noop():
    def body():
        ul = tel.start_run()
        tel.record("generator", SimpleNamespace(output="hi"))   # a fake with no usage view
        tel.record("generator", object())                        # nothing usage-like at all
        return ul.snapshot()
    assert _in_ctx(body) == {}


def test_record_no_active_log_is_noop():
    def body():
        tel._current.set(None)   # no collector installed in THIS (copied) context
        tel.record("judge", SimpleNamespace(usage=RunUsage(input_tokens=99)))
        return tel.current()
    assert _in_ctx(body) is None


# -- ContextVar isolation + concurrency ---------------------------------------

def test_concurrent_analysts_record_into_same_run():
    async def body():
        ul = tel.start_run()

        async def analyst(n):
            res = SimpleNamespace(usage=RunUsage(input_tokens=n, output_tokens=1, requests=1))
            tel.record("analyst", res)
            return n

        await asyncio.gather(analyst(10), analyst(20), analyst(30))
        return ul.snapshot()

    # run under a copied context so start_run stays scoped to this task tree
    snap = _in_ctx(lambda: _run(body()))
    assert snap["analyst"].input_tokens == 60       # all three gather tasks recorded
    assert snap["analyst"].requests == 3
