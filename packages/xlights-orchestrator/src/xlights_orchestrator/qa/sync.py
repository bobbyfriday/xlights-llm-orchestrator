"""Sync QA (objective): how well effect starts land on the beat grid."""

from __future__ import annotations

from ..refine import Finding

SYNC_TOLERANCE_MS = 60   # ~1-2 frames at 20-50fps; explicit + tunable


def evaluate(instructions, analysis) -> tuple[int, list[Finding]]:
    beats_ms = [b.time * 1000 for b in analysis.beats]
    if not beats_ms or not instructions:
        return 100, []   # no beat reference (or nothing to score) → neutral, don't gate

    findings: list[Finding] = []
    on = 0
    for ins in instructions:
        dist = min(abs(ins.start_ms - bt) for bt in beats_ms)
        if dist <= SYNC_TOLERANCE_MS:
            on += 1
        else:
            findings.append(Finding(
                scope=f"section {ins.section_index} / {ins.target}",
                severity="warn", metric="sync", objective=True,
                detail=f"start {ins.start_ms}ms is {dist:.0f}ms off the nearest beat"))
    score = round(100 * on / len(instructions))
    return score, findings
