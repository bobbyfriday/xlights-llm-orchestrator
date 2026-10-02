"""Export a song's audio analysis as a shared clock for an xLights show and a music video.

Writes into ``--out``:

- ``<name>.xtiming``      every reference timing track (Sections, Bars, Beats, Onsets, Chords,
                          Impacts) in xLights' multi-track import format (Timing track → Import)
- ``cue_sheet.csv/.json`` every Section, Bar, Chord, Impact and Shot with ms, timecode and frame
- ``video_timeline.json`` the shot list resolved to real times, for a renderer or editor script

Inputs are hand-edited JSON next to the outputs:

- ``sections.json``  ``[{"label", "bar" | "start_ms", "palette"?}, ...]``. Starts are snapped to
                     the nearest downbeat; each section runs to the next one (the last to the end).
- ``shots.json``     ``[{"title", "bar" | "start_ms", "video", "lights", "sync"?}, ...]``. Same
                     resolution as sections. Optional; without it no shots are exported.

Bars are 1-based: ``bar: 1`` is the first downbeat the tracker found. Timecodes are ``MM:SS:FF``
at ``--fps``; ms values are the master clock (time 0 = the first sample of the audio file).

    python scripts/export_show_timeline.py --song "mp3/Highway to Hell.mp3" \\
        --out shows/highway-to-hell --sections shows/highway-to-hell/sections.json \\
        --fps 30 --name "Highway to Hell"
"""

from __future__ import annotations

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from bisect import bisect_left
from pathlib import Path
from types import SimpleNamespace

DEFAULT_IMPACTS = 16
MIN_IMPACT_GAP_BARS = 2       # two surges closer than this are one event; keep the stronger


# -- clock ----------------------------------------------------------------------

def frame_of(ms: int, fps: int) -> int:
    return round(ms * fps / 1000)


def timecode(ms: int, fps: int) -> str:
    """``MM:SS:FF`` at ``fps`` (minutes are not wrapped into hours)."""
    f = frame_of(ms, fps)
    s, ff = divmod(f, fps)
    mm, ss = divmod(s, 60)
    return f"{mm:02d}:{ss:02d}:{ff:02d}"


def downbeats_ms(sa, beats_per_bar: int) -> list[int]:
    """Bar starts: the tracker's ``bar_position == 1`` beats when it labelled them, else every
    ``beats_per_bar``-th beat (the same stride the orchestrator's Bars track uses)."""
    beats = sorted(getattr(sa, "beats", None) or [], key=lambda b: b.time)
    labelled = [int(b.time * 1000) for b in beats if getattr(b, "bar_position", None) == 1]
    if len(labelled) >= 2:
        return labelled
    return [int(b.time * 1000) for b in beats[::beats_per_bar]]


def bar_of(ms: int, downbeats: list[int]) -> int | None:
    """1-based bar containing ``ms`` (None before the first downbeat)."""
    i = bisect_left(downbeats, ms + 1) - 1
    return i + 1 if i >= 0 else None


def _snap(ms: int, downbeats: list[int]) -> int:
    if not downbeats:
        return ms
    i = bisect_left(downbeats, ms)
    near = [downbeats[j] for j in (i - 1, i) if 0 <= j < len(downbeats)]
    return min(near, key=lambda d: abs(d - ms))


def _start_of(item: dict, downbeats: list[int]) -> int:
    """Resolve an entry's start: ``bar`` (1-based) wins; else ``start_ms`` snapped to a downbeat
    (``start_ms: 0`` stays at 0 so a cold open can begin before the first bar)."""
    if "bar" in item:
        n = int(item["bar"])
        if not 1 <= n <= len(downbeats):
            raise ValueError(f"{item.get('label') or item.get('title')!r}: bar {n} is outside "
                             f"1..{len(downbeats)}")
        return downbeats[n - 1]
    ms = int(item.get("start_ms", 0))
    return 0 if ms == 0 else _snap(ms, downbeats)


def _spans(items: list[dict], downbeats: list[int], end_ms: int) -> list[tuple[dict, int, int]]:
    """(item, start_ms, end_ms) contiguous spans, sorted by start, the last ending at ``end_ms``."""
    starts = sorted(((_start_of(it, downbeats), k, it) for k, it in enumerate(items)),
                    key=lambda x: (x[0], x[1]))
    out = []
    for i, (s, _, it) in enumerate(starts):
        e = starts[i + 1][0] if i + 1 < len(starts) else end_ms
        if e <= s:
            raise ValueError(f"{it.get('label') or it.get('title')!r} has no duration "
                             f"(starts at {s} ms, next starts at {e} ms)")
        out.append((it, s, e))
    return out


# -- impacts --------------------------------------------------------------------

def _mean_rms(arc: list[tuple[int, float]], lo: int, hi: int) -> float:
    vals = [r for t, r in arc if lo <= t < hi]
    return sum(vals) / len(vals) if vals else 0.0


