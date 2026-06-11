"""Parse each VAMP plugin output into schema records (pinned to observed shapes)."""

from __future__ import annotations

from ..schema import Beat, Chord, KeyPoint, Segment, TempoPoint
from . import vamp_host as vh


def _values0(item: dict) -> float | None:
    v = item.get("values")
    try:
        return float(v[0]) if v is not None and len(v) else None
    except (TypeError, ValueError, IndexError):
        return None


def tempo(y, sr) -> list[TempoPoint]:
    out = vh.items(vh.run("qm-vamp-plugins:qm-tempotracker", "tempo", y, sr))
    pts = []
    for it in out:
        bpm = _values0(it)
        if bpm is None:  # fall back to the "<n> bpm" label
            lab = (it.get("label") or "").split()[0:1]
            bpm = float(lab[0]) if lab and lab[0].replace(".", "", 1).isdigit() else None
        if bpm:
            pts.append(TempoPoint(time=vh.ts(it), bpm=bpm))
    return pts


def beats(y, sr) -> list[Beat]:
    out = vh.items(vh.run("qm-vamp-plugins:qm-barbeattracker", "beats", y, sr))
    res = []
    for it in out:
        lab = (it.get("label") or "").strip()
        res.append(Beat(time=vh.ts(it), bar_position=int(lab) if lab.isdigit() else None))
    return res


def key(y, sr) -> list[KeyPoint]:
    out = vh.items(vh.run("qm-vamp-plugins:qm-keydetector", "key", y, sr))
    return [KeyPoint(time=vh.ts(it), key=(it.get("label") or "").strip()) for it in out]


def onsets(y, sr) -> list[float]:
    out = vh.items(vh.run("qm-vamp-plugins:qm-onsetdetector", "onsets", y, sr))
    return [vh.ts(it) for it in out]


def segments(y, sr) -> list[Segment]:
    out = vh.items(vh.run("segmentino:segmentino", "segmentation", y, sr))
    segs = []
    for it in out:
        start = vh.ts(it)
        try:
            dur = float(it.get("duration", 0) or 0)
        except (TypeError, ValueError):
            dur = 0.0
        segs.append(Segment(start=start, end=start + dur, segment_id=(it.get("label") or "").strip()))
    return segs


def chords(y, sr) -> list[Chord]:
    out = vh.items(vh.run("nnls-chroma:chordino", "simplechord", y, sr))
    return [Chord(time=vh.ts(it), label=(it.get("label") or "").strip()) for it in out]


def harmonic_changes(y, sr) -> list[float]:
    out = vh.items(vh.run("qm-vamp-plugins:qm-tonalchange", "changepositions", y, sr))
    return [vh.ts(it) for it in out]
