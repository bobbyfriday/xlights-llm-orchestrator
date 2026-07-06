"""Variety/coverage QA (advisory): monotony + group coverage. Informs, never gates."""

from __future__ import annotations

from collections import Counter

from ..pipeline.matrix_text import MATRIX_TEXT_MARKER
from ..pipeline.tuning import MAX_TEXT_MOMENTS
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

    # Over-captioning guard: narrative Text is outside rules.FEATURES/ENERGY_BAND (objectively
    # unconstrained), so this advisory is the belt-and-braces backstop against a future author
    # adding "just one more" text source past the cap. Advisory only — never gates the objective.
    text_moments = sum(1 for ins in instructions if ins.extra_settings.get(MATRIX_TEXT_MARKER) == "1")
    if text_moments > MAX_TEXT_MOMENTS:
        findings.append(Finding(
            scope="global", severity="warn", metric="matrix-text", objective=False,
            detail=f"{text_moments} matrix text moments exceed the cap of {MAX_TEXT_MOMENTS} "
                   "(text is punctuation, not captioning)"))
        score -= 10

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