def detect_impacts(sa, downbeats: list[int], end_ms: int, n: int = DEFAULT_IMPACTS,
                   min_gap_bars: int = MIN_IMPACT_GAP_BARS) -> list[int]:
    """The ``n`` biggest energy surges, on bar lines: score each downbeat by the jump in mean
    whole-mix RMS from the bar before it to the bar after it, then keep the strongest positive
    jumps at least ``min_gap_bars`` apart. Returned sorted by time."""
    arc = sorted((int(p.time * 1000), float(p.rms)) for p in (getattr(sa, "energy_arc", None) or []))
    if not arc or len(downbeats) < 2:
        return []
    bounds = downbeats + [end_ms]
    scored = []
    for i in range(1, len(downbeats)):
        before = _mean_rms(arc, bounds[i - 1], bounds[i])
        after = _mean_rms(arc, bounds[i], bounds[i + 1])
        if after > before:
            scored.append((after - before, i))
    picked: list[int] = []
    for _, i in sorted(scored, key=lambda x: (-x[0], x[1])):
        if all(abs(i - j) >= min_gap_bars for j in picked):
            picked.append(i)
        if len(picked) == n:
            break
    return sorted(downbeats[i] for i in picked)


# -- timing tracks --------------------------------------------------------------

def build_tracks(sa, sections, downbeats, impacts, end_ms, beats_per_bar, onset_stems=None):
    """The orchestrator's reference tracks (Sections/Beats/Onsets/Chords/Lyrics), with Bars on
    the same downbeat grid the shots use, plus an Impacts track."""
    from xlights_orchestrator.pipeline.timing import (
        TimingMark,
        TimingTrack,
        build_timing_tracks,
    )

    brief = SimpleNamespace(
        sections=[SimpleNamespace(label=it["label"], start_ms=s, end_ms=e) for it, s, e in sections],
        identity=SimpleNamespace(time_signature=f"{beats_per_bar}/4"))
    tracks = [t for t in build_timing_tracks(sa, brief, onset_stems=onset_stems) if t.name != "Bars"]
    bars = [TimingMark(str(i + 1), s, e)
            for i, (s, e) in enumerate(zip(downbeats, downbeats[1:] + [end_ms])) if e > s]
    hits = [TimingMark(f"Impact {i + 1}", t, min(t + 500, end_ms)) for i, t in enumerate(impacts)]
    at = next((i for i, t in enumerate(tracks) if t.name == "Beats"), len(tracks))
    tracks.insert(at, TimingTrack("Bars", bars))
    tracks.append(TimingTrack("Impacts", hits))
    return [t for t in tracks if t.has_marks()]


def write_xtiming(tracks, path: Path) -> None:
    """xLights multi-track ``.xtiming``: ``<timings><timing name=..><EffectLayer><Effect ..>``."""
    from xlights_orchestrator.pipeline.timing import _frame_safe

    root = ET.Element("timings")
    for tr in tracks:
        el = ET.SubElement(root, "timing", {"name": tr.name, "SourceVersion": "2024.01"})
        for marks in tr.layer_list():
            layer = ET.SubElement(el, "EffectLayer")
            for m in _frame_safe(marks):
                ET.SubElement(layer, "Effect", {"label": m.label, "starttime": str(m.start_ms),
                                                "endtime": str(m.end_ms)})
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


# -- export ---------------------------------------------------------------------

def build_timeline(sa, sections_raw: list[dict], shots_raw: list[dict] | None, *, fps: int,
                   name: str, n_impacts: int = DEFAULT_IMPACTS) -> dict:
    """Resolve sections, impacts and shots against the analysis' clock (pure; no I/O)."""
    from xlights_orchestrator.pipeline.meter import resolve_beats_per_bar

    end_ms = round(sa.duration_s * 1000)
    bpb = resolve_beats_per_bar(sa)
    downbeats = downbeats_ms(sa, bpb)
    if not downbeats:
        raise ValueError("analysis has no beats; cannot build a bar grid")
    sections = _spans(sections_raw, downbeats, end_ms)
    impacts = detect_impacts(sa, downbeats, end_ms, n_impacts)
    shots = _spans(shots_raw, downbeats, end_ms) if shots_raw else []

    def section_at(ms):
        return next((it["label"] for it, s, e in sections if s <= ms < e), None)

    def shot_at(ms):
        return next((i for i, (_, s, e) in enumerate(shots) if s <= ms < e), None)

    def bar_span(s, e):
        return bar_of(s, downbeats), bar_of(max(s, e - 1), downbeats)

    impact_rows = []
    for i, t in enumerate(impacts):
        k = shot_at(t)
        impact_rows.append({
            "index": i + 1, "ms": t, "timecode": timecode(t, fps), "frame": frame_of(t, fps),
            "bar": bar_of(t, downbeats), "section": section_at(t),
            "shot": shots[k][0]["title"] if k is not None else None})

    shot_rows = []
    for i, (it, s, e) in enumerate(shots):
        b0, b1 = bar_span(s, e)
        shot_rows.append({
            "index": i + 1, "title": it["title"], "section": section_at(s),
            "start_ms": s, "end_ms": e, "tc_in": timecode(s, fps), "tc_out": timecode(e, fps),
            "frame_in": frame_of(s, fps), "frame_out": frame_of(e, fps),
            "duration_s": round((e - s) / 1000, 3), "bar_in": b0, "bar_out": b1,
            "impacts": [r["index"] for r in impact_rows if s <= r["ms"] < e],
            "video": it.get("video", ""), "lights": it.get("lights", ""), "sync": it.get("sync", "")})

    section_rows = []
    for it, s, e in sections:
        b0, b1 = bar_span(s, e)
        section_rows.append({
            "label": it["label"], "start_ms": s, "end_ms": e,
            "tc_in": timecode(s, fps), "tc_out": timecode(e, fps),
            "bar_in": b0, "bar_out": b1,
            "bars": (b1 - (b0 or 1) + 1) if b1 else 0, "palette": it.get("palette", "")})

    return {
        "name": name, "audio": Path(sa.path).name, "fps": fps, "duration_ms": end_ms,
        "duration_tc": timecode(end_ms, fps), "tempo_bpm": sa.tempo_overall,
        "beats_per_bar": bpb, "bars": len(downbeats), "key": sa.key_overall,
        "downbeats_ms": downbeats, "sections": section_rows, "impacts": impact_rows,
        "shots": shot_rows,
        "_resolved": {"sections": sections, "impacts": impacts},   # for build_tracks; not written
    }


