"""Analysis bundle: one self-contained directory per song for downstream LLM consumers.

    <out>/<song-name>/
        manifest.json   what's inside: versions, capabilities present/lost, file list
        analysis.json   the full SongAnalysis (every beat, onset, chord, key change, stem arc, lyric)
        summary.json    a compact, code-derived per-section digest sized for an LLM prompt
        stems/*.mp3     the separated instrument stems (when stems ran)

`summary.json` is facts only — times, counts, normalized energy, chord runs, dominant
instruments, the lyric lines inside each section — never interpretation; labelling and mood are
the consumer's job. Pure: no LLM, no xLights, no network.
"""

from __future__ import annotations

import json
import shutil
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xlights_core.audio import SongAnalysis
from xlights_core.audio.analyzer import AudioAnalyzer, _content_key

BUNDLE_VERSION = 1


def _r(x: float, nd: int = 2) -> float:
    return round(float(x), nd)


def _in(t: float, a: float, b: float) -> bool:
    return a <= t < b


def _norm(vals: list[float]) -> list[float]:
    """Robust 5th-95th percentile min/max → 0..1 (song-relative, like normalize_intensities)."""
    if not vals:
        return []
    ordered = sorted(vals)
    n = len(ordered)
    lo, hi = ordered[max(0, int(0.05 * (n - 1)))], ordered[min(n - 1, round(0.95 * (n - 1)))]
    span = hi - lo
    return [0.5 if span <= 1e-9 else _r(max(0.0, min(1.0, (v - lo) / span)), 3) for v in vals]


def _chord_runs(labels: list[str]) -> list[str]:
    """Collapse consecutive repeats and no-chord markers: [C, C, N, G, G, Am] → [C, G, Am]."""
    out: list[str] = []
    for lab in labels:
        if lab and lab != "N" and (not out or out[-1] != lab):
            out.append(lab)
    return out


def _meter(sa: SongAnalysis) -> int | None:
    """Beats per bar: the most common highest bar_position reached before each downbeat."""
    bars, run = [], 0
    for b in sa.beats:
        if b.bar_position is None:
            return None
        if b.bar_position == 1 and run:
            bars.append(run)
        run = b.bar_position
    return Counter(bars).most_common(1)[0][0] if bars else None


def summarize(sa: SongAnalysis) -> dict[str, Any]:
    """The compact per-section digest (see module docstring)."""
    segs = list(sa.segments)
    lyric = sa.lyrics or {}
    lines = lyric.get("lines") or []
    instr = {(si.start_ms, si.end_ms): si for si in (sa.section_instrumentation or [])}
    energies = [statistics.fmean([p.rms for p in sa.energy_arc if _in(p.time, s.start, s.end)] or [0.0])
                for s in segs]
    sections = []
    for i, (s, e) in enumerate(zip(segs, _norm(energies))):
        dur = max(1e-6, s.end - s.start)
        si = instr.get((int(s.start * 1000), int(s.end * 1000)))
        if si is None:   # stale windows: best time-overlap match
            si = max((x for x in (sa.section_instrumentation or [])
                      if x.start_ms < s.end * 1000 and x.end_ms > s.start * 1000),
                     key=lambda x: min(x.end_ms, s.end * 1000) - max(x.start_ms, s.start * 1000),
                     default=None)
        key_here = next((k.key for k in reversed(sa.key) if k.time <= s.start + 0.01), sa.key_overall)
        sec: dict[str, Any] = {
            "index": i, "id": s.segment_id, "start": _r(s.start), "end": _r(s.end),
            "duration": _r(dur),
            "energy": e,
            "beats": sum(_in(b.time, s.start, s.end) for b in sa.beats),
            "downbeats": sum(_in(b.time, s.start, s.end) and b.bar_position == 1 for b in sa.beats),
            "onsets_per_s": _r(sum(_in(t, s.start, s.end) for t in sa.onsets) / dur),
            "key": key_here,
            "chords": _chord_runs([c.label for c in sa.chords if _in(c.time, s.start, s.end)])[:16],
        }
        if si is not None:
            sec["dominant"] = si.dominant
            sec["instrument_shares"] = {k: _r(v, 3) for k, v in si.shares.items()}
        sec_lines = [ln["text"] for ln in lines if _in(float(ln.get("start", -1)), s.start, s.end)]
        if sec_lines:
            sec["lyrics"] = sec_lines
        sections.append(sec)
    out: dict[str, Any] = {
        "duration_s": _r(sa.duration_s),
        "tempo_bpm": _r(sa.tempo_overall) if sa.tempo_overall else None,
        "tempo_range_bpm": ([_r(min(p.bpm for p in sa.tempo)), _r(max(p.bpm for p in sa.tempo))]
                            if sa.tempo else None),
        "beats_per_bar": _meter(sa),
        "key": sa.key_overall,
        "key_changes": [{"time": _r(k.time), "key": k.key} for k in sa.key],
        "counts": {"beats": len(sa.beats), "onsets": len(sa.onsets), "chords": len(sa.chords),
                   "harmonic_changes": len(sa.harmonic_changes), "sections": len(segs)},
        "stems": sorted(s.stem for s in sa.stems) if sa.stems else [],
        "lyrics": ({"title": lyric.get("title", ""), "artist": lyric.get("artist", ""),
                    "timed_lines": len(lines), "markers": lyric.get("sections", []),
                    "repeated": lyric.get("repeated", [])[:8]} if lines else None),
        "sections": sections,
    }
    return out


def write_bundle(sa: SongAnalysis, song_path: str, out_dir: str | Path, *,
                 degradations: list[dict] | None = None,
                 analyzer: AudioAnalyzer | None = None) -> Path:
    """Write the bundle for `sa` under `out_dir` (created/overwritten); returns the bundle dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(sa.model_dump_json(indent=1))
    (out / "summary.json").write_text(json.dumps(summarize(sa), indent=1))
    files = ["analysis.json", "summary.json"]
    src = (analyzer or AudioAnalyzer()).cache_dir / _content_key(song_path) / "stems"
    if src.is_dir():
        (out / "stems").mkdir(exist_ok=True)
        for f in sorted(src.iterdir()):
            if f.suffix in (".mp3", ".wav"):
                shutil.copy2(f, out / "stems" / f.name)
                files.append(f"stems/{f.name}")
    manifest = {
        "bundle_version": BUNDLE_VERSION,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"file": Path(song_path).name, "sha1_key": _content_key(song_path)},
        "analyzer_version": sa.analyzer_version,
        "structure_version": sa.structure_version,
        "plugins_used": sa.plugins_used,
        "capabilities": {"stems": bool(sa.stems), "timed_lyrics": bool((sa.lyrics or {}).get("lines")),
                         "section_instrumentation": bool(sa.section_instrumentation)},
        "degradations": degradations or [],
        "files": files,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return out
