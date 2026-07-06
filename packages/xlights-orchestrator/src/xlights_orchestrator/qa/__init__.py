"""Deterministic QA — objective guardrails (sync, placement, rendered coverage) + advisory
(variety).

Pure functions, no xLights, no LLM. Only `objective_score` drives the refine loop's
revert/stall gate; `advisory_score` + all findings inform the Judge and the human. Coverage
needs rendered eyes (a frame `sampler`); without one it stays neutral and the objective is
exactly the legacy sync+placement mean.
"""

from __future__ import annotations

from ..refine import QAReport
from . import coverage, musicality, placement, rules, sync, variety


def evaluate(instructions, analysis, plan, applied, groups, *, sampler=None,
             repetition_map=None) -> QAReport:
    s_sync, f_sync = sync.evaluate(instructions, analysis)
    s_place, f_place = placement.evaluate(plan, applied)
    s_var, f_var = variety.evaluate(instructions, groups)
    s_rules, f_rules = rules.evaluate(instructions, plan)
    # advisory musicality: repetition-rhyme + dynamic-range + focus-budget (objective=False —
    # informs the Judge/revision log, never gates the objective score or the loop's convergence).
    s_mus, f_mus = musicality.evaluate(instructions, plan, repetition_map)
    subscores = {"sync": s_sync, "placement": s_place, "rules": s_rules, "variety": s_var,
                 "musicality": s_mus}
    findings = f_sync + f_place + f_rules + f_var + f_mus
    parts = [s_sync, s_place, s_rules]
    if sampler is not None:                  # rendered eyes available → coverage gates too
        s_cov, f_cov = coverage.evaluate(plan, sampler)
        subscores["coverage"] = s_cov
        findings += f_cov
        parts.append(s_cov)
    objective = round(sum(parts) / len(parts))
    # advisory score blends variety + musicality (both non-gating) so the Judge sees one number
    advisory = round((s_var + s_mus) / 2)
    return QAReport(
        objective_score=objective,
        advisory_score=advisory,
        findings=findings,
        subscores=subscores,
    )


__all__ = ["evaluate", "coverage", "musicality", "rules", "sync", "variety", "placement"]
