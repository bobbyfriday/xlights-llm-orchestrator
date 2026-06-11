"""Judge agent: QA findings + plan/brief -> score + scoped revisions + verdict.

The Judge owns *quality* judgment; the deterministic objective score only guards
regressions, and the human has the final say at the checkpoint.
"""

from __future__ import annotations

import json

from ..models import build_agent
from .guide import with_guide
from ..refine import JudgeVerdict

_PROMPT = (
    "You are the Judge of a generated light show. You are given QA findings — objective"
    " (timing/placement), advisory (variety/coverage), and music-aware VISUAL findings"
    " (metric `visual:*`, from a model that watched the rendered stills+clips against the music) —"
    " plus the show plan and a 'do-not-repeat' ledger. Score 0-100, decide accept / iterate / stop,"
    " and if iterating return a SMALL set of scoped RevisionBriefs (each: section_index, groups,"
    " issue, concrete suggested_fix, do_not_repeat). Treat the visual findings as first-class"
    " judgment: a visual finding of severity=error (a real defect IN MUSICAL CONTEXT — e.g. dark"
    " mid-energy, repetitive, energy-mismatched) SHOULD become a scoped revision for that"
    " section_index, carrying the visual issue into suggested_fix (brighter/fuller/more dynamic to"
    " fit the music). Use judgment on advisory/visual-warn findings. Prioritize real errors; do NOT"
    " re-flag the ledger; prefer fewer, high-value revisions."
)


def judge_agent():
    return build_agent("judge", output_type=JudgeVerdict, system_prompt=with_guide(_PROMPT))


def render_input(report, plan, brief, ledger) -> str:
    return (
        "QA REPORT:\n" + report.model_dump_json(indent=1)
        + "\n\nSHOW PLAN (sections):\n"
        + json.dumps([{"i": i, "label_groups": s.target_groups, "family": s.effect_family,
                       "intensity": s.intensity} for i, s in enumerate(plan.sections)])
        + "\n\nDO-NOT-REPEAT LEDGER:\n"
        + json.dumps([r.model_dump() for r in ledger], default=str)
        + "\n\nReturn your verdict."
    )
