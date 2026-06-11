"""Pydantic contracts: SongAnalysis -> ShowPlan -> EffectInstruction[]."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ShowPalette(BaseModel):
    name: str = ""
    colors: list[str] = []                  # named colors of the show's core palette
    mapping: str = ""                        # how color maps to moods/sections + why


class GroupMotif(BaseModel):
    role: str = ""                           # this group's job in the show
    style: str = ""                          # its signature effect style
    color: str = ""                          # its color treatment


class KeyMoment(BaseModel):
    at_ms: int
    kind: str = ""                           # accent | climax | lyric
    treatment: str = ""                      # the deliberate visual punctuation


class SectionPlan(BaseModel):
    """Per-section creative direction over prop groups (plain `look` + grounded direction)."""

    start_ms: int
    end_ms: int
    target_groups: list[str] = Field(description="prop GROUP names to light in this section")
    effect_family: str = Field(description="an effect type to use (must be a placeable type)")
    intensity: float = Field(ge=0, le=1, description="0=calm .. 1=peak")
    rationale: str = ""                      # grounded: cite this section's dynamics/instruments/accents
    # -- creative direction (additive) --
    look: str = ""                           # PLAIN-language: what a viewer sees here (no music theory)
    palette: list[str] = []                  # section colors
    effect_types: list[str] = []             # richer than the single effect_family
    motion: str = ""                         # the motion/feel
    transition: str = ""                     # how it flows into the next section
    # -- rhythmic intent (beat layer; all defaulted/back-compat) --
    pulse_groups: list[str] = []             # groups that punctuate the beat (default 04_BEAT_*)
    follow_stem: str = ""                    # whose rhythm to ride (default the prominent stem)
    accent_effect: str = ""                  # placeable punctuation effect (default On)
    pulse_on: str = ""                       # "beat" | "onset" (default beat)


class ShowPlan(BaseModel):
    sections: list[SectionPlan]
    # -- creative brief (additive) --
    experience: str = ""                     # PLAIN-language audience vision (leads the brief; no theory)
    concept: str = ""                        # the artistic concept
    palette: ShowPalette | None = None
    group_motifs: dict[str, GroupMotif] = {}
    key_moments: list[KeyMoment] = []


class EffectInstruction(BaseModel):
    """A concrete, placeable effect — maps onto an addEffect call."""

    target: str
    effect_type: str
    look_id: str
    palette_id: str | None = None
    palette_colors: list[str] = []     # the brief's section colors (code-applied; override palette_id)
    knob_values: dict[str, str] = {}
    extra_settings: dict[str, str] = {}  # appended settings the look lacks (e.g. synthesized value curves)
    render_style: str = ""               # LLM-chosen buffer style (group-canvas vs per-model); "" → fallback
    layer: int = 0
    start_ms: int
    end_ms: int
    section_index: int | None = None   # which ShowPlan section produced it (for scoped regen/QA)


class SectionEffects(BaseModel):
    """Generator output for one section."""

    instructions: list[EffectInstruction]
