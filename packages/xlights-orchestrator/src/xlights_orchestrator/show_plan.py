"""Pydantic contracts: SongAnalysis -> ShowPlan -> EffectInstruction[]."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

# The realization-layer provenance vocabulary for EffectInstruction.source (I7 attribution,
# report-only; excluded from model_dump so cache/golden formats stay byte-identical).
EFFECT_SOURCES = ("weave", "accents", "bed", "triggers", "flash", "generator", "vu", "composite",
                  "scene")

# The brief's fabric vocabulary (claude-driven-orchestration D3). Kept here, beside the contract,
# so the schema (brief_schema) and the weaver (pipeline/weave) enumerate the SAME values.
FABRIC_ALTERNATIONS = ("chase", "pingpong", "all", "sparse")   # CellRecipe.alternation
# How often directional effects turn (pipeline/motion): one way all section, every phrase, bar, beat.
DIRECTION_CHANGES = ("hold", "phrase", "bar", "beat")
# xLights `T_CHOICE_LayerMethod` values (the layer blend/mix types), community-corpus-ordered:
# the ones our looks/composites actually carry first, then the rest of xLights' menu.
BLEND_METHODS = (
    "Normal", "Max", "Brightness", "Layered", "Average", "Additive", "Subtractive",
    "1 is Mask", "1 is Unmask", "1 is True Unmask", "2 is Mask", "2 is Unmask", "2 is True Unmask",
    "1 reveals 2", "2 reveals 1", "Effect 1", "Effect 2", "Shadow 1 on 2", "Shadow 2 on 1",
    "Bottom-Top", "Left-Right", "Min", "Highlight", "Highlight Vibrant", "Canvas",
)


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
    text: str = ""                           # kind "lyric": the lyric line/word this moment refers to —
                                             #   the matrix caption (snapped to the aligned lyric line;
                                             #   dropped when no aligned line matches). "" otherwise.


class SectionFabric(BaseModel):
    """The brief's optional per-section fabric knobs (D3): the few CellRecipe fields with a
    visible, nameable effect on the show. Every field is optional — "" / None means "code
    chooses" (today's deterministic fallback weave), so an absent block realizes identically."""

    carrier: str = ""                        # a CELLABLE effect type for the beat carrier (e.g. SingleStrand)
    alternation: str = ""                    # chase | pingpong | all | sparse ("" = chase)
    cell_beats: int | None = Field(default=None, ge=1, le=8)   # carrier cell length in beats
    blend: str = ""                          # T_CHOICE_LayerMethod on the carrier cells ("" = code default)
    direction_change: str = ""               # hold | phrase | bar | beat ("" = by energy; pipeline/motion)
    mirror: bool | None = None               # right-hand groups move opposite the left (None = on)


STACK_ROLES = ("bed", "carrier", "feature", "overlay", "mask", "accent")
STACK_TWINS = ("", "mirror", "counter", "flip", "color")
STACK_DIRECTIONS = ("", "ltr", "rtl", "up", "down", "bounce", "alternate", "center_out", "center_in", "vary")
STACK_ALTERNATIONS = ("", "all", "chase", "pingpong", "sparse")
BUFFER_TRANSFORMS = ("", "None", "Rotate CC 90", "Rotate CW 90", "Rotate 180", "Flip Vertical",
                     "Flip Horizontal", "Rotate CC 90 Flip Horizontal", "Rotate CW 90 Flip Horizontal")
STACK_CELL_BEATS_RANGE = (0, 16)


class StackLayer(BaseModel):
    """One authored layer of a section's STACK (the xlo-effects skill's vocabulary): what the
    designer decided, placed by code without the synthesized weave/composites in the way.

    Layers are listed bottom → top. Each becomes one row per group (held for the section) or
    one row per beat cell (`cell_beats` > 0), plus a second row for a `twin`."""

    effect_type: str
    role: str = "feature"                    # bed | carrier | feature | overlay | mask | accent
    groups: list[str] = []                   # [] → the section's target_groups
    look_id: str = ""                        # a catalog look (vocab `looks`); "" → the picker
    knobs: dict[str, str] = {}               # knob values on the look (validated against it)
    settings: dict[str, str] = {}            # extra settings verbatim: value curves, blur, sparkles,
                                             #   transitions… (blend/transform/fades have fields)
    direction: str = ""                      # ltr | rtl | up | down | bounce | alternate |
                                             #   center_out | center_in | vary | "" (effect default)
    blend: str = ""                          # T_CHOICE_LayerMethod over the layer below ("" = Normal)
    transform: str = ""                      # B_CHOICE_BufferTransform ("" = none)
    render_style: str = ""                   # buffer style; "" → the per-effect fallback
    palette: list[str] = []                  # this layer's colors; [] → the section palette, rotated
    cell_beats: int = Field(default=0, ge=0, le=16)   # 0 = hold the section; N = re-cut every N beats
    alternation: str = ""                    # which groups a cell lights: all (default) | chase |
                                             #   pingpong | sparse
    twin: str = ""                           # "" | mirror (Rotate 180) | counter (direction reversed,
                                             #   twist/rotation negated) | flip (Flip Horizontal) |
                                             #   color (next palette rotation) → a second row above
    fade_in: float = Field(default=0.0, ge=0, le=10)
    fade_out: float = Field(default=0.0, ge=0, le=10)
    brightness: float | None = Field(default=None, ge=0, le=4)   # 1.0 = normal


