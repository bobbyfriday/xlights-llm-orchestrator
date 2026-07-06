"""One shared, stdlib-only async retry primitive with bounded exponential backoff.

Both the xLights transport boundary and the LLM seam reuse ``with_retry``. It lives in
``xlights-core`` (the bottom of the dependency graph) so the orchestrator can import it for
LLM calls without a cycle. No third-party dependency (deliberately not ``tenacity``): the
callable-wrapping shape keeps the retry visible at the seam and never wraps an injected fake
invisibly — a fake that never raises a retryable exception is called exactly once, so the
hermetic suite sees identical behavior.

Retryability is a **caller-supplied predicate**, never a blanket "5xx ⇒ retry": xLights
overloads 5xx for non-transient semantic states, and LLM schema/auth failures repeat
identically at full token cost. The two predicates live next to their taxonomies —
``xlights_transient`` here, ``llm_transient`` in the orchestrator (owner of the pydantic_ai
dependency).
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar

from .exceptions import XLightsConnectionError, XLightsTimeout

log = logging.getLogger(__name__)

T = TypeVar("T")


def xlights_transient(exc: BaseException) -> bool:
    """The xLights transport predicate: connection failures and timeouts self-heal.

    Deliberately does NOT match ``XLightsNotImplemented``/``XLightsTargetMissing``/
    ``XLightsUnsavedChanges``/generic ``XLightsResponseError`` — those 5xx codes carry
    semantic state, not a transient transport blip.
    """
    return isinstance(exc, (XLightsConnectionError, XLightsTimeout))


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    retryable: Callable[[BaseException], bool],
    attempts: int = 3,
    base_delay: float = 1.0,
    factor: float = 2.0,
    max_delay: float = 20.0,
    jitter: float = 0.5,
    label: str = "",
) -> T:
    """Run ``fn()``; on a retryable exception, back off and re-run up to ``attempts`` times.

    Backoff is exponential (``base_delay * factor**n``) capped at ``max_delay``, with a full
    ±``jitter`` band applied multiplicatively so concurrently-launched callers (e.g. the three
    panel analysts) do not re-collide on the same rate-limit window. A non-retryable exception,
    and the final failure after the last attempt, propagate **unchanged** so every existing
    ``except``/``isinstance`` path still works. Each retry logs a WARNING naming the label,
    attempt count, and cause. ``attempts <= 1`` disables retry (one call).
    """
    last: BaseException | None = None
    for attempt in range(max(1, attempts)):
        try:
            return await fn()
        except BaseException as exc:  # noqa: BLE001 — re-raised below unless retryable
            last = exc
            if attempt + 1 >= max(1, attempts) or not retryable(exc):
                raise
            delay = min(max_delay, base_delay * (factor ** attempt))
            if jitter:
                delay *= 1.0 + random.uniform(-jitter, jitter)
            delay = max(0.0, delay)
            log.warning("retry %s: attempt %d/%d failed (%s); backing off %.2fs",
                        label or "call", attempt + 1, attempts, exc, delay)
            await asyncio.sleep(delay)
    # Unreachable (the loop either returns or re-raises), but keep the type-checker happy.
    assert last is not None
    raise last
