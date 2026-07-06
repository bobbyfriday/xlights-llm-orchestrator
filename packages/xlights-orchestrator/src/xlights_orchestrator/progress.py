"""Live progress event bus + browser-backed checkpoint gate (F-I).

An attended ``xlo run --refine`` is a 10–30 minute pipeline whose only live surface used to
be stdout, with blocking ``input()`` prompts parking the async event loop. This module is the
observable spine: a thread-safe append-only ``ProgressBus`` with per-client queue fan-out (the
``live_server`` subscribes each SSE client), a ``NullProgressBus`` twin that is the default so
``--auto`` and every test see zero behavior change, and a ``CheckpointGate`` that lets a browser
answer the four approval checkpoints WITHOUT parking the loop (``await asyncio.to_thread(q.get)``).

Pure stdlib, no pipeline imports (the pipeline injects the bus; the bus never reaches back).
``emit`` swallows-and-logs like ``RevisionLog.write`` — observability must never break a run.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# The event `type` vocabulary the page dispatches on.
EVENT_TYPES = ("stage", "section", "score", "refine", "checkpoint",
               "checkpoint_resolved", "log", "done")


@dataclass(frozen=True)
class ProgressEvent:
    """One immutable point on the run's timeline. ``seq`` is monotonic (assigned by the bus)."""
    seq: int
    ts: float
    type: str
    stage: str = ""
    section: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "ts": self.ts, "type": self.type,
                "stage": self.stage, "section": self.section, "payload": self.payload}


