"""Reference timing tracks (Section/Beat/Bar/per-stem-Onset/Chords/Lyrics) patched into the
finished `.xsq` OFFLINE — a grid for the human editing the sequence. Mirrors the corpus `.xsq`
timing-track XML exactly; never blocks finalize. See [[timing-tracks-plan]]."""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from ..song_description import _timed_lines
from .meter import resolve_beats_per_bar

log = logging.getLogger(__name__)

BEATS_PER_BAR = 4   # default/fallback only; the real meter is resolved per song
LAST_MARK_MS = 500            # clamp a final tiled mark so it isn't a giant block
MAX_ONSET_STEMS = 3           # selective: drums + lead/bass, not all six
_MIN_ENERGY_SHARE = 0.10      # a stem needs ≥10% of the loudest stem's mean energy to get a track


@dataclass
class TimingMark:
    label: str
    start_ms: int
    end_ms: int


@dataclass
class TimingTrack:
    name: str
    marks: list[TimingMark] = field(default_factory=list)


def _tile(times_ms: list[int], end_ms: int | None, labels: list[str] | None = None) -> list[TimingMark]:
    """Pair sorted times t_i→t_{i+1} into contiguous marks; clamp the last to LAST_MARK_MS/end."""
    ts = sorted(int(t) for t in times_ms)
    out: list[TimingMark] = []
    for i, t in enumerate(ts):
        if i + 1 < len(ts):
            e = ts[i + 1]
        else:
            e = min(t + LAST_MARK_MS, end_ms) if end_ms and end_ms > t else t + LAST_MARK_MS
        if e <= t:
            continue
        out.append(TimingMark(labels[i] if labels else "", t, e))
    return out


# -- builders -----------------------------------------------------------------

def _section_track(brief, fallback_sections) -> TimingTrack | None:
    secs = getattr(brief, "sections", None) or None
    if secs:
        marks = [TimingMark(s.label, s.start_ms, s.end_ms) for s in secs]
    elif fallback_sections:                       # SectionPlan has no label → index labels
        marks = [TimingMark(f"Section {i + 1}", s.start_ms, s.end_ms)
                 for i, s in enumerate(fallback_sections)]
    else:
        return None
    return TimingTrack("Sections", marks)


def _beat_track(sa, end_ms, beats_per_bar=BEATS_PER_BAR) -> TimingTrack | None:
    beats = [int(b.time * 1000) for b in (getattr(sa, "beats", None) or [])]
    if not beats:
        return None
    labels = [str((i % beats_per_bar) + 1) for i in range(len(beats))]   # beat-in-bar 1..N
    return TimingTrack("Beats", _tile(beats, end_ms, labels))


def _bar_track(sa, end_ms, beats_per_bar=BEATS_PER_BAR) -> TimingTrack | None:
    beats = sorted(int(b.time * 1000) for b in (getattr(sa, "beats", None) or []))
    if len(beats) < beats_per_bar:
        return None
    downbeats = beats[::beats_per_bar]                                   # bars at the song's meter
    return TimingTrack("Bars", _tile(downbeats, end_ms))


def _prominent_stems(sa, stems_cfg) -> list[str]:
    """Rank by mean stem ENERGY (not onset count): the demucs vocals stem on an instrumental is
    onset-noisy but near-silent in energy, so energy correctly drops it. Excludes "other"."""
    energy: dict[str, float] = {}
    for f in getattr(sa, "stems", None) or []:
        if f.stem == "other" or not f.onsets:        # need onsets to mark; "other" is the catch-all
            continue
        arc = f.energy_arc or []
        energy[f.stem] = (sum(p.rms for p in arc) / len(arc)) if arc else 0.0
    if not energy:
        return []
    if stems_cfg:
        return [s for s in stems_cfg if s in energy]
    top = max(energy.values()) or 1.0
    ranked = sorted((s for s, e in energy.items() if e >= _MIN_ENERGY_SHARE * top),
                    key=lambda s: (-energy[s], s))
    if "drums" in energy and "drums" not in ranked[:MAX_ONSET_STEMS]:    # always include drums if present
        ranked = ["drums"] + [s for s in ranked if s != "drums"]
    return ranked[:MAX_ONSET_STEMS]


