"""Run-scoped LLM token telemetry — turn every run into evaluation data.

Every PydanticAI ``AgentRunResult`` carries a ``.usage()`` returning a ``RunUsage``
dataclass (request/response token counts, prompt-cache splits). We capture it at each
``.run()`` call site into a run-scoped :class:`UsageLog` held in a ``ContextVar`` so a
collector installed at the top of ``run_pipeline``/``regen_section`` reaches every await
point below it — including the concurrently-run analysts (``asyncio.gather`` copies the
context per task) — with no pipeline signature churn.

Everything here is BEST-EFFORT: :func:`record` swallows every error (no ``.usage()``, a
fake result, an absent collector) to a ``log.debug``, so a run produces the same result
whether or not telemetry succeeds. This is the one thing observability must never do —
break the thing it observes.

ContextVar is per-task-tree: each ``run_pipeline`` call installs its own log via
:func:`start_run` in its own context, so two pipelines in one process never cross-attribute.
"""

from __future__ import annotations

import contextvars
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel

log = logging.getLogger(__name__)


class RoleUsage(BaseModel):
    """Per-role token counts (a serializable view of ``RunUsage`` for the revision log).

    ``input_tokens`` is the UNCACHED prompt remainder; the full prompt is
    ``input_tokens + cache_read_tokens + cache_write_tokens``. Audio fields are ignored.
    """

    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def incr(self, other: "RoleUsage") -> None:
        self.requests += other.requests
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_write_tokens += other.cache_write_tokens

    @property
    def total_tokens(self) -> int:
        return (self.input_tokens + self.output_tokens
                + self.cache_read_tokens + self.cache_write_tokens)


def _from_run_usage(usage) -> RoleUsage:
    """Map a PydanticAI ``RunUsage`` → ``RoleUsage``. Isolated so a field rename upstream
    breaks a unit test (which constructs a real ``RunUsage``), not a run."""
    return RoleUsage(
        requests=int(getattr(usage, "requests", 0) or 0),
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        cache_read_tokens=int(getattr(usage, "cache_read_tokens", 0) or 0),
        cache_write_tokens=int(getattr(usage, "cache_write_tokens", 0) or 0),
    )


@dataclass
class UsageLog:
    """A run-scoped accumulator: whole-run totals + a per-record delta window.

    ``record`` adds to BOTH the totals and the delta window; :meth:`drain_delta` empties
    the window (not the totals) so each revision-log record carries exactly the tokens
    spent producing it, while :meth:`snapshot` gives the whole-run per-role totals.
    """

    totals: dict[str, RoleUsage] = field(default_factory=dict)
    _delta: dict[str, RoleUsage] = field(default_factory=dict)

    def add(self, role: str, usage: RoleUsage) -> None:
        self.totals.setdefault(role, RoleUsage()).incr(usage)
        self._delta.setdefault(role, RoleUsage()).incr(usage)

    def drain_delta(self) -> dict[str, RoleUsage]:
        """Return the tokens spent since the previous drain and reset the window."""
        d = {k: v for k, v in self._delta.items() if v.total_tokens or v.requests}
        self._delta = {}
        return d

    def snapshot(self) -> dict[str, RoleUsage]:
        """Whole-run per-role totals (a deep copy — callers must not mutate the live log)."""
        return {k: v.model_copy() for k, v in self.totals.items()}


_current: contextvars.ContextVar[UsageLog | None] = contextvars.ContextVar(
    "xlo_usage_log", default=None)


def start_run() -> UsageLog:
    """Install a fresh run-scoped :class:`UsageLog` and return it. Call once at the top of
    ``run_pipeline``/``regen_section``."""
    ul = UsageLog()
    _current.set(ul)
    return ul


def current() -> UsageLog | None:
    """The active run-scoped log, or ``None`` when none is installed."""
    return _current.get()


def record(role: str, result) -> None:
    """Capture the agent result's usage into the active log under ``role``. Best-effort: a
    result without a usage view, an absent collector, or any error is a defined no-op.

    PydanticAI exposes usage as ``AgentRunResult.usage`` — a property returning ``RunUsage`` in
    2.x, a ``.usage()`` method in some 1.x lines — so we accept either shape."""
    try:
        ul = _current.get()
        if ul is None:
            return
        usage = getattr(result, "usage", None)
        if usage is None:
            return
        # 2.x: `result.usage` is already a RunUsage (property). 1.x: a method returning one.
        # Only call it when the value isn't already token-bearing — calling the 2.x property
        # value hits a deprecated compat shim that emits a PydanticAIDeprecationWarning.
        if callable(usage) and not (hasattr(usage, "input_tokens") or hasattr(usage, "output_tokens")):
            usage = usage()
        # duck-type: only capture something that looks like a RunUsage (has token fields)
        if not hasattr(usage, "input_tokens") and not hasattr(usage, "output_tokens"):
            return
        ul.add(role, _from_run_usage(usage))
    except Exception as exc:  # noqa: BLE001 — telemetry never breaks a run
        log.debug("usage capture failed for role %s: %s", role, exc)
