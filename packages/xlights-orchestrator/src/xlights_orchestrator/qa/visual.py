"""Advisory visual findings from the rendered `.fseq` per-group lit-coverage series (design D9).

The two judgments the multimodal critic used to contribute that are computable without a model:
- ``visual:dark``   — an energetic section (effective intensity ≥ ``ENERGETIC``) whose rendered
                      lit coverage sits below the coverage floor for most (> ``DARK_SPAN``) of its
                      span. Severity ``error``: the payoff the brief asked for isn't on the display.
- ``visual:static`` — an energetic section whose lit-coverage series barely varies over its span
                      (variance < ``STATIC_VARIANCE``). Severity ``warn``: a wash that never breathes.

Both are ADVISORY (``objective=False``), carry ``section_index`` and a plain-language ``fix`` so
Claude can propose a brief edit; nothing here gates any stage. No series → neutral (``[]``).

The coverage curve is the section's per-frame lit fraction averaged over the groups it targets
(``fseq_metrics._section_groups``), so a section is judged on the props it meant to light. The
floor is the same expectation ``fseq_metrics`` scores against: ``COVERAGE_FAIL × COVERAGE_EXPECT ×
intensity``. Sections whose treatment resolves to ``gesture``/``rest`` are deliberately sparse
(as in ``qa/coverage.py``) and are never flagged.
"""

from __future__ import annotations

import logging

import numpy as np

from ..refine import Finding
from .fseq_metrics import COVERAGE_EXPECT, COVERAGE_FAIL, _restrict, _section_groups

log = logging.getLogger(__name__)

ENERGETIC = 0.6                                 # normalized energy at/above which a section must show
DARK_SPAN = 0.6                                 # fraction of frames below the floor → "dark" (strictly more)
COVERAGE_FLOOR = COVERAGE_FAIL * COVERAGE_EXPECT   # per-frame lit-fraction floor, × intensity (0.25·i)
STATIC_VARIANCE = 1e-3                          # lit-fraction variance below which a section is "static"
MIN_FRAMES = 2                                  # shorter than this → nothing to judge
_EXEMPT_TREATMENTS = ("gesture", "rest")        # deliberately sparse — restraint, not a defect

DARK_FIX = ("brighter/fuller treatment: raise the section's intensity, switch its treatment to "
            "\"full\" or \"pulse\", or target broader groups (e.g. SEM_ALL / SEM_YARD)")
STATIC_FIX = ("add movement: give the section a moving carrier in `fabric` (e.g. SingleStrand or "
              "Spirals with pingpong alternation), set pulse_groups so the beat punctuates it, or "
              "switch its treatment from a plain wash to \"pulse\"")


class VisualFinding(Finding):
    """A ``Finding`` with a plain-language ``fix`` the human/Claude can apply to the brief."""
    fix: str = ""


def coverage_curve(series, sec) -> np.ndarray | None:
    """The section's per-frame lit fraction averaged over its target groups (all series groups
    when none of its targets are in the series). None when the series has nothing for it."""
    sl = _restrict(series.section_slice(sec.start_ms, sec.end_ms), _section_groups(series, sec))
    curves = [d["lit"] for d in sl.values() if d["lit"].size]
    if not curves:
        return None
    return np.mean(np.stack(curves), axis=0)


def section_energy(sec, index: int, repetition_map) -> float:
    """The section's normalized energy as realization sees it: the brief's intensity lifted by its
    escalation level (``pipeline.beats.effective_intensity``)."""
    from ..pipeline.beats import effective_intensity
    return effective_intensity(getattr(sec, "intensity", 0.0) or 0.0, index, repetition_map)


def evaluate(plan, series, *, repetition_map=None) -> list[Finding]:
    """``visual:dark`` / ``visual:static`` findings over the render series; ``[]`` without one."""
    if series is None or plan is None:
        return []
    sections = list(getattr(plan, "sections", None) or [])
    if not sections:
        return []
    try:
        from ..pipeline.beats import peak_sections, resolve_treatment
        peaks = peak_sections(plan)
        findings: list[Finding] = []
        for i, sec in enumerate(sections):
            energy = section_energy(sec, i, repetition_map)
            if energy < ENERGETIC:
                continue
            if resolve_treatment(sec, i in peaks, has_focal=True) in _EXEMPT_TREATMENTS:
                continue
            curve = coverage_curve(series, sec)
            if curve is None or curve.size < MIN_FRAMES:
                continue
            floor = COVERAGE_FLOOR * energy
            dark_frac = float((curve < floor).mean())
            if dark_frac > DARK_SPAN:
                findings.append(VisualFinding(
                    scope=f"section {i}", severity="error", metric="visual:dark", objective=False,
                    section_index=i, fix=DARK_FIX,
                    detail=(f"energetic section (energy {energy:.2f}) renders dark for {dark_frac:.0%} "
                            f"of its span — lit coverage under {floor:.0%} (mean {curve.mean():.0%})")))
                continue                                 # dark dominates; a dark section is trivially flat
            variance = float(curve.var())
            if variance < STATIC_VARIANCE:
                findings.append(VisualFinding(
                    scope=f"section {i}", severity="warn", metric="visual:static", objective=False,
                    section_index=i, fix=STATIC_FIX,
                    detail=(f"energetic section (energy {energy:.2f}) is static — lit coverage holds at "
                            f"{curve.mean():.0%} with variance {variance:.4f} (< {STATIC_VARIANCE})")))
        return findings
    except Exception as exc:  # noqa: BLE001 — advisory eyes; a metric bug must not break QA
        log.debug("visual findings skipped: %s", exc)
        return []
