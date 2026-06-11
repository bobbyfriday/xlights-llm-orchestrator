"""Contracts + helpers for the test → judge → refine loop."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .show_plan import EffectInstruction


class Finding(BaseModel):
    scope: str                              # "section 2 / G1" or "global"
    severity: Literal["info", "warn", "error"] = "warn"
    metric: str                             # sync | placement | variety | visual:*
    detail: str
    objective: bool = True                  # objective gates the loop; advisory only informs
    section_index: int | None = None        # set for section-scoped findings (e.g. visual) — robust targeting


class QAReport(BaseModel):
    objective_score: int                    # 0-100 (sync + placement) — the only gate
    advisory_score: int                     # 0-100 (variety) — informs Judge/human only
    findings: list[Finding] = []
    subscores: dict[str, float] = {}


class RevisionBrief(BaseModel):
    section_index: int
    groups: list[str] = []
    issue: str
    suggested_fix: str
    do_not_repeat: str = ""


class JudgeVerdict(BaseModel):
    score: int
    verdict: Literal["accept", "iterate", "stop"]
    revisions: list[RevisionBrief] = []


class Decision(BaseModel):
    """A checkpoint outcome — human (attended) or auto."""
    action: Literal["approve", "redirect", "stop", "accept"]
    revisions: list[RevisionBrief] = []


def replace_section(
    instructions: list[EffectInstruction], section_index: int, new: list[EffectInstruction]
) -> list[EffectInstruction]:
    """Swap out one section's slice (by section_index tag), keeping all others intact."""
    for ins in new:
        ins.section_index = section_index
    return [x for x in instructions if x.section_index != section_index] + list(new)


def floor_visual_revisions(
    findings: list[Finding], existing: list[RevisionBrief]
) -> list[RevisionBrief]:
    """Backstop: a critic-confirmed visual ERROR (in musical context) the Judge didn't act on
    becomes a revision for that section. Triggers ONLY on `visual:*` severity=error with a known
    section_index — never on darkness per se (the critic's contextual judgment decides severity)."""
    covered = {r.section_index for r in existing}
    out: list[RevisionBrief] = []
    for f in findings:
        if not f.metric.startswith("visual:") or f.severity != "error" or f.section_index is None:
            continue
        if f.section_index in covered:
            continue
        covered.add(f.section_index)
        out.append(RevisionBrief(
            section_index=f.section_index, issue=f.detail,
            suggested_fix="visual defect for this musical moment — regenerate to fit the music here"))
    return out
