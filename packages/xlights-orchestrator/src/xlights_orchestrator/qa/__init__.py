"""Deterministic QA — objective guardrails (sync, placement, rendered coverage) + advisory
(variety).

Pure functions, no xLights, no LLM. Only `objective_score` drives the refine loop's
revert/stall gate; `advisory_score` + all findings inform the Judge and the human. Coverage
needs rendered eyes (a frame `sampler`); without one it stays neutral and the objective is
exactly the legacy sync+placement mean.
"""

from __future__ import annotations

from ..refine import QAReport
from . import coverage, fseq_metrics, placement, rules, sync, variety


def evaluate(instructions, analysis, plan, applied, groups, *, sampler=None,
             fseq_series=None) -> QAReport:
    s_sync, f_sync = sync.evaluate(instructions, analysis)
    s_place, f_place = placement.evaluate(plan, applied)
    s_var, f_var = variety.evaluate(instructions, groups)
    s_rules, f_rules = rules.evaluate(instructions, plan)
    subscores = {"sync": s_sync, "placement": s_place, "rules": s_rules, "variety": s_var}
    findings = f_sync + f_place + f_rules + f_var
    parts = [s_sync, s_place, s_rules]
    # Rendered coverage: when the full render-data series is available it strictly dominates the
    # 3-point sampler, so it supersedes it for coverage (Decision 6 / show-refinement spec).
    if fseq_series is not None:
        fseq_sub, fseq_find = fseq_metrics.evaluate(plan, analysis, fseq_series,
                                                    repetition_map=_repetition_map(plan))
        subscores.update(fseq_sub)               # fseq:* subscores are recorded...
        findings += fseq_find                    # ...and their findings inform Judge/human (advisory-first)
        if "fseq:coverage" in fseq_sub:          # rendered-series coverage replaces the sampler's
            subscores["coverage"] = fseq_sub["fseq:coverage"]
        elif sampler is not None:
            s_cov, f_cov = coverage.evaluate(plan, sampler)
            subscores["coverage"] = s_cov
            findings += f_cov
    elif sampler is not None:                    # rendered eyes available → coverage gates too
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


def _repetition_map(plan):
    """Best-effort repetition_map (label -> section indices) from the plan/brief, for rhyme."""
    rm = getattr(plan, "repetition_map", None)
    return rm if isinstance(rm, dict) else None


__all__ = ["evaluate", "coverage", "fseq_metrics", "rules", "sync", "variety", "placement"]
