"""Refine song structure from timed lyric section markers (Genius [Verse]/[Chorus]/...).

The audio segmenter hears coarse structure (candy cane lane: 4 segments over 3.5 min); the
lyrics carry the REAL structure (8 markers → ~10 sections). When `align_lyrics` produced timed
markers, rebuild `analysis.segments` from them: boundaries beat-snapped, tiny sections merged,
intro/outro split out, and the audio segmentation retained as in-fill inside long instrumental
spans. Labels become ground truth for the analysts. Code owns boundaries; LLMs keep judgment.
"""

from __future__ import annotations

import logging

from .schema import Segment, SongAnalysis

log = logging.getLogger(__name__)

MIN_SECTION_S = 6.0       # a section shorter than ~3 bars merges into its predecessor
                          # (a REAL 4-bar chorus at 133bpm is only ~7.2s — don't swallow it)
OUTRO_TAIL_S = 8.0        # split an outro when this much song remains after the last sung line
INFILL_SPAN_S = 25.0      # spans longer than this keep interior audio boundaries (instrumentals)
INFILL_EDGE_S = 10.0      # ...but only boundaries at least this far from the span's edges
LINE_NEAR_S = 2.0         # an audio boundary within this of a sung line is NOT instrumental


def _snap(t: float, beats: list[float]) -> float:
    return min(beats, key=lambda b: abs(b - t)) if beats else t


def refine_segments_with_lyrics(analysis: SongAnalysis) -> bool:
    """Rebuild `analysis.segments` from timed lyric markers; False (untouched) when <2 markers."""
    lyr = getattr(analysis, "lyrics", None) or {}
    markers = [m for m in (lyr.get("sections") or []) if m.get("start") is not None]
    if len(markers) < 2:
        return False
    duration = float(analysis.duration_s)
    beats = [float(b.time) for b in (analysis.beats or [])]
    lines = lyr.get("lines") or []
    old = list(analysis.segments or [])

    # boundaries: snapped marker starts, deduped, in-range
    cuts: list[tuple[float, str]] = []
    for m in sorted(markers, key=lambda m: m["start"]):
        t = _snap(float(m["start"]), beats)
        if 0.0 < t < duration and (not cuts or t - cuts[-1][0] > 1e-6):
            cuts.append((t, str(m.get("label") or "section")))
    if len(cuts) < 2:
        return False

    # outro: split after the last sung line when a long tail remains
    last_sung = max((float(s["end"]) for s in lines), default=0.0)
    tail = _snap(last_sung, beats)
    if duration - tail >= OUTRO_TAIL_S and tail > cuts[-1][0] + 1e-6:
        cuts.append((tail, "outro"))

    # spans: intro + marker-to-marker (+ outro tail)
    spans: list[tuple[float, float, str]] = []
    if cuts[0][0] > 1e-6:
        spans.append((0.0, cuts[0][0], "intro"))
    for (t, lbl), nxt in zip(cuts, cuts[1:] + [(duration, "")]):
        if nxt[0] - t > 1e-6:
            spans.append((t, nxt[0], lbl))

    # in-fill: long spans keep interior audio boundaries that sit in instrumental silence
    filled: list[tuple[float, float, str]] = []
    for a, b, lbl in spans:
        inner = []
        if b - a > INFILL_SPAN_S:
            for seg in old:
                t = float(seg.start)
                if a + INFILL_EDGE_S < t < b - INFILL_EDGE_S and not any(
                        float(s["start"]) - LINE_NEAR_S < t < float(s["end"]) + LINE_NEAR_S
                        for s in lines):
                    inner.append((_snap(t, beats), seg.segment_id))
        prev = a
        for t, sid in sorted(set(inner)):
            if t - prev > MIN_SECTION_S:
                filled.append((prev, t, lbl))
                prev, lbl = t, sid                  # remainder takes the audio segment's id
        filled.append((prev, b, lbl))

    # merge: short sections fold into their predecessor (a short intro folds FORWARD)
    merged: list[list] = []
    for a, b, lbl in filled:
        if merged and b - a < MIN_SECTION_S:
            merged[-1][1] = b
        elif not merged and b - a < MIN_SECTION_S:
            merged.append([a, b, None])             # placeholder: fold into the NEXT section
        else:
            if merged and merged[-1][2] is None:
                a, lbl = merged.pop()[0], lbl
            merged.append([a, b, lbl])
    if merged and merged[-1][2] is None:            # degenerate: everything was tiny
        merged[-1][2] = filled[0][2]

    analysis.segments = [Segment(start=round(a, 3), end=round(b, 3), segment_id=str(lbl))
                         for a, b, lbl in merged]
    log.info("structure refined from lyrics: %d segments (%s)", len(analysis.segments),
             ", ".join(s.segment_id for s in analysis.segments))
    return True
