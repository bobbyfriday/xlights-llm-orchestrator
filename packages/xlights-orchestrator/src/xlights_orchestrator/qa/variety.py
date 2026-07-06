"""Variety/coverage QA (advisory): monotony + group coverage. Informs, never gates."""

from __future__ import annotations

from collections import Counter

from ..refine import Finding

DOMINANCE = 0.7      # one effect type covering >70% of effects reads as monotone
COVERAGE = 0.3       # using <30% of groups reads as thin
MIN_DISTINCT_TYPES = 4   # a whole show fielding fewer than this many effect types reads as samey


def evaluate(instructions, groups) -> tuple[int, list[Finding]]:
    if not instructions:
        return 100, []
    findings: list[Finding] = []
    score = 100

    counts = Counter(ins.effect_type for ins in instructions)
    top_type, top_n = counts.most_common(1)[0]
    if top_n > DOMINANCE * len(instructions):
        findings.append(Finding(scope="global", severity="warn", metric="variety", objective=False,
                                detail=f"effect '{top_type}' dominates ({top_n}/{len(instructions)})"))
        score -= 30

    # Reward breadth: too few DISTINCT effect types across the show reads as monotone even when
    # no single type dominates. Graduated so the Judge sees how far short it falls.
    distinct = len(counts)
    if distinct < MIN_DISTINCT_TYPES:
        findings.append(Finding(
            scope="global", severity="warn", metric="variety", objective=False,
            detail=f"only {distinct} distinct effect types (aim ≥{MIN_DISTINCT_TYPES}) — "
                   "give some sections different effect_types/weave carriers"))
        score -= 10 * (MIN_DISTINCT_TYPES - distinct)

    used = {ins.target for ins in instructions}
    if groups:
        ratio = len(used) / len(groups)
        if ratio < COVERAGE:
            # "group-coverage", not "coverage" — the latter is the objective rendered-coverage
            # metric (qa/coverage.py) and the two were indistinguishable in the revision log
            findings.append(Finding(scope="global", severity="info", metric="group-coverage",
                                    objective=False,
                                    detail=f"only {len(used)}/{len(groups)} groups used"))
            score -= 20

    return max(0, score), findings
