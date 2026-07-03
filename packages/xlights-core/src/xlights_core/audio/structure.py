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

log = logging.getLogger(__name__)

MIN_SECTION_S = 6.0       # a section shorter than ~3 bars merges into its predecessor
                          # (a REAL 4-bar chorus at 133bpm is only ~7.2s — don't swallow it)
OUTRO_TAIL_S = 8.0        # split an outro when this much song remains after the last sung line
INFILL_SPAN_S = 25.0      # spans longer than this keep interior audio boundaries (instrumentals)
INFILL_EDGE_S = 10.0      # ...but only boundaries at least this far from the span's edges
LINE_NEAR_S = 2.0         # an audio boundary within this of a sung line is NOT instrumental
INSTR_MAX_SECTION_S = 32.0  # one look longer than ~35s reads as boring (user verdict)
INSTR_MIN_PIECE_S = 12.0    # don't shred a musical part into confetti
SEAM_ENERGY_NEAR_S = 0.75   # a harmonic seam scores by energy shift within this of it
                            # (energy_arc is ~0.5s-spaced, so ±0.75 catches the adjacent step)
DOWNBEAT_SNAP_TOL_S = 0.6   # snap a section boundary to a bar line within this (≈ one beat at
                            # ~130bpm) — sections should START on a downbeat, not a weak pickup


def _snap(t: float, beats: list[float]) -> float:
    return min(beats, key=lambda b: abs(b - t)) if beats else t


def _downbeats(analysis: SongAnalysis) -> list[float]:
    """Bar-line times from the beat grid (empty when the tracker labelled no bar positions —
    legacy caches / meters it couldn't resolve — so callers degrade to beat snapping)."""
    return [float(b.time) for b in (analysis.beats or []) if b.is_downbeat]


def _snap_downbeat(t: float, beats: list[float], downbeats: list[float],
                   tol_s: float = DOWNBEAT_SNAP_TOL_S) -> float:
    """Snap to the nearest DOWNBEAT when one is within `tol_s`, else to the nearest beat (today's
    behaviour). With no downbeats this is exactly `_snap` — section boundaries should land on bar
    lines, but only when a bar line is genuinely near the seam (a far one would distort timing)."""
    if downbeats:
        db = min(downbeats, key=lambda d: abs(d - t))
        if abs(db - t) <= tol_s:
            return db
    return _snap(t, beats)


def refine_segments_with_lyrics(analysis: SongAnalysis) -> bool:
    """Rebuild `analysis.segments` from timed lyric markers; False (untouched) when <2 markers."""
    lyr = getattr(analysis, "lyrics", None) or {}
    markers = [m for m in (lyr.get("sections") or []) if m.get("start") is not None]
    if len(markers) < 2:
        return False
    duration = float(analysis.duration_s)
    beats = [float(b.time) for b in (analysis.beats or [])]
    downbeats = _downbeats(analysis)          # sections start on the BAR LINE when one is near
    lines = lyr.get("lines") or []
    old = list(analysis.segments or [])

    # boundaries: snapped marker starts, deduped, in-range
    cuts: list[tuple[float, str]] = []
    for m in sorted(markers, key=lambda m: m["start"]):
        t = _snap_downbeat(float(m["start"]), beats, downbeats)
        if 0.0 < t < duration and (not cuts or t - cuts[-1][0] > 1e-6):
            cuts.append((t, str(m.get("label") or "section")))
    if len(cuts) < 2:
        return False

    # outro: split after the last sung line when a long tail remains
    last_sung = max((float(s["end"]) for s in lines), default=0.0)
    tail = _snap_downbeat(last_sung, beats, downbeats)
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
                    inner.append((_snap_downbeat(t, beats, downbeats), seg.segment_id))
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
                a = merged.pop()[0]
            merged.append([a, b, lbl])
    if merged and merged[-1][2] is None:            # degenerate: everything was tiny
        merged[-1][2] = filled[0][2]

    analysis.segments = [Segment(start=round(a, 3), end=round(b, 3), segment_id=str(lbl))
                         for a, b, lbl in merged]
    log.info("structure refined from lyrics: %d segments (%s)", len(analysis.segments),
             ", ".join(s.segment_id for s in analysis.segments))
    return True


