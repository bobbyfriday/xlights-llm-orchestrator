"""Per-run degradations collector — turn "the show looks off" into "stems failed, brief had
no instruments".

The pipeline's best-effort posture (lyrics, stems, the visual critic, the real render, timing
tracks, caching are enrichments) is correct, but a lost capability used to scatter across
debug/info/warning with no rule and nothing aggregated at the end. This module is the aggregation:
a run-scoped, best-effort collector keyed by a **closed capability taxonomy**, an end-of-run
summary, and a machine-readable ``degradations.json`` written beside ``revision_log.jsonl``.

Contract (mirrors ``RevisionLog.write``): observability must NEVER break a run. ``note()`` is
wrapped in its own guard, is a safe no-op when there's no active run, and dedupes repeated losses
of the same capability into one entry with a count. The collector is a ``ContextVar`` so two
sequential runs in one process (tests, ``regen``) don't bleed into each other.

Capability keys are a FIXED, documented set (free-form keys would defeat dashboard aggregation):

    audio:lyrics                lyric fetch/attach failed → no timed lines
    audio:stems                 all stem-separation backends failed → no per-section instruments
    audio:instrumental-refine   instrumental section subdivision failed
    groups:probe                targetability probe failed → using the full group list
    emit:view                   the SEM Master render-order view wasn't loaded → default view
    qa:coverage-blind           coverage sampling failed → the objective can't see darkness
    qa:render-flush             the pre-QA .fseq save/real-render refresh failed
    visual:critique             the multimodal visual critic couldn't run this iteration
    visual:real-render          the real xLights render/export was unavailable
    visual:fseq-metrics         (reserved) deterministic Tier-0 fseq-metrics skipped
    refine:redesign             a section redesign escalation failed
    refine:analyst-drop         a panel analyst was dropped after its retry
    generate:triggers           one or more trigger detectors failed
    finalize:media              the show folder / media staging was unavailable
    finalize:timing-tracks      reference timing tracks couldn't be patched into the .xsq
    finalize:xsq-patch          the offline .xsq patch step failed
    cache:post-refine           persisting the revised brief/instructions failed
"""

from __future__ import annotations

import contextvars
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

# Closed taxonomy — a typo here is a phantom capability, so keep these as the single source.
CAPABILITIES = frozenset({
    "audio:lyrics", "audio:stems", "audio:instrumental-refine",
    "groups:probe", "emit:view", "qa:coverage-blind", "qa:render-flush",
    "visual:critique", "visual:real-render", "visual:fseq-metrics",
    "refine:redesign", "refine:analyst-drop", "generate:triggers",
    "finalize:media", "finalize:timing-tracks", "finalize:xsq-patch",
    "cache:post-refine",
})


@dataclass
class Degradation:
    """One lost capability. ``count`` accrues on repeated notes; ``detail``/``stage`` keep the
    first occurrence (the root cause; later ones are usually the same)."""
    capability: str
    detail: str
    count: int = 1
    stage: str | None = None


@dataclass
class DegradationLog:
    """A run's degradations, deduplicated by capability key."""
    items: dict[str, Degradation] = field(default_factory=dict)

    def note(self, capability: str, detail: str, *, stage: str | None = None) -> None:
        entry = self.items.get(capability)
        if entry is None:
            self.items[capability] = Degradation(capability, detail, count=1, stage=stage)
        else:
            entry.count += 1                 # keep the first detail/stage — the root cause

    def summary(self) -> list[Degradation]:
        return list(self.items.values())

    def as_json(self) -> list[dict]:
        return [{"capability": d.capability, "detail": d.detail, "count": d.count, "stage": d.stage}
                for d in self.summary()]


_current: contextvars.ContextVar[DegradationLog | None] = contextvars.ContextVar(
    "degradations_current", default=None)


def start_run() -> DegradationLog:
    """Install a fresh collector for the current run and return it. Call at each pipeline entry
    point (``run_pipeline``/``regen_section``); a later ``start_run()`` isolates the next run."""
    dl = DegradationLog()
    _current.set(dl)
    return dl


def current() -> DegradationLog | None:
    """The active collector, or ``None`` outside a run (``note`` becomes a logged no-op)."""
    return _current.get()


def note(capability: str, exc_or_detail: object, *, stage: str | None = None,
         level: int = logging.WARNING) -> None:
    """Log AND record a degradation in one call. Best-effort: any failure inside recording is
    swallowed to a DEBUG log so observability can never take a run down (mirrors
    ``RevisionLog.write``). Whole-capability losses default to WARNING so a plain ``grep -i
    warning`` over the run log is a complete degradation list even without the collector.

    A safe no-op (still logs) when there's no active run — call sites don't need a guard.
    """
    try:
        detail = str(exc_or_detail)
        log.log(level, "%s lost: %s", capability, detail)
        dl = _current.get()
        if dl is not None:
            dl.note(capability, detail, stage=stage)
    except Exception as exc:  # noqa: BLE001 — recording must never break a run
        log.debug("degradations.note failed for %r: %s", capability, exc)


def note_once(capability: str, exc_or_detail: object, *, stage: str | None = None,
              level: int = logging.WARNING) -> None:
    """Like ``note`` but logs (and records) only the FIRST occurrence per run — for a capability
    checked many times per run (e.g. the coverage sampler), so the WARNING isn't spammed. Repeat
    occurrences still bump the count on the existing entry (no log). A no-op outside a run apart
    from a single debug on the first call, to avoid unbounded logging.
    """
    try:
        dl = _current.get()
        if dl is not None and capability in dl.items:
            dl.items[capability].count += 1           # already reported this run — just count
            return
        note(capability, exc_or_detail, stage=stage, level=level)
    except Exception as exc:  # noqa: BLE001 — recording must never break a run
        log.debug("degradations.note_once failed for %r: %s", capability, exc)


def render_summary(dl: DegradationLog) -> str:
    """Pure list → text for the end-of-run summary block."""
    items = dl.summary()
    if not items:
        return "no degradations"
    width = max((len(d.capability) for d in items), default=0)
    lines = [f"== degradations ({len(items)}) " + "=" * 41]
    for d in items:
        where = f", {d.stage}" if d.stage else ""
        lines.append(f"  {d.capability.ljust(width)}  {d.detail} (×{d.count}{where})")
    lines.append("=" * 57)
    return "\n".join(lines)


def emit_summary(dl: DegradationLog) -> None:
    """Log the end-of-run summary: WARNING when non-empty (a degraded run ends loudly), INFO
    "no degradations" otherwise."""
    try:
        if dl.summary():
            log.warning("\n%s", render_summary(dl))
        else:
            log.info("no degradations")
    except Exception as exc:  # noqa: BLE001 — summary emission is best-effort
        log.debug("degradations summary emit failed: %s", exc)


def write_json(dl: DegradationLog, path: str | Path) -> None:
    """Best-effort write of ``degradations.json`` beside the revision log. A degraded run's
    machine-readable record; absent/empty for a clean run (callers may skip when empty)."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(dl.as_json(), indent=1))
    except Exception as exc:  # noqa: BLE001 — the artifact is best-effort
        log.debug("degradations.json write failed for %s: %s", path, exc)
