"""Unit tests for the progress event bus + checkpoint gate (F-I)."""

from __future__ import annotations

import asyncio
import queue
import threading

from xlights_orchestrator.progress import CheckpointGate, NullProgressBus, ProgressBus


def test_emit_subscribe_ordering_and_seq_monotonic():
    bus = ProgressBus()
    q = bus.subscribe()
    bus.emit("stage", stage="analyze")
    bus.emit("stage", stage="groups")
    a = q.get_nowait(); b = q.get_nowait()
    assert a.seq == 1 and b.seq == 2 and a.seq < b.seq
    assert a.stage == "analyze" and b.stage == "groups"


def test_late_subscriber_replays_since():
    bus = ProgressBus()
    bus.emit("stage", stage="analyze")           # seq 1
    bus.emit("stage", stage="groups")            # seq 2
    bus.emit("stage", stage="design")            # seq 3
    q = bus.subscribe(since=2)                    # reconnect from Last-Event-ID 2
    ev = q.get_nowait()
    assert ev.seq == 3 and ev.stage == "design"  # replay starts at 3
    assert q.empty()


def test_fan_out_to_two_queues():
    bus = ProgressBus()
    q1 = bus.subscribe(); q2 = bus.subscribe()
    bus.emit("done")
    assert q1.get_nowait().type == "done" and q2.get_nowait().type == "done"


def test_unsubscribe_stops_delivery():
    bus = ProgressBus()
    q = bus.subscribe()
    bus.unsubscribe(q)
    bus.emit("stage", stage="x")
    assert q.empty()


def test_emit_never_raises_on_poisoned_subscriber():
    bus = ProgressBus()

    class _FullQueue(queue.Queue):
        def put_nowait(self, item):
            raise queue.Full("poisoned")

    bad = _FullQueue()
    good = bus.subscribe()
    with bus._lock:
        bus._subscribers.append(bad)             # inject a poisoned subscriber
    ev = bus.emit("done")                          # must not raise
    assert ev is not None and good.get_nowait().type == "done"


def test_thread_safety_correct_count_and_order():
    bus = ProgressBus()
    q = bus.subscribe()
    N = 200

    def worker():
        for _ in range(N):
            bus.emit("log")

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    got = []
    while not q.empty():
        got.append(q.get_nowait().seq)
    assert len(got) == 4 * N
    assert got == sorted(got)                      # monotonic seq under concurrent emit
    assert len(set(got)) == len(got)               # no duplicate seq


def test_null_bus_is_inert():
    nb = NullProgressBus()
    assert nb.emit("stage") is None
    assert nb.subscribe().empty()
    assert nb.events() == []


# -- CheckpointGate -----------------------------------------------------------

def test_checkpoint_gate_resolves_without_parking():
    bus = ProgressBus()
    gate = CheckpointGate(bus)
    q = bus.subscribe()

    async def go():
        task = asyncio.create_task(gate.wait("interpret", "review me", ["proceed", "stop"]))
        await asyncio.sleep(0)                      # let the checkpoint register + emit
        # find the checkpoint event + id
        cid = None
        while not q.empty():
            ev = q.get_nowait()
            if ev.type == "checkpoint":
                cid = ev.payload["id"]
        assert cid is not None
        assert gate.resolve(cid, "proceed") is True
        assert gate.resolve(cid, "proceed") is False   # single-use → stale afterward
        return await task

    assert asyncio.run(go()) == "proceed"


def test_checkpoint_gate_rejects_unknown_id():
    gate = CheckpointGate(ProgressBus())
    assert gate.resolve("nonexistent", "proceed") is False