class SectionPlan(BaseModel):
    """Per-section creative direction over prop groups (plain `look` + grounded direction)."""

    start_ms: int
    end_ms: int
    label: str = ""                          # the section's musical label ("verse 1", "chorus", "bridge");
                                             #   blank allowed. Recurring labels (chorus 1/2) rhyme: see
                                             #   repetition_map_from_labels.
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
    scene_adaptation: str = ""               # prose: which real groups play the scene's archetype rows
    scene_cast: dict[str, str] = {}          # the machine cast: archetype row id → real group name
                                             #   ({"G2-HERO": "SEM_FOCAL", "G2-RHYTHM": "SEM_ARCHES"});
                                             #   {} with a scene_id → pipeline/scenes.default_cast by role
    # -- rhythmic intent (beat layer; all defaulted/back-compat) --
    pulse_groups: list[str] = []             # groups that punctuate the beat (default 04_BEAT_*)
    follow_stem: str = ""                    # whose rhythm to ride (default the prominent stem)
    accent_effect: str = ""                  # placeable punctuation effect (default On)
    pulse_on: str = ""                       # "beat" | "onset" (default beat)
    # -- fabric intent (claude-driven-orchestration D3; additive, None → code chooses) --
    fabric: SectionFabric | None = None      # carrier / alternation / cell_beats / blend knobs
    # -- the authored stack (xlo-effects; additive, [] → code synthesizes as before) --
    stack: list[StackLayer] = []             # bottom → top; replaces the weave, composites, phrase
                                             #   gesture, VU and final layer for this section; beat
                                             #   accents still run unless a layer's role is "accent"


_LABEL_TAIL = re.compile(r"[\s\d#_-]+$")   # "chorus 2" / "verse-1" / "chorus #3" → the bare label


def normalize_label(label: str) -> str:
    """A section label's musical IDENTITY: lowercase, trimmed, trailing digits/separators dropped
    ("Chorus 1" and "chorus 2" → "chorus"). "" for a blank label."""
    return _LABEL_TAIL.sub("", (label or "").strip().lower()).strip()


def repetition_map_from_labels(sections) -> dict[str, list[int]]:
    """Derive the repetition map (identity → recurring section indices) from the sections' own
    `label` values — what the realization rhymes recurring sections on. Only
    identities with ≥ 2 occurrences are kept (a one-off has no rhyme partner); blank labels are
    ignored; key order follows first occurrence, so the result is deterministic."""
    by_label: dict[str, list[int]] = {}
    for i, sec in enumerate(sections or []):
        key = normalize_label(getattr(sec, "label", "") or "")
        if key:
            by_label.setdefault(key, []).append(i)
    return {k: v for k, v in by_label.items() if len(v) >= 2}


class ShowPlan(BaseModel):
    sections: list[SectionPlan]
    # -- creative brief (additive) --
    experience: str = ""                     # PLAIN-language audience vision (leads the brief; no theory)
    concept: str = ""                        # the artistic concept
    palette: ShowPalette | None = None
    group_motifs: dict[str, GroupMotif] = {}
    key_moments: list[KeyMoment] = []
    triggers_off: list[str] = []             # cookbook trigger names (`## ` headings, any case) to
                                             # skip for THIS song; the cookbook stays shared


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
    section_index: int | None = None   # which ShowPlan section produced it (for per-section QA)
    on_top: bool = False               # a punch-through accent (trigger): top layer, opaque,
                                       # exempt from the layer-budget clamp so it always shows
    source: str = Field(default="", exclude=True)   # I7: which realization layer emitted this row
                                       #   (weave/accents/bed/…); TRANSIENT — excluded from model_dump
                                       #   so the instructions cache/golden stay byte-identical. Surfaced
                                       #   only in the fabric-measurement report (per-type-per-source).
    directed: bool = Field(default=False, exclude=True)   # TRANSIENT: a direction was set on purpose
                                       #   (weave/composite/counter-rotation/motion) — later passes keep it.


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
    """One section's designed effects: base rows (+ an optional weave / composites) that
    `realize_section_effects` layers the deterministic realization over."""

    instructions: list[EffectInstruction]
    weave: SectionWeave | None = None        # cell recipes (additive; None → no woven fabric)
    composites: list[CompositeRecipe] = []   # multi-effect blended stacks on a group (additive)
