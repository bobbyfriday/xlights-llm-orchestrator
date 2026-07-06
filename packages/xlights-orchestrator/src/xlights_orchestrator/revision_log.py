"""Revision log — a flight-recorder of the refine loop, for tuning prompts with real data.

Two co-written views of the SAME record: `revision_log.jsonl` (canonical/programmatic) and
`revision_log.md` (human narrative — read why each change happened). Pure observability:
logging never reads back into or changes a refine decision.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

log = logging.getLogger(__name__)


class LogFinding(BaseModel):
    source: str                 # sync | placement | variety | visual (derived from metric)
    severity: str
    scope: str
    section_index: int | None = None
    detail: str


class LogRevision(BaseModel):
    section_index: int
    issue: str
    origin: Literal["judge", "backstop"]


class RevisionLogRecord(BaseModel):
    run_id: str
    iteration: int
    song_key: str
    ts: str
    kind: Literal["iteration", "finalize"] = "iteration"
    objective_score: int
    advisory_score: int
    findings: list[LogFinding] = []
    judge: dict | None = None                 # {"score": int, "verdict": str}
    revisions: list[LogRevision] = []
    regenerated_sections: list[int] = []
    obj_before: int | None = None
    obj_after: int | None = None
    obj_delta: int | None = None
    reverted: bool = False
    human_decision: str | None = None
    models: dict[str, str] = {}
    review_bundle: str | None = None


def source_of(metric: str) -> str:
    """`visual:coverage` -> `visual`; `sync`/`placement`/`variety` unchanged."""
    return metric.split(":", 1)[0] if ":" in metric else metric


def _render_md(r: RevisionLogRecord) -> str:
    """Pure record -> Markdown (human view). Mirrors the JSONL record exactly."""
    if r.kind == "finalize":
        return (f"\n### Run {r.run_id} · finalize\n"
                f"**Final:** objective {r.objective_score} · advisory {r.advisory_score} "
                f"after {r.iteration} iteration(s).\n")
    lines = [f"\n## Run {r.run_id} · iteration {r.iteration} · {r.ts}\n"]
    delta = f" ({r.obj_delta:+d})" if r.obj_delta is not None else ""
    kept = "reverted" if r.reverted else "kept"
    if r.obj_before is not None:
        lines.append(f"**Scores:** objective {r.obj_before} → {r.obj_after}{delta}, {kept} "
                     f"· advisory {r.advisory_score}\n")
    else:
        lines.append(f"**Scores:** objective {r.objective_score} · advisory {r.advisory_score}\n")
    if r.findings:
        lines.append("**Flagged:**\n")
        for f in r.findings:
            where = f"section {f.section_index}" if f.section_index is not None else f.scope
            lines.append(f"- [{f.severity} · {f.source}] {where} — {f.detail}\n")
    if r.judge:
        lines.append(f"**Judge ({r.judge.get('score')}, {r.judge.get('verdict')}):**\n")
    for rev in r.revisions:
        lines.append(f"- section {rev.section_index} ({rev.origin}) — {rev.issue}\n")
    if r.regenerated_sections:
        lines.append(f"**Regenerated:** {', '.join(map(str, r.regenerated_sections))}"
                     f"  →  objective{delta} ({kept})\n")
    tail = []
    if r.human_decision:
        tail.append(f"**Human:** {r.human_decision}")
    if r.review_bundle:
        tail.append(f"**Frames:** {r.review_bundle}")
    if r.models:
        tail.append("**Models:** " + ", ".join(f"{k}={v}" for k, v in r.models.items()))
    if tail:
        lines.append(" · ".join(tail) + "\n")
    return "".join(lines)


class RevisionLog:
    """File-backed writer — appends the canonical JSONL and the human Markdown view."""

    def __init__(self, jsonl_path: str | Path, md_path: str | Path) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.md_path = Path(md_path)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self.md_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: RevisionLogRecord) -> None:
        try:
            with open(self.jsonl_path, "a") as f:           # canonical
                f.write(record.model_dump_json() + "\n")
            with open(self.md_path, "a") as f:              # human view
                f.write(_render_md(record))
        except Exception as exc:  # noqa: BLE001 — logging is best-effort, never breaks a run
            log.warning("revision log write failed: %s", exc)


class NullRevisionLog:
    """No-op writer (tests, --no-log)."""

    def write(self, record: RevisionLogRecord) -> None:
        return None
