"""Variety/coverage QA (advisory): monotony + group coverage. Informs, never gates."""

from __future__ import annotations

from collections import Counter

from ..refine import Finding

DOMINANCE = 0.7   # one effect type covering >70% of effects reads as monotone
COVERAGE = 0.3    # using <30% of groups reads as thin


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

    used = {ins.target for ins in instructions}
    if groups:
        ratio = len(used) / len(groups)
        if ratio < COVERAGE:
            findings.append(Finding(scope="global", severity="info", metric="coverage", objective=False,
                                    detail=f"only {len(used)}/{len(groups)} groups used"))
            score -= 20

    return max(0, score), findings