def cue_rows(sa, timeline: dict) -> list[dict]:
    fps, end_ms = timeline["fps"], timeline["duration_ms"]
    rows = []

    def add(kind, index, label, s, e):
        rows.append({"type": kind, "index": index, "label": label, "start_ms": s, "end_ms": e,
                     "timecode": timecode(s, fps), "frame": frame_of(s, fps)})

    for i, r in enumerate(timeline["sections"]):
        add("Section", i + 1, r["label"], r["start_ms"], r["end_ms"])
    db = timeline["downbeats_ms"]
    for i, (s, e) in enumerate(zip(db, db[1:] + [end_ms])):
        add("Bar", i + 1, f"Bar {i + 1}", s, e)
    chords = sorted(getattr(sa, "chords", None) or [], key=lambda c: c.time)
    for i, c in enumerate(chords):
        s = int(c.time * 1000)
        e = int(chords[i + 1].time * 1000) if i + 1 < len(chords) else end_ms
        add("Chord", i + 1, c.label, s, e)
    for r in timeline["impacts"]:
        add("Impact", r["index"], r["shot"] or f"Impact {r['index']}", r["ms"], r["ms"])
    for r in timeline["shots"]:
        add("Shot", r["index"], r["title"], r["start_ms"], r["end_ms"])
    rows.sort(key=lambda r: (r["start_ms"], r["type"]))
    return rows


def export(sa, out_dir: Path, sections_raw, shots_raw, *, fps: int, name: str,
           n_impacts: int = DEFAULT_IMPACTS, onset_stems=None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tl = build_timeline(sa, sections_raw, shots_raw, fps=fps, name=name, n_impacts=n_impacts)
    resolved = tl.pop("_resolved")
    tracks = build_tracks(sa, resolved["sections"], tl["downbeats_ms"], resolved["impacts"],
                          tl["duration_ms"], tl["beats_per_bar"], onset_stems)
    rows = cue_rows(sa, tl)

    paths = [out_dir / f"{name}.xtiming", out_dir / "cue_sheet.csv",
             out_dir / "cue_sheet.json", out_dir / "video_timeline.json"]
    write_xtiming(tracks, paths[0])
    with paths[1].open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["type"])
        w.writeheader()
        w.writerows(rows)
    paths[2].write_text(json.dumps(rows, indent=2) + "\n")
    paths[3].write_text(json.dumps(tl, indent=2) + "\n")
    return paths


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--song", required=True, help="audio file (the master clock)")
    p.add_argument("--out", required=True, type=Path, help="output directory")
    p.add_argument("--sections", type=Path, help="sections.json (default: <out>/sections.json)")
    p.add_argument("--shots", type=Path, help="shots.json (default: <out>/shots.json if present)")
    p.add_argument("--fps", type=int, default=30, help="video frame rate for timecodes")
    p.add_argument("--name", help="show name; names the .xtiming (default: the song's file stem)")
    p.add_argument("--impacts", type=int, default=DEFAULT_IMPACTS, help="how many impacts to mark")
    p.add_argument("--onset-stems", help="comma list, e.g. drums,guitar,vocals (default: auto)")
    p.add_argument("--no-cache", action="store_true", help="re-analyze instead of using the cache")
    a = p.parse_args(argv)

    sections_path = a.sections or a.out / "sections.json"
    shots_path = a.shots or (a.out / "shots.json")
    sections_raw = json.loads(sections_path.read_text())
    shots_raw = json.loads(shots_path.read_text()) if shots_path.exists() else None
    stems = [s.strip() for s in a.onset_stems.split(",")] if a.onset_stems else None

    from xlights_core.audio import AudioAnalyzer

    sa = AudioAnalyzer().analyze(a.song, use_cache=not a.no_cache, stems=True)
    for path in export(sa, a.out, sections_raw, shots_raw, fps=a.fps,
                       name=a.name or Path(a.song).stem, n_impacts=a.impacts, onset_stems=stems):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
