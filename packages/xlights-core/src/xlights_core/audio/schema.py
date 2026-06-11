"""Typed `SongAnalysis` — objective measurements only (no interpretation).

Lean and JSON-friendly: lists of small records, no large matrices. Confidence is
optional (present only where a plugin supplies one). Reserved optional fields let the
later enrichment extractors (stems/mood/track-id/lyrics) slot in without a contract change.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

ANALYZER_VERSION = 2


class TempoPoint(BaseModel):
    time: float
    bpm: float


class Beat(BaseModel):
    time: float
    bar_position: int | None = None  # 1 == downbeat; None if unknown

    @property
    def is_downbeat(self) -> bool:
        return self.bar_position == 1


class KeyPoint(BaseModel):
    time: float
    key: str  # e.g. "Eb major" (algorithmic, not interpretive)


class Chord(BaseModel):
    time: float
    label: str  # e.g. "Ebm7"; "N" == no chord


class Segment(BaseModel):
    start: float
    end: float
    segment_id: str  # algorithmic structure id (e.g. "A", "N1") — NOT verse/chorus


class EnergyPoint(BaseModel):
    time: float
    rms: float


class StemFeatures(BaseModel):
    """Per-instrument-stem measurements (optional enrichment)."""

    stem: str                              # vocals | drums | bass | other
    energy_arc: list[EnergyPoint] = []     # per-stem RMS over time
    onsets: list[float] = []               # per-stem onset times (s)


class SectionInstrumentation(BaseModel):
    """Per-section instrument prevalence derived from stem energy."""

    segment_id: str
    start_ms: int
    end_ms: int
    shares: dict[str, float] = {}          # stem -> normalized energy share (sums to ~1); {} if silent
    dominant: list[str] = []               # top stem(s); [] if silent


class SongAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    duration_s: float
    sample_rate: int

    tempo: list[TempoPoint] = []          # tempo curve
    tempo_overall: float | None = None    # median bpm
    beats: list[Beat] = []
    key: list[KeyPoint] = []
    key_overall: str | None = None
    chords: list[Chord] = []
    segments: list[Segment] = []
    onsets: list[float] = []              # times (s)
    harmonic_changes: list[float] = []    # times (s)
    energy_arc: list[EnergyPoint] = []

    confidences: dict[str, float] = {}    # feature -> confidence, only where available
    plugins_used: list[str] = []

    # -- stem enrichment (populated only when stems=True) --------------------
    stems: list[StemFeatures] | None = None
    section_instrumentation: list[SectionInstrumentation] | None = None

    # -- reserved enrichment (unpopulated in this change) --------------------
    mood: dict | None = None
    track_id: dict | None = None
    lyrics: dict | None = None

    analyzer_version: int = ANALYZER_VERSION
