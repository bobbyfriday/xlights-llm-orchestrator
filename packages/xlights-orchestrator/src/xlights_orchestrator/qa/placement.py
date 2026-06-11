"""Placement QA (objective): did effects survive, per section (from the emitter report)."""

from __future__ import annotations

from ..refine import Finding


def evaluate(plan, applied) -> tuple[int, list[Finding]]:
    n = len(plan.sections)
    if n == 0:
        return 100, []
    placed_by: dict = {}
    skipped_by: dict = {}
    for p in applied.get("placed", []):
        placed_by[p.get("section_index")] = placed_by.get(p.get("section_index"), 0) + 1
    for s in applied.get("skipped", []):
        skipped_by[s.get("section_index")] = skipped_by.get(s.get("section_index"), 0) + 1

    findings: list[Finding] = []
    nonempty = 0
    for i in range(n):
        pc = placed_by.get(i, 0)
        sk = skipped_by.get(i, 0)
        if pc == 0:
            findings.append(Finding(scope=f"section {i}", severity="error", metric="placement",
                                    objective=True, detail="no effects survived in this section"))
        else:
            nonempty += 1
            if sk > pc:
                findings.append(Finding(scope=f"section {i}", severity="warn", metric="placement",
                                        objective=True, detail=f"{sk} skipped vs {pc} placed"))
    score = round(100 * nonempty / n)
    return score, findings
