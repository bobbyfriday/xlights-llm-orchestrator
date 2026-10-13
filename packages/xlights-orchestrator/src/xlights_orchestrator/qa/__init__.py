"""Deterministic QA — objective guardrails (sync, placement, rendered coverage) + advisory
(variety).

Pure functions, no xLights, no LLM. `xlo qa` writes the report as qa.json; nothing gates on
it — the findings are proposals for brief edits. Coverage needs rendered eyes (the `.fseq`
series, or a frame `sampler`); without one it stays neutral and the objective is the
sync+placement+rules mean.
"""

from __future__ import annotations

import json
from pathlib import Path

from .findings import Finding, QAReport
from . import coverage, fseq_metrics, musicality, placement, rules, sync, variety, visual


def evaluate(instructions, analysis, plan, applied, groups, *, sampler=None,
             repetition_map=None, fseq_series=None, manifest=None) -> QAReport:
    s_sync, f_sync = sync.evaluate(instructions, analysis)
    s_place, f_place = placement.evaluate(plan, applied)
    s_var, f_var = variety.evaluate(instructions, groups)
    s_rules, f_rules = rules.evaluate(instructions, plan, manifest)
    # advisory musicality: repetition-rhyme + dynamic-range + focus-budget (objective=False —
    # informs the reviewer, never counts toward the objective score).
    s_mus, f_mus = musicality.evaluate(instructions, plan, repetition_map)
    subscores: dict[str, float] = {"sync": s_sync, "placement": s_place, "rules": s_rules,
                                   "variety": s_var, "musicality": s_mus}
    findings = f_sync + f_place + f_rules + f_var + f_mus
    parts = [s_sync, s_place, s_rules]
    # Rendered coverage: when the full render-data series is available it strictly dominates the
    # 3-point sampler, so it supersedes it for coverage (Decision 6 / show-refinement spec).
    if fseq_series is not None:
        fseq_sub, fseq_find = fseq_metrics.evaluate(plan, analysis, fseq_series,
                                                    repetition_map=_repetition_map(plan))
        subscores.update(fseq_sub)               # fseq:* subscores are recorded...
        findings += fseq_find                    # ...and their findings inform the human (advisory-first)
        if "fseq:coverage" in fseq_sub:          # rendered-series coverage replaces the sampler's
            subscores["coverage"] = fseq_sub["fseq:coverage"]
        elif sampler is not None:
            s_cov, f_cov = coverage.evaluate(plan, sampler)
            subscores["coverage"] = s_cov
            findings += f_cov
        # advisory visual judgments (dark mid-energy / static section) — findings only, no score
        findings += visual.evaluate(plan, fseq_series,
                                    repetition_map=repetition_map or _repetition_map(plan))
    elif sampler is not None:                    # rendered eyes available → coverage gates too
        s_cov, f_cov = coverage.evaluate(plan, sampler)
        subscores["coverage"] = s_cov
        findings += f_cov
        parts.append(s_cov)
    objective = round(sum(parts) / len(parts))
    # advisory score blends variety + musicality (both non-gating) so the reviewer sees one number
    advisory = round((s_var + s_mus) / 2)
    return QAReport(
        objective_score=objective,
        advisory_score=advisory,
        findings=findings,
        subscores=subscores,
    )


def write_qa(song_dir, report: QAReport) -> Path:
    """Write ``qa.json`` under the song's cache dir: the ``QAReport`` dump plus a top-level
    ``summary`` of finding counts per severity (``info``/``warn``/``error``, and ``total``).

    Findings are dumped individually so subclass fields (``visual.VisualFinding.fix``) survive —
    ``QAReport.findings`` is typed ``list[Finding]`` and a model dump would narrow to the base."""
    song_dir = Path(song_dir)
    song_dir.mkdir(parents=True, exist_ok=True)
    data = report.model_dump()
    data["findings"] = [f.model_dump() for f in report.findings]
    summary = {"info": 0, "warn": 0, "error": 0}
    for f in report.findings:
        summary[f.severity] = summary.get(f.severity, 0) + 1
    summary["total"] = len(report.findings)
    data["summary"] = summary
    path = song_dir / "qa.json"
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return path


def _repetition_map(plan):
    """Best-effort repetition_map (label -> section indices) from the plan/brief, for rhyme."""
    rm = getattr(plan, "repetition_map", None)
    return rm if isinstance(rm, dict) else None


__all__ = ["Finding", "QAReport", "evaluate", "write_qa", "coverage", "fseq_metrics", "musicality", "rules", "sync",
           "variety", "placement", "visual"]
