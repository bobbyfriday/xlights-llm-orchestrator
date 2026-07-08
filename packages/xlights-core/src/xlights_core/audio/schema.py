"""Typed `SongAnalysis` — objective measurements only (no interpretation).

Lean and JSON-friendly: lists of small records, no large matrices. Confidence is
optional (present only where a plugin supplies one). Reserved optional fields let the
later enrichment extractors (stems/mood/track-id/lyrics) slot in without a contract change.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# Bump when the RAW analysis output (VAMP/librosa features, stems) changes so content-keyed caches
# recompute. NOT for segmentation-logic changes — those re-derive cheaply from cached lyrics/beats
# via STRUCTURE_VERSION (see structure.ensure_structure); bumping this would needlessly discard
# expensive stems and non-reproducible lyric alignment.
ANALYZER_VERSION = 2

# Bump when the deterministic SEGMENTATION logic (structure.py) changes. A cached analysis with an
# older stamp re-runs refinement in place from its already-cached lyrics + beats — no re-analysis,
# no lyric re-alignment. v1: downbeat-aligned section boundaries (`_snap_downbeat`); pre-v1 caches
# beat-snapped section starts, landing them ~1 beat before the bar line.
STRUCTURE_VERSION = 1


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
    structure_version: int = 0   # 0 = pre-migration; current-logic segments are stamped STRUCTURE_VERSION
