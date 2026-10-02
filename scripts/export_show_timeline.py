"""Export a song's analysis as a shared timeline for the light show AND a companion video.

Offline and deterministic: no xLights, no LLM key. It reads (or computes) the cached
`SongAnalysis` and writes three files that all use the SAME millisecond clock, so a video edit
and an xLights sequence built from them stay in sync:

    <out>/<name>.xtiming     xLights timing tracks (Sections, Bars, Beats, per-stem Onsets,
                             Chords, Impacts) — import via the Timing-track "Import" menu.
    <out>/cue_sheet.csv      one row per cue: track, label, start/end in ms, seconds, SMPTE
                             timecode at --fps, and the video frame number.
    <out>/cue_sheet.json     the same cues plus the song summary (tempo, key, duration).

Sections come from the audio segmentation (capped like the pipeline caps instrumentals), or
from a hand-labeled `--sections` JSON — a list of ``{"label": "...", "start": seconds}`` — whose
starts are snapped to the nearest bar line so cuts land on the downbeat.

Run::

    python scripts/export_show_timeline.py --song "mp3/song.mp3" --out shows/song \
        [--sections shows/song/sections.json] [--fps 30] [--stems]
"""

from __future__ import annotations

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path

from xlights_core.audio.analyzer import AudioAnalyzer
from xlights_core.audio.structure import refine_segments_for_instrumental
from xlights_orchestrator.pipeline.timing import (
    TimingMark,
    TimingTrack,
    _frame_safe,
    _tile,
    build_timing_tracks,
)

IMPACT_MIN_GAP_S = 6.0     # impacts closer than ~3 bars read as one hit
IMPACT_MAX = 16            # punctuation, not a strobe


def _downbeats(sa) -> list[float]:
    return [float(b.time) for b in sa.beats if getattr(b, "bar_position", None) == 1]


def _snap(t: float, grid: list[float]) -> float:
    return min(grid, key=lambda g: abs(g - t)) if grid else t


def _sections(sa, sections_file: str | None) -> list[TimingMark]:
    end_ms = int(sa.duration_s * 1000)
    if sections_file:
        spec = json.loads(Path(sections_file).read_text())
        bars = [0.0] + _downbeats(sa)
        starts = [0.0 if i == 0 else _snap(float(s["start"]), bars) for i, s in enumerate(spec)]
        ends = starts[1:] + [sa.duration_s]
        return [TimingMark(s["label"], int(a * 1000), int(b * 1000))
                for s, a, b in zip(spec, starts, ends)]
    refine_segments_for_instrumental(sa)           # cap long audio segments at musical seams
    marks = [TimingMark(seg.segment_id, int(seg.start * 1000), int(seg.end * 1000))
             for seg in sa.segments]
    if marks:
        marks[-1].end_ms = end_ms
    return marks


def _bar_aligned(sa) -> list[TimingTrack]:
    """Beats/Bars from the tracker's own `bar_position`. The pipeline's reference grid tiles from
    the first detected beat (`beats[::4]`), which mislabels the bar line whenever the song starts
    on a pickup — the video and the show must agree on where beat 1 is."""
    end_ms = int(sa.duration_s * 1000)
    beats = sorted(sa.beats, key=lambda b: b.time)
    beat_ms = [int(b.time * 1000) for b in beats]
    labels = [str(b.bar_position) for b in beats]
    bars = [int(t * 1000) for t in _downbeats(sa)]
    bar_labels = [f"Bar {i + 1}" for i in range(len(bars))]
    return [TimingTrack("Beats", _tile(beat_ms, end_ms, labels)),
            TimingTrack("Bars", _tile(bars, end_ms, bar_labels))]


def _impacts(sa) -> list[TimingMark]:
    """The biggest energy surges (|Δrms| rising), bar-snapped and spaced — the moments a video
    cut and a full-yard light hit should share."""
    arc = sa.energy_arc or []
    rises = sorted(((float(q.rms) - float(p.rms), float(q.time)) for p, q in pairwise(arc)
                    if q.rms > p.rms), reverse=True)
    bars = _downbeats(sa)
    picked: list[float] = []
    for _, t in rises:
        t = _snap(t, bars)
        if all(abs(t - p) >= IMPACT_MIN_GAP_S for p in picked):
            picked.append(t)
        if len(picked) >= IMPACT_MAX:
            break
    return [TimingMark(f"Impact {i + 1}", int(t * 1000), int(t * 1000) + 500)
            for i, t in enumerate(sorted(picked))]


def _timecode(ms: int, fps: int) -> str:
    frames = round(ms * fps / 1000)
    ff = frames % fps
    s = frames // fps
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{ff:02d}"


def write_xtiming(path: Path, tracks: list[TimingTrack]) -> None:
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


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--song", required=True)
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--sections", default=None, help="hand-labeled sections JSON")
    ap.add_argument("--fps", type=int, default=30, help="video frame rate for timecodes")
    ap.add_argument("--stems", action="store_true", help="separate stems if not cached")
    ap.add_argument("--name", default=None, help="xtiming file name (default: song stem)")
    args = ap.parse_args(argv)

    sa = AudioAnalyzer().analyze(args.song, stems=args.stems)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sections = TimingTrack("Sections", _sections(sa, args.sections))
    reference = [t for t in build_timing_tracks(sa, None)    # Onsets/Chords (+Lyrics if timed)
                 if t.name not in ("Beats", "Bars")]
    tracks = [sections, *_bar_aligned(sa), *reference, TimingTrack("Impacts", _impacts(sa))]
    tracks = [t for t in tracks if t.has_marks()]

    name = args.name or Path(args.song).stem
    write_xtiming(out / f"{name}.xtiming", tracks)

    cues = []
    for tr in tracks:
        if tr.name in ("Sections", "Bars", "Impacts") or tr.name.startswith("Chords"):
            for m in _frame_safe(tr.marks):
                cues.append({"track": tr.name, "label": m.label, "start_ms": m.start_ms,
                             "end_ms": m.end_ms, "start_s": round(m.start_ms / 1000, 3),
                             "timecode": _timecode(m.start_ms, args.fps),
                             "frame": round(m.start_ms * args.fps / 1000)})
    cues.sort(key=lambda c: (c["start_ms"], c["track"]))
    with open(out / "cue_sheet.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cues[0]))
        w.writeheader()
        w.writerows(cues)
    summary = {"song": Path(args.song).name, "duration_s": round(sa.duration_s, 3),
               "tempo_bpm": round(sa.tempo_overall, 2), "key": sa.key_overall, "fps": args.fps,
               "stems": [s.stem for s in (sa.stems or [])], "tracks": [t.name for t in tracks]}
    (out / "cue_sheet.json").write_text(json.dumps({"summary": summary, "cues": cues}, indent=2))
    print(json.dumps(summary, indent=2))
    for m in sections.marks:
        print(f"  {_timecode(m.start_ms, args.fps)}  {m.start_ms / 1000:7.2f}s  {m.label}")


if __name__ == "__main__":
    main()
