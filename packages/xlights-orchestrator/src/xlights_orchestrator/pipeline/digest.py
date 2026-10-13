"""The analysis digest: a bounded, human-readable Markdown view of a cached `SongAnalysis`.

`xlo analyze` writes `analysis_digest.md` next to the cached analysis. It is the deterministic
half of the old song description plus the slices the analyst panel used to read — rendered once,
with no model call, so Claude and the user can discuss the song's structure over the same facts.

Everything here derives from the analysis alone: per-section energy normalized to the song's own
dynamic range (the `normalize_intensities` approach, over `segments`), dominant stems by
time-overlap with `section_instrumentation`, chord-change density, the timed lyric lines grouped
under the section they fall in, repeated lines and lyric markers, detected instrument entrances,
key, and whatever mood descriptors the analysis carries. Long series are sampled, lyric lines are
capped per section (the cap is stated in the footer), and the whole thing targets < 20 KB.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from xlights_core.audio import SongAnalysis

from .features import instrument_entrances
from .meter import resolve_beats_per_bar

DIGEST_NAME = "analysis_digest.md"
SIZE_BUDGET = 20 * 1024              # soft target; the lyric cap steps down until it fits
ENERGY_SAMPLES = 24                  # energy-arc points shown (same as the old panel slice)
LYRIC_CAP_STEPS = (10, 6, 4, 2)      # per-section lyric-line caps tried in order
LYRIC_LINE_CHARS = 90                # a single lyric line is truncated past this
REPEATED_CAP = 12
CHORD_LABELS_PER_SECTION = 6
STEM_SHARES_PER_SECTION = 3


# -- formatting ---------------------------------------------------------------------

def _mmss_t(ms: int) -> str:
    """Milliseconds → 'm:ss.t' (tenths, floored, never negative)."""
    ms = max(0, int(ms))
    s, tenths = divmod(ms // 100, 10)
    return f"{s // 60}:{s % 60:02d}.{tenths}"


def _clip(text: str, n: int = LYRIC_LINE_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _sample(seq, n=ENERGY_SAMPLES):
    if len(seq) <= n:
        return list(seq)
    step = len(seq) / n
    return [seq[int(i * step)] for i in range(n)]


# -- facts ----------------------------------------------------------------------------

def _timed_lines(lyrics: dict) -> list[tuple[str, int, int]]:
    """Best-effort (text, start_ms, end_ms) from the untyped lyrics dict (ported from the old
    `song_description._timed_lines`, which leaves with the MusicBrief)."""
    out: list[tuple[str, int, int]] = []
    if not isinstance(lyrics, dict):
        return out

    def _ms(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        return int(v * 1000) if v < 10000 else int(v)   # seconds vs already-ms heuristic

    lines = lyrics.get("lines") or lyrics.get("synced") or []
    for ln in lines if isinstance(lines, list) else []:
        if not isinstance(ln, dict):
            continue
        text = ln.get("text") or ln.get("line") or ln.get("words")
        start = _ms(ln.get("start", ln.get("start_ms", ln.get("time"))))
        end = _ms(ln.get("end", ln.get("end_ms")))
        if isinstance(text, str) and start is not None:
            out.append((text.strip(), start, end if end is not None else start + 2000))
    return out


def _section_energy(seg, points) -> float:
    a, b = seg.start * 1000, seg.end * 1000
    vals = [p.rms for p in points if a <= p.time * 1000 < b]
    return statistics.fmean(vals) if vals else 0.0


def section_energies(sa: SongAnalysis) -> list[float]:
    """Per-segment mean RMS normalized to 0..1 across THIS song (robust 5th–95th percentile),
    the same relative measure the old `normalize_intensities` wrote into the brief."""
    points = sa.energy_arc or []
    segs = sa.segments or []
    if not segs:
        return []
    if not points:
        return [0.5] * len(segs)
    energies = [_section_energy(s, points) for s in segs]
    ordered = sorted(energies)
    n = len(ordered)
    lo = ordered[max(0, int(0.05 * (n - 1)))]
    hi = ordered[min(n - 1, round(0.95 * (n - 1)))]
    span = hi - lo
    return [0.5 if span <= 1e-9 else round(max(0.0, min(1.0, (e - lo) / span)), 3)
            for e in energies]


def _instrumentation_for(seg, sa: SongAnalysis):
    """The `SectionInstrumentation` record overlapping this segment the most (code-owned, as
    `merge_dominant_instruments` did), or None."""
    best, best_ov = None, 0
    a, b = int(seg.start * 1000), int(seg.end * 1000)
    for inst in sa.section_instrumentation or []:
        ov = min(b, inst.end_ms) - max(a, inst.start_ms)
        if ov > best_ov:
            best, best_ov = inst, ov
    return best


def _stems_phrase(inst) -> str:
    if inst is None:
        return "—"
    if inst.shares:
        top = sorted(inst.shares.items(), key=lambda kv: (-kv[1], kv[0]))[:STEM_SHARES_PER_SECTION]
        return " · ".join(f"{k} {v * 100:.0f}%" for k, v in top)
    if inst.dominant:
        return " + ".join(inst.dominant)
    return "silent"


def _chords_in(seg, sa: SongAnalysis) -> list[str]:
    """Chord labels sounding in the segment, in order, with 'N' (no chord) dropped."""
    return [c.label for c in sa.chords or [] if seg.start <= c.time < seg.end and c.label != "N"]


def _chord_density(seg, sa: SongAnalysis) -> str:
    labels = _chords_in(seg, sa)
    if not labels:
        return "—"
    changes = sum(1 for x, y in zip(labels, labels[1:]) if x != y)
    dur_min = max(1e-6, (seg.end - seg.start) / 60.0)
    distinct: list[str] = []
    for lbl in labels:
        if lbl not in distinct:
            distinct.append(lbl)
    shown = ", ".join(distinct[:CHORD_LABELS_PER_SECTION])
    if len(distinct) > CHORD_LABELS_PER_SECTION:
        shown += "…"
    return f"{shown} ({len(distinct)} chords · {changes / dur_min:.1f} changes/min)"


def _lyric_markers(sa: SongAnalysis) -> list[dict]:
    lyr = sa.lyrics if isinstance(sa.lyrics, dict) else {}
    return [m for m in (lyr.get("sections") or []) if isinstance(m, dict) and m.get("start") is not None]


def _section_source(seg, marker_labels: set[str], has_markers: bool) -> str:
    sid = (seg.segment_id or "").lower()
    if has_markers and (sid in marker_labels or sid in ("intro", "outro")):
        return "lyrics"
    return "audio"


def _energy_descriptors(sa: SongAnalysis) -> list[str]:
    pts = sa.energy_arc or []
    if not pts:
        return []
    peak = max(pts, key=lambda p: (p.rms, -p.time))
    low = min(pts, key=lambda p: (p.rms, p.time))
    mean = statistics.fmean(p.rms for p in pts)
    out = [f"climax (energy peak) at **{_mmss_t(int(peak.time * 1000))}** (rms {peak.rms:.3f})",
           f"quietest at {_mmss_t(int(low.time * 1000))} (rms {low.rms:.3f}); mean rms {mean:.3f}"]
    if low.rms > 1e-6:
        ratio = peak.rms / low.rms
        feel = "wide" if ratio >= 4 else "moderate" if ratio >= 2 else "narrow"
        out.append(f"dynamic range {feel} (peak/quietest ×{ratio:.1f})")
    return out


def _mood_lines(sa: SongAnalysis) -> list[str]:
    mood = sa.mood if isinstance(sa.mood, dict) else None
    if not mood:
        return []
    out = []
    for k in sorted(mood):
        v = mood[k]
        if isinstance(v, float):
            v = f"{v:.3f}"
        elif not isinstance(v, (str, int, bool)) and v is not None:
            v = json.dumps(v, sort_keys=True, ensure_ascii=False)
        out.append(f"- {k}: {v}")
    return out


# -- render ----------------------------------------------------------------------------

def _render(sa: SongAnalysis, lyric_cap: int) -> str:
    L: list[str] = ["# Analysis digest\n"]
    segs = sa.segments or []
    dur_ms = int(sa.duration_s * 1000)
    bpb = resolve_beats_per_bar(sa)
    tempo = f"{sa.tempo_overall:.1f} BPM" if sa.tempo_overall else "unknown tempo"
    stems = sorted(f.stem for f in sa.stems or [])
    lyrics = sa.lyrics if isinstance(sa.lyrics, dict) else {}
    timed = _timed_lines(lyrics) if lyrics else []
    markers = _lyric_markers(sa)
    marker_labels = {str(m.get("label") or "").lower() for m in markers}

    # -- overview
    L.append("\n## Overview\n")
    title = lyrics.get("title") if lyrics else None
    artist = lyrics.get("artist") if lyrics else None
    if title or artist:
        L.append(f"- song: {' — '.join(b for b in [artist, title] if b)}\n")
    L.append(f"- duration: {_mmss_t(dur_ms)} ({sa.duration_s:.1f} s)\n")
    L.append(f"- tempo: {tempo} · meter: {bpb}/4 (beats per bar: {bpb})\n")
    L.append(f"- key: {sa.key_overall or 'unknown'}\n")
    L.append(f"- beats: {len(sa.beats or [])} · onsets: {len(sa.onsets or [])}"
             f" · chords: {len(sa.chords or [])} · harmonic changes: {len(sa.harmonic_changes or [])}\n")
    L.append(f"- stems: {', '.join(stems) if stems else 'none (no stem separation)'}\n")
    if timed:
        L.append(f"- lyrics: {len(timed)} timed lines · {len(markers)} section markers"
                 f" · {len(lyrics.get('repeated') or [])} repeated lines\n")
    else:
        L.append("- lyrics: none (instrumental, or no timed lyrics available)\n")
    L.append(f"- sections: {len(segs)} ("
             + ("lyric markers + audio, downbeat-snapped" if markers else "audio segmentation, downbeat-snapped")
             + ")\n")

    # -- energy arc
    L.append("\n## Energy arc\n")
    for d in _energy_descriptors(sa):
        L.append(f"- {d}\n")
    pts = _sample(sa.energy_arc or [])
    if pts:
        L.append(f"- sampled rms ({len(pts)} of {len(sa.energy_arc)} points): "
                 + ", ".join(f"{_mmss_t(int(p.time * 1000))} {p.rms:.2f}" for p in pts) + "\n")
    else:
        L.append("- no energy arc in the analysis\n")

    # -- sections
    L.append("\n## Sections\n")
    if not segs:
        L.append("_No sections in the analysis._\n")
    energies = section_energies(sa)
    lines_by_section: list[list[tuple[str, int, int]]] = [[] for _ in segs]
    orphan: list[tuple[str, int, int]] = []
    for ln in sorted(timed, key=lambda t: (t[1], t[2], t[0])):
        idx = next((i for i, s in enumerate(segs) if s.start * 1000 <= ln[1] < s.end * 1000), None)
        (lines_by_section[idx] if idx is not None else orphan).append(ln)
    if segs:
        L.append("\n| # | id | time | energy | dominant stems | chords | source |\n")
        L.append("|---|----|------|--------|----------------|--------|--------|\n")
        for i, (seg, e) in enumerate(zip(segs, energies)):
            L.append(f"| {i} | {seg.segment_id} | {_mmss_t(int(seg.start * 1000))}–{_mmss_t(int(seg.end * 1000))}"
                     f" | {e:.2f} | {_stems_phrase(_instrumentation_for(seg, sa))}"
                     f" | {_chord_density(seg, sa)} | {_section_source(seg, marker_labels, bool(markers))} |\n")
    for i, (seg, e) in enumerate(zip(segs, energies)):
        L.append(f"\n### {i}. {seg.segment_id} · {_mmss_t(int(seg.start * 1000))}–{_mmss_t(int(seg.end * 1000))}"
                 f" · energy {e:.2f}\n")
        inst = _instrumentation_for(seg, sa)
        if inst is not None and inst.dominant:
            L.append(f"- led by {' + '.join(inst.dominant)}\n")
        lns = lines_by_section[i]
        if not lns:
            L.append("- (no sung lines)\n" if timed else "- instrumental\n")
            continue
        for text, a, _b in lns[:lyric_cap]:
            L.append(f"- {_mmss_t(a)} {_clip(text)}\n")
        if len(lns) > lyric_cap:
            L.append(f"- … +{len(lns) - lyric_cap} more lines\n")
    if orphan:
        L.append("\n### Lines outside every section\n")
        for text, a, _b in orphan[:lyric_cap]:
            L.append(f"- {_mmss_t(a)} {_clip(text)}\n")

    # -- lyrics: repeated lines + markers
    L.append("\n## Lyrics\n")
    if not timed:
        L.append("_No lyrics: instrumental, or no timed lyrics available for this song._\n")
    else:
        rep = [r for r in (lyrics.get("repeated") or []) if isinstance(r, dict) and r.get("text")]
        rep = sorted(rep, key=lambda r: (-len(r.get("times") or []), r["text"]))
        L.append("\n### Repeated lines (likely hooks / choruses)\n")
        if not rep:
            L.append("- none detected\n")
        for r in rep[:REPEATED_CAP]:
            times = ", ".join(_mmss_t(int(float(t) * 1000)) for t in sorted(r.get("times") or []))
            L.append(f"- ×{len(r.get('times') or [])} “{_clip(str(r['text']))}” at {times}\n")
        if len(rep) > REPEATED_CAP:
            L.append(f"- … +{len(rep) - REPEATED_CAP} more repeated lines\n")
        L.append("\n### Lyric section markers\n")
        if not markers:
            L.append("- none (the lyric source had no [Verse]/[Chorus] headers)\n")
        for m in sorted(markers, key=lambda m: float(m["start"])):
            L.append(f"- {_mmss_t(int(float(m['start']) * 1000))} {m.get('label') or 'section'}\n")

    # -- instrument entrances
    L.append("\n## Instrument entrances\n")
    ents = instrument_entrances(sa)
    if not ents:
        L.append("- none detected" + ("" if stems else " (no stems)") + "\n")
    for t_ms, stem in ents:
        L.append(f"- {_mmss_t(t_ms)} {stem} surges in\n")

    # -- harmony + mood
    L.append("\n## Harmony\n")
    L.append(f"- key: {sa.key_overall or 'unknown'}\n")
    if sa.key and len(sa.key) > 1:
        changes = [k for k, prev in zip(sa.key[1:], sa.key) if k.key != prev.key]
        if changes:
            L.append("- key changes: " + ", ".join(f"{_mmss_t(int(k.time * 1000))} → {k.key}" for k in changes[:8]) + "\n")
    if sa.chords:
        L.append("- chords (sampled): " + ", ".join(c.label for c in _sample(sa.chords, 16)) + "\n")
    if sa.harmonic_changes:
        L.append("- harmonic changes (sampled): "
                 + ", ".join(_mmss_t(int(t * 1000)) for t in _sample(sa.harmonic_changes, 12)) + "\n")
    mood = _mood_lines(sa)
    L.append("\n## Mood\n")
    if mood:
        L.extend(f"{m}\n" for m in mood)
    else:
        L.append("_No mood descriptors in the analysis; interpret from the energy arc, key, and lyrics above._\n")

    # -- footer
    L.append(f"\n---\n_Deterministic digest from the cached analysis (no model call). Lyric lines capped at"
             f" {lyric_cap} per section; energy arc sampled to {ENERGY_SAMPLES} points; repeated lines"
             f" capped at {REPEATED_CAP}; lines truncated at {LYRIC_LINE_CHARS} chars._\n")
    return "".join(L)


def render_digest(analysis: SongAnalysis) -> str:
    """The digest Markdown. Deterministic; the per-section lyric cap steps down until the
    rendered text fits the size budget (the footer states the cap actually used)."""
    text = ""
    for cap in LYRIC_CAP_STEPS:
        text = _render(analysis, cap)
        if len(text.encode("utf-8")) <= SIZE_BUDGET:
            break
    return text


def write_digest(song_dir: Path, analysis: SongAnalysis) -> Path:
    """Write `analysis_digest.md` into the song's cache dir; returns its path."""
    song_dir = Path(song_dir)
    song_dir.mkdir(parents=True, exist_ok=True)
    out = song_dir / DIGEST_NAME
    out.write_text(render_digest(analysis), encoding="utf-8")
    return out
