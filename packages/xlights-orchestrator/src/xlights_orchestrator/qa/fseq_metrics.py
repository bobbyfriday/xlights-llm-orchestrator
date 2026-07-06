"""Tier-0 deterministic rendered-pixel metrics (I8), from the compiled `.fseq` series.

Given a per-group brightness/lit/motion series (``xlights_core.preview.FseqSeries``, computed from
the exact channel data — not the projected preview), score each section on five families and emit
scoped ``Finding``s. This is the *free, deterministic eyes* that run every refine iteration before
any LLM critique.

Rollout is ADVISORY-FIRST (Decision 6): every finding ships ``objective=False`` until a calibration
pass (task 2.6) flips coverage/motion/sync to objective; color/rhyme stay advisory (taste-adjacent).
``XLO_FSEQ_METRICS=0`` disables the whole family. Unreadable inputs → ``({}, [])`` — never gate blind.

Thresholds (documented like ``qa/coverage.py``, calibrate on real runs before promoting to objective):
- COVERAGE: a section at intensity ≥ ``MIN_INTENSITY`` should light ≥ ``COVERAGE_EXPECT`` × intensity
  of its groups on average; below ``COVERAGE_FAIL`` × that → a finding.
- MOTION:   a rhythmic (intensity ≥ ``MOTION_MIN_INTENSITY``) section whose lit groups barely change
  frame-to-frame (normalized motion < ``MOTION_FLOOR``) reads as static → a finding.
- SYNC:     positive brightness-derivative should correlate with the beat grid; a lag-0 correlation
  below ``SYNC_FLOOR`` (vs a shift baseline) reads as unsynced → a finding.
- RHYME/RANGE: sections sharing a repetition label should look alike (cosine of their brightness
  signatures); the show's brightness spread (loudest vs quietest section) is the dynamic range.
"""

from __future__ import annotations

import logging
import os

import numpy as np

from ..refine import Finding

log = logging.getLogger(__name__)

MIN_INTENSITY = 0.5
COVERAGE_EXPECT = 0.5
COVERAGE_FAIL = 0.5
MOTION_MIN_INTENSITY = 0.6
MOTION_FLOOR = 2.0            # mean per-frame |Δbrightness| over lit groups, below which a section is "static"
SYNC_FLOOR = 0.15            # lag-0 beat correlation below this reads as unsynced
RHYME_FLOOR = 0.75           # cosine similarity below which two same-labeled sections don't "rhyme"


def _enabled() -> bool:
    return os.environ.get("XLO_FSEQ_METRICS", "1") != "0"


def _sections(plan):
    return list(getattr(plan, "sections", None) or [])


def _section_groups(series, sec) -> list[str] | None:
    """The section's own target groups that exist in the series (so coverage/motion judge the
    groups the section is supposed to light, not the whole show). None → judge all series groups."""
    tg = list(getattr(sec, "target_groups", None) or [])
    present = [g for g in tg if g in series.groups]
    return present or None


def _restrict(sl: dict, keep: list[str] | None) -> dict:
    return sl if keep is None else {g: d for g, d in sl.items() if g in keep}


def _coverage(series, sections) -> tuple[float | None, list[Finding]]:
    findings: list[Finding] = []
    scores: list[float] = []
    for i, sec in enumerate(sections):
        intensity = getattr(sec, "intensity", 0.0) or 0.0
        if intensity < MIN_INTENSITY:
            continue
        sl = _restrict(series.section_slice(sec.start_ms, sec.end_ms), _section_groups(series, sec))
        if not sl:
            continue
        lit_by_group = {g: float(d["lit"].mean()) for g, d in sl.items() if d["lit"].size}
        if not lit_by_group:
            continue
        avg_lit = float(np.mean(list(lit_by_group.values())))
        expected = COVERAGE_EXPECT * intensity
        score = min(1.0, avg_lit / expected) if expected > 0 else 1.0
        scores.append(score)
        if score < COVERAGE_FAIL:
            dark = sorted(lit_by_group, key=lambda g: lit_by_group[g])[:2]
            findings.append(Finding(
                scope=f"section {i}", severity="warn", metric="fseq:coverage", objective=False,
                section_index=i,
                detail=(f"high-energy section (intensity {intensity:.2f}) renders mostly dark — "
                        f"{avg_lit:.0%} lit on average (expected ≥{expected:.0%}); "
                        f"darkest groups: {', '.join(dark)}")))
    if not scores:
        return None, findings
    return round(100 * sum(scores) / len(scores)), findings


