"""Fuse extractor outputs into one SongAnalysis (measurements only)."""

from __future__ import annotations

import statistics
from collections import Counter

from .extractors import librosa_ext as le
from .extractors import vamp_features as vf
from .schema import SongAnalysis

PLUGINS_USED = [
    "qm-vamp-plugins:qm-tempotracker",
    "qm-vamp-plugins:qm-barbeattracker",
    "qm-vamp-plugins:qm-keydetector",
    "qm-vamp-plugins:qm-onsetdetector",
    "segmentino:segmentino",
    "nnls-chroma:chordino",
    "qm-vamp-plugins:qm-tonalchange",
]


def build(path: str, y, sr: int) -> SongAnalysis:
    tempo = vf.tempo(y, sr)
    beats = vf.beats(y, sr)
    key = vf.key(y, sr)
    segments = vf.segments(y, sr)
    chords = vf.chords(y, sr)
    onsets = vf.onsets(y, sr)
    harmonic = vf.harmonic_changes(y, sr)
    energy = le.energy_arc(y, sr)

    tempo_overall = statistics.median(p.bpm for p in tempo) if tempo else None
    key_overall = Counter(k.key for k in key).most_common(1)[0][0] if key else None

    return SongAnalysis(
        path=path,
        duration_s=len(y) / sr,
        sample_rate=sr,
        tempo=tempo,
        tempo_overall=tempo_overall,
        beats=beats,
        key=key,
        key_overall=key_overall,
        chords=chords,
        segments=segments,
        onsets=onsets,
        harmonic_changes=harmonic,
        energy_arc=energy,
        confidences={},  # these plugins don't expose usable confidences; none fabricated
        plugins_used=PLUGINS_USED,
    )
