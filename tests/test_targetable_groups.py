"""Tests for the targetable-group probe + cache + fail-safe."""

from __future__ import annotations

import asyncio

import pytest

from xlights_core.exceptions import XLightsTargetMissing
from xlights_orchestrator.pipeline import groups as G


def run(c):
    return asyncio.run(c)


class _FakeClient:
    """A layout where only some groups accept effects; counts probe attempts."""
    def __init__(self, names, targetable, *, place_error=None):
        self._names = names
        self._targetable = set(targetable)
        self._place_error = place_error          # an exception to raise on a specific group
        self.probe_calls = 0
        self.saved = False
        self.closes = 0

    async def get_group_names(self):
        return list(self._names)

    async def close_sequence(self, *, force=False, quiet=False):
        self.closes += 1

    async def new_sequence(self, *, duration_secs, frame_ms=50, media_file=None, view=None, force=False):
        return None

    async def save_sequence(self, name=None):
        self.saved = True


async def _fake_place(client, target, effect_type, look_id, **kw):
    client.probe_calls += 1
    if client._place_error and target == client._place_error[0]:
        raise client._place_error[1]
    if target not in client._targetable:
        raise XLightsTargetMissing(status_code=503, message="missing", command="addEffect")
    return "settings"


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    monkeypatch.setattr(G, "place_preset", _fake_place)
    monkeypatch.setattr(G, "candidate_look_ids", lambda t: ["On#0"])
    monkeypatch.setattr(G, "_SETTLE_SECS", 0)          # skip the populate-settle in tests


def test_probe_keeps_only_targetable(tmp_path):
    c = _FakeClient(["A", "B", "C", "D"], targetable=["A", "C"])
    out = run(G.targetable_groups(c, cache_root=tmp_path))
    assert out == ["A", "C"] and not c.saved          # filtered; disposable never saved


def test_cache_reused_no_reprobe(tmp_path):
    c = _FakeClient(["A", "B", "C"], targetable=["A"])
    run(G.targetable_groups(c, cache_root=tmp_path))
    first = c.probe_calls
    assert first == 3                                  # probed all 3
    c.probe_calls = 0
    out = run(G.targetable_groups(c, cache_root=tmp_path))
    assert out == ["A"] and c.probe_calls == 0         # second call hit the cache, no re-probe


def test_layout_change_reprobes(tmp_path):
    c = _FakeClient(["A", "B"], targetable=["A"])
    run(G.targetable_groups(c, cache_root=tmp_path))
    c2 = _FakeClient(["A", "B", "X"], targetable=["A", "X"])   # different group set → new fingerprint
    run(G.targetable_groups(c2, cache_root=tmp_path))
    assert c2.probe_calls == 3                          # re-probed the new layout


def test_non_target_error_falls_back_no_cache(tmp_path):
    # a transient (non-target) error mid-probe → full list, and NO cache written
    c = _FakeClient(["A", "B", "C"], targetable=["A", "C"],
                    place_error=("B", RuntimeError("blip")))
    out = run(G.targetable_groups(c, cache_root=tmp_path))
    assert out == ["A", "B", "C"]                      # full list (no wrong exclusion)
    assert not list(tmp_path.glob("targetable_groups_*.json"))   # cache NOT poisoned → re-probe next run


def test_empty_probe_falls_back(tmp_path):
    c = _FakeClient(["A", "B"], targetable=[])          # nothing targetable → distrust → full list
    assert run(G.targetable_groups(c, cache_root=tmp_path)) == ["A", "B"]
    assert not list(tmp_path.glob("*.json"))