def _motion(series, sections) -> tuple[float | None, list[Finding]]:
    findings: list[Finding] = []
    scores: list[float] = []
    for i, sec in enumerate(sections):
        intensity = getattr(sec, "intensity", 0.0) or 0.0
        if intensity < MOTION_MIN_INTENSITY:
            continue
        sl = _restrict(series.section_slice(sec.start_ms, sec.end_ms), _section_groups(series, sec))
        # lit-weighted mean motion (only groups that are actually on contribute)
        vals = []
        for g, d in sl.items():
            lit = float(d["lit"].mean())
            if lit > 0.05 and d["motion"].size:
                vals.append(float(d["motion"].mean()))
        if not vals:
            continue
        mean_motion = float(np.mean(vals))
        scores.append(min(1.0, mean_motion / (MOTION_FLOOR * 2)))
        if mean_motion < MOTION_FLOOR:
            findings.append(Finding(
                scope=f"section {i}", severity="warn", metric="fseq:motion", objective=False,
                section_index=i,
                detail=(f"high-energy section (intensity {intensity:.2f}) is nearly static — "
                        f"mean frame-to-frame change {mean_motion:.1f} (expected ≥{MOTION_FLOOR})")))
    if not scores:
        return None, findings
    return round(100 * sum(scores) / len(scores)), findings


def _beat_impulses(analysis, series, n_frames: int) -> np.ndarray | None:
    beats = getattr(analysis, "beats", None) or []
    if not beats or n_frames <= 1:
        return None
    imp = np.zeros(n_frames, dtype=np.float32)
    step = series.step_ms
    for b in beats:
        t = getattr(b, "time", None)
        if t is None:
            continue
        fi = int(round(t * 1000 / step))
        if 0 <= fi < n_frames:
            imp[fi] = 1.0
    return imp if imp.any() else None


def _sync(series, sections, analysis) -> tuple[float | None, list[Finding]]:
    imp = _beat_impulses(analysis, series, series.frames)
    if imp is None:
        return None, []
    findings: list[Finding] = []
    scores: list[float] = []
    for i, sec in enumerate(sections):
        intensity = getattr(sec, "intensity", 0.0) or 0.0
        if intensity < MIN_INTENSITY:
            continue
        sl_frames = series._frame_slice(sec.start_ms, sec.end_ms)
        seg_imp = imp[sl_frames]
        if seg_imp.sum() < 2:
            continue
        # aggregate positive brightness derivative across lit groups
        agg = None
        for g, d in series.section_slice(sec.start_ms, sec.end_ms).items():
            b = d["brightness"]
            if b.size < 2:
                continue
            dpos = np.clip(np.diff(b, prepend=b[:1]), 0, None)
            agg = dpos if agg is None else agg + dpos
        if agg is None or agg.std() < 1e-6 or seg_imp.std() < 1e-6:
            continue
        corr = float(np.corrcoef(agg, seg_imp[:agg.size])[0, 1])
        corr = 0.0 if np.isnan(corr) else corr
        scores.append(max(0.0, min(1.0, (corr + 1) / 2)))
        if corr < SYNC_FLOOR:
            findings.append(Finding(
                scope=f"section {i}", severity="info", metric="fseq:sync", objective=False,
                section_index=i,
                detail=(f"brightness changes weakly track the beat (corr {corr:.2f} < {SYNC_FLOOR}) "
                        f"in a rhythmic section (intensity {intensity:.2f})")))
    if not scores:
        return None, findings
    return round(100 * sum(scores) / len(scores)), findings


