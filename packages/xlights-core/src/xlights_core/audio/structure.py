"""Refine song structure from timed lyric section markers (Genius [Verse]/[Chorus]/...).

The audio segmenter hears coarse structure (candy cane lane: 4 segments over 3.5 min); the
lyrics carry the REAL structure (8 markers → ~10 sections). When `align_lyrics` produced timed
markers, rebuild `analysis.segments` from them: boundaries beat-snapped, tiny sections merged,
intro/outro split out, and the audio segmentation retained as in-fill inside long instrumental
spans. Labels become ground truth for the analysts. Code owns boundaries; LLMs keep judgment.

Instrumental songs (no timed lines) get the complement: long coarse audio segments are
subdivided at harmonic/energy seams so no single look runs past ~32s.
"""

from __future__ import annotations

import logging

from .schema import Segment, SongAnalysis
from .tuning import (  # show-feel dials — see audio/tuning.py
    INFILL_EDGE_S,
    INFILL_SPAN_S,
    INSTR_MIN_PIECE_S,
    INSTR_SECTION_FLEX_S,
    INSTR_TARGET_SECTION_S,
    LINE_NEAR_S,
    MIN_SECTION_S,
    OUTRO_TAIL_S,
    SEAM_ENERGY_NEAR_S,
    SEAM_MIN_STRENGTH_FRAC,
)

log = logging.getLogger(__name__)


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


def cap_long_segments(analysis: SongAnalysis,
                      target_s: float = INSTR_TARGET_SECTION_S,
                      flex_s: float = INSTR_SECTION_FLEX_S,
                      min_piece_s: float = INSTR_MIN_PIECE_S) -> bool:
    """Subdivide ANY segment longer than the ceiling (`target_s + flex_s`) at the music's own seams.
    Each cut AIMS for `target_s` but flexes ±`flex_s` to land on a real structural break — the
    energy dropping out / surging back — instead of snapping to a fixed length. Pieces are labeled
    parent id + ordinal ("A" -> "A1","A2",...). False (untouched) when every segment already fits
    the ceiling; idempotent on its own output.

    Runs regardless of lyrics, so a lyric song's long instrumental stretch (e.g. a 100s intro
    before the first sung line, which the lyric refiner can't cut for lack of markers there) is
    still broken up — no single section runs past the ceiling.
    """
    ceiling = target_s + flex_s
    old = list(analysis.segments or [])
    if all(s.end - s.start <= ceiling + 1e-6 for s in old):
        return False
    beats = [float(b.time) for b in (analysis.beats or [])]

    # candidates (time, STRENGTH): a cut should land on a real structural break. Strength = how much
    # the ENERGY changes there (|Δrms|): the music dropping out / surging back is the audible
    # boundary. Harmonic-change times are candidates too, scored by the energy shift around them — so
    # a seam that is BOTH a chord change and an energy jump scores highest, while a dense run of chord
    # changes at steady volume scores ~0. `strength_bar` is the floor for a shift to count as a real
    # break (vs. noise), set relative to the song's own RMS span so it adapts to the mix. Snapped to beats.
    arc = analysis.energy_arc or []
    edelta = [(float(q.time), abs(float(q.rms) - float(p.rms))) for p, q in zip(arc, arc[1:])]
    rms = [float(p.rms) for p in arc]
    strength_bar = SEAM_MIN_STRENGTH_FRAC * (max(rms) - min(rms)) if rms else 0.0

    def _energy_strength(t: float) -> float:
        return max((d for et, d in edelta if abs(et - t) <= SEAM_ENERGY_NEAR_S), default=0.0)

    cand: dict[float, float] = {}
    for t in (analysis.harmonic_changes or []):        # harmonic seams, scored by coincident energy
        s = _snap(float(t), beats)
        cand[s] = max(cand.get(s, 0.0), _energy_strength(float(t)))
    for et, d in edelta:                               # energy-delta points are seams in their own right
        s = _snap(et, beats)
        cand[s] = max(cand.get(s, 0.0), d)
    cands = sorted(cand.items())

    out: list[Segment] = []
    counts: dict[str, int] = {}                         # parent id -> ordinal (A,A -> A1..A7)
    for seg in old:
        a, b = float(seg.start), float(seg.end)
        if b - a <= ceiling + 1e-6:
            out.append(seg)                             # short segment: untouched, byte-for-byte
            continue
        cuts: list[float] = []
        prev = a
        while b - prev > ceiling + 1e-6:
            target = prev + target_s
            lo = prev + max(target_s - flex_s, min_piece_s)      # earliest allowed cut
            hi = min(prev + target_s + flex_s, b - min_piece_s)  # latest; keep the tail >= min_piece
            lo = min(lo, hi)                            # degenerate guard (tail clamp below the floor)
            window = [(t, w) for t, w in cands if lo <= t <= hi]
            real = [tw for tw in window if tw[1] >= strength_bar and tw[1] > 0.0]
            pick = real or window           # a real energy break, else any seam (harmonic-only / flat)
            if pick:                        # land on the seam NEAREST the target; ties → the stronger
                cut = min(pick, key=lambda tw: (abs(tw[0] - target), -tw[1]))[0]
            else:
                # no seam at all in the window: even spacing at the target (beat-snapped)
                near = [bt for bt in beats if lo <= bt <= hi]
                cut = min(near, key=lambda bt: abs(bt - target)) if near else min(max(target, lo), hi)
            cuts.append(cut)
            prev = cut
        pieces = [[x, y] for x, y in zip([a] + cuts, cuts + [b])]
        if len(pieces) > 1 and pieces[-1][1] - pieces[-1][0] < MIN_SECTION_S:
            tail = pieces.pop()                         # fold a tiny tail into the previous piece
            pieces[-1][1] = tail[1]
        for x, y in pieces:
            counts[seg.segment_id] = counts.get(seg.segment_id, 0) + 1
            out.append(Segment(start=round(x, 3), end=round(y, 3),
                               segment_id=f"{seg.segment_id}{counts[seg.segment_id]}"))
    analysis.segments = out
    log.info("long segments capped: %d -> %d segments (%s)", len(old), len(out),
             ", ".join(s.segment_id for s in out))
    return True


def refine_segments_for_instrumental(analysis: SongAnalysis,
                                     target_s: float = INSTR_TARGET_SECTION_S,
                                     flex_s: float = INSTR_SECTION_FLEX_S,
                                     min_piece_s: float = INSTR_MIN_PIECE_S) -> bool:
    """The lyric refiner's complement for INSTRUMENTAL songs (no timed lines): cap long audio
    segments at musical seams. Lyric songs get the same cap as a final pass inside
    `refine_segments_with_lyrics`, so this stays the no-lyrics entry point. False when lyrics are
    timed or nothing needed capping."""
    lyr = getattr(analysis, "lyrics", None) or {}
    if lyr.get("lines"):
        return False                                    # lyric refiner's territory
    return cap_long_segments(analysis, target_s, flex_s, min_piece_s)
