"""Interpretation contracts: raw SongAnalysis -> per-analyst outputs -> a rich SongDescription.

The MusicBrief is what the Director plans from. It is a DEEP, human-reviewable description of
the song: labeled sections with per-section musical description + normalized dynamics +
instrument prevalence over time, the dynamic arc, harmony/transition cues, the narrative or
emotional journey, and the lyric lines worth featuring (with timestamps). Per-section intensity
is normalized in code; stem shares are filled in code from stem analysis. The point is that
every downstream creative choice can trace to something real here — no fabricated narrative.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LabeledSection(BaseModel):
    start_ms: int
    end_ms: int
    label: str = Field(description="semantic label: intro/verse/chorus/bridge/drop/breakdown/outro")
    intensity: float = Field(0.5, ge=0, le=1, description="normalized to THIS song: 0=quietest .. 1=peak")
    musical_description: str = ""               # 2-4 sentences: what actually happens musically here
    dominant_instruments: list[str] = []        # filled in code from stem section_instrumentation
    stem_shares: dict[str, float] = {}          # stem -> share (filled in code); {} if stems absent
    instrumentation_phrase: str = ""            # e.g. "driven by kick + bass, orchestral pads under"
    accents_ms: list[int] = []                  # hit/accent times within this section


class Identity(BaseModel):
    title: str = ""
    artist: str = ""
    genre: str = ""
    bpm: float | None = None
    time_signature: str = ""
    key_mode: str = ""
    character: str = ""                          # one-paragraph overall character


class DynamicArc(BaseModel):
    climax_ms: int | None = None
    builds_ms: list[int] = []
    drops_ms: list[int] = []
    range_note: str = ""                         # describe the dynamic range / shape


class FeaturedLyricMoment(BaseModel):
    line: str
    start_ms: int
    end_ms: int
    why: str = ""                                # why this line is worth featuring


class MusicBrief(BaseModel):
    sections: list[LabeledSection]
    repetition_map: dict[str, list[int]] = {}      # label -> section indices that recur
    energy_arc: list[float] = []
    key_mood: str = ""
    candidate_themes: list[str] = []
    transition_points_ms: list[int] = []
    # -- rich song-description layers --
    identity: Identity | None = None
    dynamic_arc: DynamicArc | None = None
    harmony_summary: str = ""
    transition_cues_ms: list[int] = []
    narrative_or_journey: str | None = None        # lyric narrative OR instrumental emotional journey
    featured_lyric_moments: list[FeaturedLyricMoment] = []
    # lyric-derived narrative (present only when lyrics were found)
    narrative_summary: str | None = None
    sentiment: str | None = None
    featured_lines: list[str] = []


# -- per-analyst structured outputs -------------------------------------------

class StructureOut(BaseModel):
    sections: list[LabeledSection]                 # each carries musical_description from the analyst
    repetition_map: dict[str, list[int]] = {}
    candidate_themes: list[str] = []


class RhythmOut(BaseModel):
    groove: str = ""
    energy_arc: list[float] = []
    climax_ms: int | None = None
    accents_ms: list[int] = []
    builds_ms: list[int] = []
    drops_ms: list[int] = []
    range_note: str = ""


class HarmonyOut(BaseModel):
    emotional_arc: str = ""
    key_mood: str = ""
    palette_hint: str = ""
    harmony_summary: str = ""
    transition_cues_ms: list[int] = []


class LyricOut(BaseModel):
    narrative_summary: str = ""
    sentiment: str = ""
    featured_lines: list[str] = []
    lyric_themes: list[str] = []