def cap_long_segments(analysis: SongAnalysis,
                      max_section_s: float = INSTR_MAX_SECTION_S,
                      min_piece_s: float = INSTR_MIN_PIECE_S) -> bool:
    """Subdivide ANY segment longer than `max_section_s` at the music's own seams — preferring
    harmonic-change points, then energy-delta peaks, then beat-snapped time. Pieces are labeled
    parent id + ordinal ("A" -> "A1","A2",...). False (untouched) when every segment already fits;
    idempotent on its own output.

    Runs regardless of lyrics, so a lyric song's long instrumental stretch (e.g. a 100s intro
    before the first sung line, which the lyric refiner can't cut for lack of markers there) is
    still broken up — no single section runs past the cap.
    """
    old = list(analysis.segments or [])
    if all(s.end - s.start <= max_section_s + 1e-6 for s in old):
        return False
    beats = [float(b.time) for b in (analysis.beats or [])]
    downbeats = _downbeats(analysis)              # bar lines (empty → beat-snapped, as before)

    # candidates (time, STRENGTH): a cut should land on a real structural break, not just the
    # latest seam before the cap. Strength = how much the ENERGY changes there (|Δrms|): the music
    # dropping out / surging back is the audible boundary. Harmonic-change times are candidates too,
    # scored by the energy shift around them — so a seam that is BOTH a chord change and an energy
    # jump wins, but a dense run of harmonic changes at steady volume no longer all tie at 1.0
    # (which made the old code pick the latest → it drifted to the ~32s cap). Snapped to beats.
    arc = analysis.energy_arc or []
    edelta = [(float(q.time), abs(float(q.rms) - float(p.rms))) for p, q in zip(arc, arc[1:])]

    def _energy_strength(t: float) -> float:
        return max((d for et, d in edelta if abs(et - t) <= SEAM_ENERGY_NEAR_S), default=0.0)

    # Snap candidates to the BAR LINE (downbeat) when one is near: off-beat seams collapse onto
    # their downbeat, and a loud seam near the cap whose bar line is PAST the cap then falls outside
    # the window and is dropped — so an earlier downbeat phrase boundary wins over a louder off-beat.
    cand: dict[float, float] = {}
    for t in (analysis.harmonic_changes or []):        # harmonic seams, scored by coincident energy
        s = _snap_downbeat(float(t), beats, downbeats)
        cand[s] = max(cand.get(s, 0.0), _energy_strength(float(t)))
    for et, d in edelta:                               # energy-delta points are seams in their own right
        s = _snap_downbeat(et, beats, downbeats)
        cand[s] = max(cand.get(s, 0.0), d)
    cands = sorted(cand.items())

    out: list[Segment] = []
    counts: dict[str, int] = {}                         # parent id -> ordinal (A,A -> A1..A7)
    for seg in old:
        a, b = float(seg.start), float(seg.end)
        if b - a <= max_section_s + 1e-6:
            out.append(seg)                             # short segment: untouched, byte-for-byte
            continue
        cuts: list[float] = []
        prev = a
        while b - prev > max_section_s + 1e-6:
            lo, hi = prev + min_piece_s, prev + max_section_s
            # cap keeps the eventual tail >= min_piece_s (>= MIN_SECTION_S when min is too big)
            cap = next((c for c in (min(hi, b - min_piece_s), min(hi, b - MIN_SECTION_S), hi)
                        if c >= lo))
            inside = [(t, w) for t, w in cands if lo <= t <= cap]
            if inside:
                cut = max(inside, key=lambda tw: (tw[1], -tw[0]))[0]   # strongest seam; ties → EARLIEST
            else:
                # no seam at all in the window (no harmonic/energy data): even spacing near the cap
                near = [bt for bt in beats if prev < bt <= cap]
                cut = min(near, key=lambda bt: abs(bt - cap)) if near else cap
            # bar-align the chosen cut: a downbeat within the window [lo, cap] and the snap tolerance
            # (so the spacing fallback and any off-bar candidate still land on a bar line, never
            # below the min-piece floor `lo` nor past the cap)
            db_in = [d for d in downbeats if lo <= d <= cap and abs(d - cut) <= DOWNBEAT_SNAP_TOL_S]
            if db_in:
                cut = min(db_in, key=lambda d: abs(d - cut))
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
                                     max_section_s: float = INSTR_MAX_SECTION_S,
                                     min_piece_s: float = INSTR_MIN_PIECE_S) -> bool:
    """The lyric refiner's complement for INSTRUMENTAL songs (no timed lines): cap long audio
    segments at musical seams. Lyric songs get the same cap as a final pass inside
    `refine_segments_with_lyrics`, so this stays the no-lyrics entry point. False when lyrics are
    timed or nothing needed capping."""
    lyr = getattr(analysis, "lyrics", None) or {}
    if lyr.get("lines"):
        return False                                    # lyric refiner's territory
    return cap_long_segments(analysis, max_section_s, min_piece_s)
