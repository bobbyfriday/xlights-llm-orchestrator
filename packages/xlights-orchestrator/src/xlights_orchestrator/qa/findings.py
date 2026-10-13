"""The QA contracts: one `Finding` per issue and the `QAReport` that `xlo qa` writes as qa.json."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Finding(BaseModel):
    scope: str                              # "section 2 / G1" or "global"
    severity: Literal["info", "warn", "error"] = "warn"
    metric: str                             # sync | placement | variety | visual:* | fseq:*
    detail: str
    objective: bool = True                  # objective counts toward objective_score; advisory informs
    section_index: int | None = None        # set for section-scoped findings — robust targeting


class QAReport(BaseModel):
    objective_score: int                    # 0-100 (sync + placement + rules [+ coverage])
    advisory_score: int                     # 0-100 (variety + musicality) — informs only
    findings: list[Finding] = []
    subscores: dict[str, float] = {}