class ProgressBus:
    """Thread-safe, append-only event log with per-client ``queue.Queue`` fan-out.

    ``emit`` is callable from ANY thread (the pipeline's event loop, or a server handler) and
    never raises. ``subscribe(since)`` returns a fresh queue pre-loaded with the replay tail so a
    late/reconnecting client (SSE ``Last-Event-ID``) catches up, then streams live.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[ProgressEvent] = []
        self._seq = itertools.count(1)
        self._subscribers: list[queue.Queue] = []

    def emit(self, type: str, *, stage: str = "", section: int | None = None,
             payload: dict[str, Any] | None = None) -> ProgressEvent | None:
        """Append an event and fan it out. Swallows-and-logs — never breaks a run."""
        try:
            with self._lock:
                ev = ProgressEvent(seq=next(self._seq), ts=time.time(), type=type,
                                   stage=stage, section=section, payload=payload or {})
                self._events.append(ev)
                subs = list(self._subscribers)
            for q in subs:
                try:
                    q.put_nowait(ev)
                except Exception as exc:  # noqa: BLE001 — a poisoned subscriber never sinks emit
                    log.debug("progress fan-out to a subscriber failed: %s", exc)
            return ev
        except Exception as exc:  # noqa: BLE001 — observability must not break the run
            log.debug("progress emit failed: %s", exc)
            return None

    def subscribe(self, since: int = 0) -> queue.Queue:
        """Register a client queue, pre-loaded with events after ``since`` (replay tail)."""
        q: queue.Queue = queue.Queue()
        with self._lock:
            for ev in self._events:
                if ev.seq > since:
                    q.put_nowait(ev)
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def events(self) -> list[ProgressEvent]:
        with self._lock:
            return list(self._events)


class NullProgressBus:
    """No-op twin (the default injection; ``--auto``/tests). Every method is inert."""

    def emit(self, *a, **kw) -> None:
        return None

    def subscribe(self, since: int = 0) -> queue.Queue:
        return queue.Queue()

    def unsubscribe(self, q: queue.Queue) -> None:
        return None

    def events(self) -> list[ProgressEvent]:
        return []


@dataclass
class PendingCheckpoint:
    id: str
    kind: str
    q: queue.Queue


class CheckpointGate:
    """Replaces the four blocking ``input()`` checkpoints with a browser round-trip that never
    parks the asyncio loop.

    ``wait(kind, body_md, options)`` registers a pending checkpoint (single-use random token),
    emits a ``checkpoint`` event, then awaits the browser's action via ``asyncio.to_thread(
    q.get)`` — thread-safe and NON-parking, unlike raw ``input()``. ``resolve(id, action)`` is
    called by the server's ``POST /checkpoint/<id>`` route; a stale/unknown id is rejected.
    """

    def __init__(self, bus: ProgressBus) -> None:
        self.bus = bus
        self._pending: dict[str, PendingCheckpoint] = {}
        self._lock = threading.Lock()

    async def wait(self, kind: str, body_md: str, options: list[str]) -> str:
        cid = uuid.uuid4().hex
        pc = PendingCheckpoint(id=cid, kind=kind, q=queue.Queue(maxsize=1))
        with self._lock:
            self._pending[cid] = pc
        self.bus.emit("checkpoint", stage=kind,
                      payload={"id": cid, "kind": kind, "body_md": body_md, "options": options})
        action = await asyncio.to_thread(pc.q.get)          # non-parking wait for the browser
        with self._lock:
            self._pending.pop(cid, None)
        self.bus.emit("checkpoint_resolved", stage=kind, payload={"id": cid, "action": action})
        return action

    def resolve(self, cid: str, action: str) -> bool:
        """Deliver the browser's action to a waiting ``wait``. Returns False for a stale/unknown
        or already-resolved token (the route answers 409)."""
        with self._lock:
            pc = self._pending.get(cid)
        if pc is None:
            return False
        try:
            pc.q.put_nowait(action)
            return True
        except queue.Full:
            return False                                    # already answered — single-use


# -- browser checkpoint factories ---------------------------------------------
# Each returns a callable with TODAY's checkpoint signature, but backed by the CheckpointGate
# (browser round-trip) instead of a blocking ``input()``. The action string maps to the existing
# return contract: ``bool`` for the interpret/design/final stage gates, ``Decision`` for refine.

def browser_interpret_review(gate: CheckpointGate):
    async def _review(desc_md: str, brief) -> bool:
        action = await gate.wait("interpret", desc_md, ["proceed", "stop"])
        return action == "proceed"
    return _review


def browser_design_review(gate: CheckpointGate):
    async def _review(brief_md: str, plan) -> bool:
        action = await gate.wait("design", brief_md, ["proceed", "stop"])
        return action == "proceed"
    return _review


def browser_final_checkpoint(gate: CheckpointGate):
    async def _final(st) -> bool:
        body = f"Save final sequence ({len(st.instructions)} effects)?"
        action = await gate.wait("final", body, ["save", "discard"])
        return action == "save"
    return _final


def browser_refine_checkpoint(gate: CheckpointGate):
    """Mirrors the `[A/s/k]` prompt: Approve revisions / Stop / Keep-as-final → a ``Decision``."""
    from .refine import Decision

    async def _decide(report, verdict, ledger) -> "Decision":
        lines = [f"objective {report.objective_score} · advisory {report.advisory_score}",
                 f"judge {verdict.score} ({verdict.verdict})"]
        for r in verdict.revisions[:8]:
            lines.append(f"- revise §{r.section_index}: {r.issue}")
        action = await gate.wait("refine", "\n".join(lines), ["approve", "stop", "keep"])
        if action in ("stop", "keep"):
            return Decision(action="accept")
        return Decision(action="approve", revisions=verdict.revisions)
    return _decide


def emit_progress(bus, type: str, *, stage: str = "", section: int | None = None,
                  **payload) -> None:
    """Tiny helper the pipeline calls at a seam: ``emit_progress(progress, "stage", stage="analyze",
    phase="start", ...)``. Tolerates a ``NullProgressBus`` (inert) and never raises."""
    try:
        bus.emit(type, stage=stage, section=section, payload=payload)
    except Exception as exc:  # noqa: BLE001 — a progress emit must never break a run
        log.debug("emit_progress failed: %s", exc)