def _onset_tracks(sa, end_ms, stems_cfg) -> list[TimingTrack]:
    feats = {f.stem: f for f in (getattr(sa, "stems", None) or [])}
    out = []
    for stem in _prominent_stems(sa, stems_cfg):
        ons = [int(t * 1000) for t in (feats[stem].onsets or [])]
        if ons:
            out.append(TimingTrack(f"Onsets ({stem})", _tile(ons, end_ms)))   # blank labels (no per-onset energy)
    return out


def _chord_track(sa, end_ms) -> TimingTrack | None:
    chords = getattr(sa, "chords", None) or []
    if not chords:
        return None
    times = [int(c.time * 1000) for c in chords]
    labels = [c.label for c in chords]
    order = sorted(range(len(times)), key=lambda i: times[i])
    marks = _tile([times[i] for i in order], end_ms, [labels[i] for i in order])
    return TimingTrack("Chords", marks) if marks else None


def _lyric_track(sa, end_ms) -> TimingTrack | None:
    lyrics = getattr(sa, "lyrics", None)
    lines = _timed_lines(lyrics) if lyrics else []
    marks = [TimingMark(text, start, end) for (text, start, end) in lines if end > start]
    return TimingTrack("Lyrics", marks) if marks else None


def build_timing_tracks(sa, brief, *, fallback_sections=None, onset_stems=None) -> list[TimingTrack]:
    """Assemble all reference tracks from the analysis + brief (skips any with no data)."""
    end_ms = int(getattr(sa, "duration_s", 0) * 1000) or None
    bpb = resolve_beats_per_bar(sa, brief)        # label/stride the beat+bar grid at the real meter
    candidates = [
        _section_track(brief, fallback_sections),
        _beat_track(sa, end_ms, bpb),
        _bar_track(sa, end_ms, bpb),
        *_onset_tracks(sa, end_ms, onset_stems),
        _chord_track(sa, end_ms),
        _lyric_track(sa, end_ms),
    ]
    return [t for t in candidates if t and t.marks]


# -- offline patcher ----------------------------------------------------------

def patch_xsq_timing_tracks(xsq_path: str | Path, tracks: list[TimingTrack]) -> bool:
    """Inject timing tracks into a saved `.xsq` offline (DisplayElements + ElementEffects).

    Mirrors the corpus XML (no ids on timing marks). Atomic write (temp + os.replace) so a
    mid-write failure can't corrupt the file. Best-effort: returns False, file intact, on error.
    """
    xsq_path = Path(xsq_path)
    tracks = [t for t in tracks if t.marks]
    if not tracks:
        return False
    try:
        tree = ET.parse(xsq_path)
        root = tree.getroot()
        display = root.find("DisplayElements")
        effects = root.find("ElementEffects")
        if display is None:
            display = ET.SubElement(root, "DisplayElements")
        if effects is None:
            effects = ET.SubElement(root, "ElementEffects")
        names = {tr.name for tr in tracks}
        for parent in (display, effects):            # idempotent: drop our same-named timing tracks first
            for el in [e for e in parent if e.get("type") == "timing" and e.get("name") in names]:
                parent.remove(el)
        for tr in tracks:
            ET.SubElement(display, "Element", {
                "type": "timing", "name": tr.name,
                "visible": "1", "collapsed": "0", "active": "1"})
            el = ET.SubElement(effects, "Element", {"type": "timing", "name": tr.name})
            layer = ET.SubElement(el, "EffectLayer")
            for m in tr.marks:
                ET.SubElement(layer, "Effect", {
                    "label": m.label, "startTime": str(int(m.start_ms)),
                    "endTime": str(int(m.end_ms))})
        tmp = xsq_path.with_suffix(xsq_path.suffix + ".tmp")
        tree.write(tmp, encoding="UTF-8", xml_declaration=True)
        os.replace(tmp, xsq_path)                  # atomic
        log.info("timing tracks: wrote %d tracks to %s", len(tracks), xsq_path.name)
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort; leave the .xsq intact
        log.warning("timing-track patch failed for %s: %s", xsq_path, exc)
        return False