def _section_signature(series, sec) -> np.ndarray | None:
    """A short brightness signature of a section (mean per-group brightness), for rhyme cosine."""
    sl = series.section_slice(sec.start_ms, sec.end_ms)
    if not sl:
        return None
    vec = np.array([float(d["brightness"].mean()) for d in sl.values()], dtype=np.float32)
    return vec if vec.size and np.linalg.norm(vec) > 1e-6 else None


def _rhyme_and_range(series, sections, repetition_map) -> tuple[dict, list[Finding]]:
    subscores: dict[str, float] = {}
    findings: list[Finding] = []
    sigs = {i: _section_signature(series, s) for i, s in enumerate(sections)}
    brights = [float(v.mean()) for v in sigs.values() if v is not None and v.size]
    # dynamic range: spread between the loudest and quietest section (0..100 of the max)
    if brights:
        lo, hi = min(brights), max(brights)
        subscores["fseq:range"] = round(100 * (hi - lo) / hi) if hi > 0 else 0

    # rhyme: sections sharing a repetition label should look alike
    if repetition_map:
        label_to_sections: dict[str, list[int]] = {}
        for label, members in repetition_map.items():
            for si in (members if isinstance(members, (list, tuple)) else [members]):
                if isinstance(si, int) and 0 <= si < len(sections):
                    label_to_sections.setdefault(label, []).append(si)
        sims: list[float] = []
        for label, members in label_to_sections.items():
            vecs = [sigs[m] for m in members if sigs.get(m) is not None]
            for a in range(len(vecs)):
                for b in range(a + 1, len(vecs)):
                    va, vb = vecs[a], vecs[b]
                    n = min(va.size, vb.size)
                    cos = float(np.dot(va[:n], vb[:n]) /
                                (np.linalg.norm(va[:n]) * np.linalg.norm(vb[:n]) + 1e-9))
                    sims.append(cos)
                    if cos < RHYME_FLOOR:
                        findings.append(Finding(
                            scope=f"label {label}", severity="info", metric="fseq:rhyme",
                            objective=False,
                            detail=(f"repeated sections labeled {label!r} don't rhyme visually "
                                    f"(cosine {cos:.2f} < {RHYME_FLOOR})")))
        if sims:
            subscores["fseq:rhyme"] = round(100 * float(np.mean(sims)))
    return subscores, findings


def evaluate(plan, analysis, series, *, repetition_map=None):
    """Return ``(subscores: dict[str,float], findings: list[Finding])`` from the render series.

    ``series`` is a ``FseqSeries`` (or None). Unreadable inputs / kill switch → ``({}, [])`` so the
    caller's objective score is left exactly as it was (never gate blind). Color adherence is a
    documented follow-up: the current series carries brightness/lit/motion, not per-node hue, so
    ``fseq:color`` is emitted only when hue data is available (none today) — a neutral no-op."""
    if not _enabled() or series is None or plan is None:
        return {}, []
    sections = _sections(plan)
    if not sections:
        return {}, []
    try:
        subscores: dict[str, float] = {}
        findings: list[Finding] = []
        for name, (score, fs) in {
            "fseq:coverage": _coverage(series, sections),
            "fseq:motion": _motion(series, sections),
            "fseq:sync": _sync(series, sections, analysis),
        }.items():
            if score is not None:
                subscores[name] = score
            findings += fs
        rr_sub, rr_find = _rhyme_and_range(series, sections, repetition_map)
        subscores.update(rr_sub)
        findings += rr_find
        return subscores, findings
    except Exception as exc:  # noqa: BLE001 — never gate blind on a metric bug
        log.debug("fseq metrics skipped: %s", exc)
        return {}, []
