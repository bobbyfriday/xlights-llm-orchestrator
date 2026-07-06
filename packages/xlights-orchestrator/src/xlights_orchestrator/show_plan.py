"""Pydantic contracts: SongAnalysis -> ShowPlan -> EffectInstruction[]."""

from __future__ import annotations

from pydantic import BaseModel, Field

# The realization-layer provenance vocabulary for EffectInstruction.source (I7 attribution,
# report-only; excluded from model_dump so cache/golden formats stay byte-identical).
EFFECT_SOURCES = ("weave", "accents", "bed", "triggers", "flash", "generator", "vu", "composite")


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
    phrasing: str = ""                       # "legato" (soft, evolving edges) | "staccato" (crisp on/off)
                                             #   | "" (default from intensity) — the cell soft-edge character
    treatment: str = ""                      # texture archetype controlling which realization LAYERS are
                                             #   included (withheld, not just dimmed): "full" (everything) |
                                             #   "pulse" (bed+accents+feature, no weave/composite) |
                                             #   "feature" (dim bed + one hero, sparse accents) |
                                             #   "gesture" (one carrier recipe on ≤2 groups, nothing else) |
                                             #   "rest" (dim bed on ≤2 groups) | "" → energy-based fallback.
                                             #   Defaulted "" so old cached plans validate (back-compat).
    # -- scene intent (cookbook; additive) --
    scene_id: str = ""                       # cookbook scene this section realizes (e.g. "SC-01"); "" = freeform
    scene_adaptation: str = ""               # which real groups play the scene's archetype rows (hero/rhythm/...)
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
    direct_settings: str = ""            # F-B asset-bound path: a code-built settings string (Text/Faces).
                                         #   When set, the emitter bypasses the preset catalog entirely and
                                         #   look_id may be ""; NEVER surfaced to a generator prompt.
    render_style: str = ""               # LLM-chosen buffer style (group-canvas vs per-model); "" → fallback
    layer: int = 0
    start_ms: int
    end_ms: int
    section_index: int | None = None   # which ShowPlan section produced it (for scoped regen/QA)
    on_top: bool = False               # a punch-through accent (trigger): top layer, opaque,
                                       # exempt from the layer-budget clamp so it always shows
    source: str = Field(default="", exclude=True)   # I7: which realization layer emitted this row
                                       #   (weave/accents/bed/…); TRANSIENT — excluded from model_dump
                                       #   so the instructions cache/golden stay byte-identical. Surfaced
                                       #   only in the fabric-measurement report (per-type-per-source).


class CellRecipe(BaseModel):
    """One cell DESIGN the deterministic weaver repeats across a section's beat grid.

    The LLM designs ~3–6 of these per section (the judgment); code expands them into the
    hundreds of beat-snapped cells (the realization) — community fabric is ~12× reuse per design.
    """

    effect_type: str
    look_id: str = ""                        # "" → first candidate look for the type
    render_style: str = ""                   # buffer style; "" → fallback per effect
    role: str = "texture"                    # carrier | texture | accent | bed
    groups: list[str] = []                   # the alternation set (real targetable groups)
    cell_beats: int = Field(default=1, ge=1, le=8)   # cell length in beats (1|2|4 typical)
    alternation: str = "chase"               # chase | pingpong | all | sparse
    direction: str = ""                      # ltr|rtl|bounce|center_out|center_in|up|down
                                             #   (realized via the EFFECT'S own settings)
    blend: str = ""                          # T_CHOICE_LayerMethod value ("" = Normal)
    motion_curve: str = ""                   # logical curve name (rotation/twist/radius/...)
    transition: str = ""                     # in/out transition type (e.g. "Wipe")
    palette: list[str] = []                  # cell colors; [] → the section palette


class SectionWeave(BaseModel):
    """The section's cell fabric: a few designs the weaver expands beat-by-beat."""

    cells: list[CellRecipe] = []


class CompositeLayer(BaseModel):
    """One layer of a composite stack (index 0 = base/bottom; higher = stacked above)."""

    effect_type: str
    look_id: str = ""                        # "" → first candidate look for the type
    direction: str = ""                      # the effect's own motion direction (counter-phases per layer)
    motion_curve: str = ""                   # logical curve name ramped over the span
    blend: str = ""                          # T_CHOICE_LayerMethod over the layer below ("" = Normal)
    palette: list[str] = []                  # this layer's colors; [] → rotated section palette


class CompositeRecipe(BaseModel):
    """A multi-effect STACK on the SAME group(s): 2–3 effects on blended layers that COMBINE into
    one rich, kaleidoscopic look (e.g. two counter-moving Morphs blended Max). Code expands it into
    stacked EffectInstructions sharing a target + span; the LLM may emit these, or code synthesizes
    one from the curated set for a feature moment."""

    groups: list[str] = []                   # the group(s) the stack lights (each gets the full stack)
    layers: list[CompositeLayer] = []        # 2–3 layers, base first


class SectionEffects(BaseModel):
    """Generator output for one section."""

    instructions: list[EffectInstruction]
    weave: SectionWeave | None = None        # cell recipes (additive; None → no woven fabric)
    composites: list[CompositeRecipe] = []   # multi-effect blended stacks on a group (additive)
