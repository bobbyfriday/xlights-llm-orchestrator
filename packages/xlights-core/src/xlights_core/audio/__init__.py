"""Audio analysis: extract a SongAnalysis from an audio file (offline, VAMP+librosa)."""

from __future__ import annotations

from .analyzer import AudioAnalyzer
from .envelope import song_tail_envelope
from .exceptions import AudioDependencyMissing, AudioError, AudioPluginsMissing
from .phonemes import VISEMES, arpabet_to_visemes, word_to_visemes
from .schema import (
    Beat,
    Chord,
    EnergyPoint,
    KeyPoint,
    SectionInstrumentation,
    Segment,
    SongAnalysis,
    StemFeatures,
    TempoPoint,
)

__all__ = [
    "AudioAnalyzer",
    "AudioError",
    "AudioPluginsMissing",
    "AudioDependencyMissing",
    "SongAnalysis",
    "TempoPoint",
    "Beat",
    "KeyPoint",
    "Chord",
    "Segment",
    "EnergyPoint",
    "StemFeatures",
    "SectionInstrumentation",
    "song_tail_envelope",
    "VISEMES",
    "arpabet_to_visemes",
    "word_to_visemes",
]
