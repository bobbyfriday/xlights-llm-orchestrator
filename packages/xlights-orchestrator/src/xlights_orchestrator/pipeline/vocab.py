"""The song dir's brief vocabulary: `vocab.json` (D6) and the schema derived from it.

`xlo groups` writes `vocab.json` BEFORE any brief exists so Claude (and `validate-brief`) share one
source for what a brief may name: the live layout's targetable groups, the placeable effect
types, the cellable carrier types (for `fabric.carrier`), the cookbook scene ids, the song's
stems, the named colors, and the layer blend methods (for `fabric.blend`). This module takes
those lists as arguments — it never calls xLights or the preset library itself — so it is
hermetic and the values are the caller's to source (`pipeline.groups.targetable_groups`,
`agents.catalog.placeable_effect_types`, `pipeline.effect_meta.DURATION_CELLABLE`,
`agents.guide_extracts.scene_ids`, the analysis' stems,
`xlights_core.knowledge.colors.NAMED_COLORS`, `show_plan.BLEND_METHODS`).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from ..brief_schema import SCHEMA_NAME, build_brief_schema
from ..show_plan import BLEND_METHODS

VOCAB_NAME = "vocab.json"

# The keys of vocab.json, in the order they are written.
VOCAB_KEYS = ("groups", "effect_types", "cellable", "scene_ids", "stems", "colors", "blends")


def _dedupe(values) -> list[str]:
    """Stable-order, unique, stringified, blanks dropped."""
    out: list[str] = []
    seen: set[str] = set()
    for v in values or []:
        s = str(v).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def build_vocab(*, groups, effect_types, cellable, scene_ids, stems, colors,
                blends=BLEND_METHODS) -> dict:
    """Assemble the vocabulary dict. Order is preserved for groups (the layout's own order is
    meaningful to a reader) and blends (xLights' menu order); the type/scene/stem/color lists
    are sorted for a stable file. `cellable` is intersected with `effect_types` — a carrier
    must also be placeable. `blends` defaults to the contract's `BLEND_METHODS`."""
    types = sorted(_dedupe(effect_types))
    placeable = set(types)
    return {
        "groups": _dedupe(groups),
        "effect_types": types,
        "cellable": sorted(t for t in _dedupe(cellable) if t in placeable),
        "scene_ids": sorted(_dedupe(scene_ids)),
        "stems": _dedupe(stems),
        "colors": _dedupe(colors),
        "blends": _dedupe(blends),
    }


def write_vocab(song_dir, vocab: dict) -> Path:
    """Write `vocab.json` under the song dir; returns its path."""
    out = Path(song_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / VOCAB_NAME
    path.write_text(json.dumps({k: list(vocab.get(k, [])) for k in VOCAB_KEYS}, indent=1))
    return path


def load_vocab(song_dir) -> dict:
    """Read `vocab.json` from the song dir. Missing keys come back as empty lists so a validator
    can run against an older file; a missing file raises `FileNotFoundError` (the caller names
    the prerequisite: run `xlo groups`)."""
    data = json.loads((Path(song_dir) / VOCAB_NAME).read_text())
    return {k: list(data.get(k, [])) for k in VOCAB_KEYS}


def schema_from_vocab(vocab: dict) -> dict:
    """`ShowPlan`'s JSON Schema with the vocab as field enums. Passes `cellable=` to
    `build_brief_schema` only when that kwarg exists (lane A adds it with the `fabric` block),
    so this works on either side of that change."""
    kwargs = dict(groups=list(vocab.get("groups", [])),
                  effect_types=list(vocab.get("effect_types", [])),
                  scene_ids=list(vocab.get("scene_ids", [])),
                  stems=list(vocab.get("stems", [])),
                  colors=list(vocab.get("colors", [])))
    if "cellable" in inspect.signature(build_brief_schema).parameters:
        kwargs["cellable"] = list(vocab.get("cellable", []))
    return build_brief_schema(**kwargs)


def write_brief_schema(song_dir, vocab: dict) -> Path:
    """Write `creative_brief.schema.json` (from the vocab) under the song dir; returns its path."""
    out = Path(song_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / SCHEMA_NAME
    path.write_text(json.dumps(schema_from_vocab(vocab), indent=1))
    return path


def write_vocab_and_schema(song_dir, vocab: dict) -> tuple[Path, Path]:
    """The `xlo groups` file contract: `(vocab.json path, creative_brief.schema.json path)`."""
    return write_vocab(song_dir, vocab), write_brief_schema(song_dir, vocab)
