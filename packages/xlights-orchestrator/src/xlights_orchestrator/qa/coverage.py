"""Coverage QA (objective): is the display actually LIT in high-energy sections?

Samples rendered frames from the `.fseq` via an injected `sampler(t_ms) -> lit_pixel_count`.
This is the metric that gates the dark-chorus failure mode the Judge kept describing while the
objective score looked fine. Quiet sections are exempt — restraint is intentional; only
high-energy darkness is a defect.
"""

from __future__ import annotations

from ..refine import Finding

MIN_INTENSITY = 0.5        # only sections at/above this are scored (below = intentional restraint)
EXPECTATION = 0.6          # a loud section should reach ~60% of the song's own peak, × intensity
FAIL_FRACTION = 0.5        # under half its expectation → error finding
_SAMPLES = (0.25, 0.5, 0.75)


def evaluate(plan, sampler) -> tuple[int, list[Finding]]:
    if sampler is None or plan is None:
        return 100, []                                  # no eyes → neutral, don't gate
    sections = list(getattr(plan, "sections", None) or [])
    if not sections:
        return 100, []

    lit: dict[int, int] = {}                            # section index -> max lit px across samples
    try:
        for i, sec in enumerate(sections):
            span = sec.end_ms - sec.start_ms
            lit[i] = max(int(sampler(int(sec.start_ms + span * f))) for f in _SAMPLES)
    except Exception:  # noqa: BLE001 — can't see (missing fseq/deps) → neutral, never gate blind
        return 100, []
    peak = max(lit.values())
    if peak <= 0:
        return 0, [Finding(scope="global", severity="error", metric="coverage", objective=True,
                           detail="the rendered show is entirely dark (no lit pixels sampled)")]

    findings: list[Finding] = []
    scores: list[float] = []
    for i, sec in enumerate(sections):
        intensity = getattr(sec, "intensity", 0.0) or 0.0
        if intensity < MIN_INTENSITY:
            continue
        frac = lit[i] / peak
        expected = EXPECTATION * intensity
        score = min(1.0, frac / expected) if expected > 0 else 1.0
        scores.append(score)
        if score < FAIL_FRACTION:
            findings.append(Finding(
                scope=f"section {i}", severity="error", metric="coverage", objective=True,
                section_index=i,
                detail=(f"high-energy section (intensity {intensity:.2f}) renders mostly dark — "
                        f"{frac:.0%} of the show's peak lit pixels (expected ≥{expected:.0%})")))
    if not scores:
        return 100, []                                  # nothing high-energy to judge
    return round(100 * sum(scores) / len(scores)), findings
