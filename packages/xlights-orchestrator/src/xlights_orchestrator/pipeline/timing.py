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
from .meter import DEFAULT_BEATS_PER_BAR as BEATS_PER_BAR, resolve_beats_per_bar

log = logging.getLogger(__name__)

LAST_MARK_MS = 500            # clamp a final tiled mark so it isn't a giant block
FRAME_MS = 50                 # sequence frame granularity; xLights drops sub-frame (zero-width) marks
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
    # multi-layer tracks (e.g. the phoneme lyric track: phrases/words/phonemes) carry a layer per
    # entry, written as one <EffectLayer> each. Single-layer tracks leave this None and use `marks`.
    layers: list[list[TimingMark]] | None = None

    def layer_list(self) -> list[list[TimingMark]]:
        return self.layers if self.layers is not None else [self.marks]

    def has_marks(self) -> bool:
        return any(layer for layer in self.layer_list())


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


def _frame_safe(marks: list[TimingMark], frame: int = FRAME_MS) -> list[TimingMark]:
    """Snap each mark to the frame grid and guarantee ≥1-frame width, so xLights never drops a
    zero-width mark on load. Dense onsets/phonemes that fall within a single frame (< ``frame`` ms
    apart) can't be distinguished at the sequence frame rate, so a mark colliding with the previous
    one is merged (dropped). Contiguous tiled marks (end == next start) are preserved."""
    out: list[TimingMark] = []
    for m in marks:
        s = round(m.start_ms / frame) * frame
        e = round(m.end_ms / frame) * frame
        if e <= s:                                  # sub-frame span → give it exactly one frame
            e = s + frame
        if out and s < out[-1].end_ms:              # overlaps the previous frame-snapped mark → drop
            continue
        out.append(TimingMark(m.label, s, e))
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


def _overall_onset_track(sa, end_ms) -> TimingTrack | None:
    """Fallback when stems aren't separated: one `Onsets` track from the whole-mix onsets, so we
    don't lose the onset grid entirely (we compute these regardless of stem availability)."""
    ons = sorted(int(t * 1000) for t in (getattr(sa, "onsets", None) or []))
    return TimingTrack("Onsets", _tile(ons, end_ms)) if ons else None


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


def _ms(v) -> int | None:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return int(v * 1000) if v < 10000 else int(v)   # seconds vs already-ms heuristic


def _timed_words(lyrics) -> list[tuple[str, int, int]]:
    """(word, start_ms, end_ms) across all lines, from `lyrics.lines[].words` (Whisper word timing)."""
    out: list[tuple[str, int, int]] = []
    lines = lyrics.get("lines") if isinstance(lyrics, dict) else None
    for ln in lines or []:
        for w in (ln.get("words") if isinstance(ln, dict) else None) or []:
            if not isinstance(w, dict):
                continue
            text = w.get("word") or w.get("text") or ""
            s, e = _ms(w.get("start")), _ms(w.get("end"))
            if text and s is not None and e is not None and e > s:
                out.append((str(text).strip(), s, e))
    out.sort(key=lambda x: x[1])
    return out


def _viseme_marks(words: list[tuple[str, int, int]]) -> list[TimingMark]:
    """Tile each word's mouth shapes evenly across its span; fill the gaps between words with `rest`."""
    from xlights_core.audio.phonemes import word_to_visemes
    marks: list[TimingMark] = []
    prev_end = words[0][1] if words else 0
    for word, s, e in words:
        if s > prev_end:                              # silence between words → closed mouth
            marks.append(TimingMark("rest", prev_end, s))
        vis = word_to_visemes(word) or ["rest"]
        step = max(1, (e - s) // len(vis))
        for i, v in enumerate(vis):
            ms = s + i * step
            me = e if i == len(vis) - 1 else min(e, s + (i + 1) * step)
            if me > ms:
                marks.append(TimingMark(v, ms, me))
        prev_end = e
    return marks


def _phoneme_track(sa, end_ms, name: str = "Faces") -> TimingTrack | None:
    """A 3-layer lyric timing track (phrases / words / phonemes) the xLights Faces effect reads."""
    lyrics = getattr(sa, "lyrics", None)
    words = _timed_words(lyrics) if lyrics else []
    if not words:
        return None
    phrases = [TimingMark(t, s, e) for (t, s, e) in _timed_lines(lyrics) if e > s]
    word_marks = [TimingMark(w, s, e) for (w, s, e) in words]
    phoneme_marks = _viseme_marks(words)
    return TimingTrack(name, layers=[phrases, word_marks, phoneme_marks])


def build_timing_tracks(sa, brief, *, fallback_sections=None, onset_stems=None) -> list[TimingTrack]:
    """Assemble all reference tracks from the analysis + brief (skips any with no data)."""
    end_ms = int(getattr(sa, "duration_s", 0) * 1000) or None
    bpb = resolve_beats_per_bar(sa, brief)        # label/stride the beat+bar grid at the real meter
    onset_tracks = _onset_tracks(sa, end_ms, onset_stems)
    if not onset_tracks:                          # no stems → keep the onset grid from the whole mix
        fallback = _overall_onset_track(sa, end_ms)
        onset_tracks = [fallback] if fallback else []
    candidates = [
        _section_track(brief, fallback_sections),
        _beat_track(sa, end_ms, bpb),
        _bar_track(sa, end_ms, bpb),
        *onset_tracks,
        _chord_track(sa, end_ms),
        _lyric_track(sa, end_ms),
        _phoneme_track(sa, end_ms),               # phrases/words/phonemes for the Faces effect
    ]
    return [t for t in candidates if t and t.has_marks()]


# -- offline patcher ----------------------------------------------------------

def patch_xsq_timing_tracks(xsq_path: str | Path, tracks: list[TimingTrack]) -> bool:
    """Inject timing tracks into a saved `.xsq` offline (DisplayElements + ElementEffects).

    Mirrors the corpus XML (no ids on timing marks). Atomic write (temp + os.replace) so a
    mid-write failure can't corrupt the file. Best-effort: returns False, file intact, on error.
    """
    xsq_path = Path(xsq_path)
    tracks = [t for t in tracks if t.has_marks()]
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
            for marks in tr.layer_list():            # one <EffectLayer> per layer (phrases/words/phonemes)
                layer = ET.SubElement(el, "EffectLayer")
                for m in _frame_safe(marks):         # frame-snap so xLights drops no zero-width marks
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
