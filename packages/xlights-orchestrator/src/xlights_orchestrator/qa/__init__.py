"""Deterministic QA — objective guardrails (sync, placement, rendered coverage) + advisory
(variety).

Pure functions, no xLights, no LLM. Only `objective_score` drives the refine loop's
revert/stall gate; `advisory_score` + all findings inform the Judge and the human. Coverage
needs rendered eyes (a frame `sampler`); without one it stays neutral and the objective is
exactly the legacy sync+placement mean.
"""

from __future__ import annotations

from ..refine import QAReport
from . import coverage, placement, rules, sync, variety


def evaluate(instructions, analysis, plan, applied, groups, *, sampler=None) -> QAReport:
    s_sync, f_sync = sync.evaluate(instructions, analysis)
    s_place, f_place = placement.evaluate(plan, applied)
    s_var, f_var = variety.evaluate(instructions, groups)
    s_rules, f_rules = rules.evaluate(instructions, plan)
    subscores = {"sync": s_sync, "placement": s_place, "rules": s_rules, "variety": s_var}
    findings = f_sync + f_place + f_rules + f_var
    parts = [s_sync, s_place, s_rules]
    if sampler is not None:                  # rendered eyes available → coverage gates too
        s_cov, f_cov = coverage.evaluate(plan, sampler)
        subscores["coverage"] = s_cov
        findings += f_cov
        parts.append(s_cov)
    objective = round(sum(parts) / len(parts))
    return QAReport(
        objective_score=objective,
        advisory_score=s_var,
        findings=findings,
        subscores=subscores,
    )


__all__ = ["evaluate", "coverage", "rules", "sync", "variety", "placement"]
