"""Pydantic models for the effect-preset catalog."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Knob(BaseModel):
    """A setting whose value varies across a look's corpus group."""

    model_config = ConfigDict(extra="forbid")

    key: str
    kind: str  # slider | choice | checkbox | text | notebook | button | valuecurve | other
    numeric: bool = False
    min: float | None = None          # sliders
    max: float | None = None          # sliders
    options: list[str] | None = None  # categorical: observed values (verbatim)
    vc_class: str | None = None       # valuecurve: parametric | custom | mixed
    default: str                      # most-frequently observed value


class Look(BaseModel):
    """A parameterized effect look: frozen structure + tunable knobs."""

    model_config = ConfigDict(extra="forbid")

    look_id: str
    effect_type: str
    key_signature: list[str]
    key_order: list[str]              # canonical emission order (frozen + knob keys)
    frozen_base: dict[str, str]       # keys constant across the group
    knobs: list[Knob]
    source_versions: list[str]
    count: int                        # placements observed


class Palette(BaseModel):
    """A deduped color palette (the second, independent axis)."""

    model_config = ConfigDict(extra="forbid")

    palette_id: str
    palette_string: str
    colors: list[str]
    tags: list[str]


class Catalog(BaseModel):
    """The committed catalog: looks by effect type + palettes + provenance meta."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    meta: dict = {}
    looks_by_type: dict[str, list[Look]] = {}
    palettes: list[Palette] = []
