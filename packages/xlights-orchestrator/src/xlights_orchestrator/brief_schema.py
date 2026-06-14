"""Make the creative brief (`ShowPlan`) a schema-backed, human-editable JSON file.

`ShowPlan.model_json_schema()` gives a base schema; we overlay `enum`s drawn from the RUN's actual
vocabulary (live layout groups, placeable effect types, cookbook scene IDs, the song's stems, the
named colors) so a schema-aware editor (VS Code) offers exactly the valid choices, with validation
and hover docs — no custom UI. The models stay plain `str`/`list[str]` (not Literal), so the schema
is advisory: a hand-typed value still loads, and the vocab can vary per run.
"""

from __future__ import annotations

import json
from pathlib import Path

from .show_plan import ShowPlan

SCHEMA_NAME = "creative_brief.schema.json"


def _set_array_enum(props: dict, field: str, values: list[str]) -> None:
    p = props.get(field)
    if isinstance(p, dict) and isinstance(p.get("items"), dict):
        p["items"]["enum"] = list(values)


def _set_scalar_enum(props: dict, field: str, values: list[str]) -> None:
    p = props.get(field)
    if isinstance(p, dict):
        p["enum"] = list(values)


def build_brief_schema(*, groups: list[str], effect_types: list[str], scene_ids: list[str],
                       stems: list[str], colors: list[str]) -> dict:
    """`ShowPlan`'s JSON Schema, enriched with the run's vocabulary as field `enum`s."""
    schema = ShowPlan.model_json_schema()
    defs = schema.get("$defs", {})
    sp = defs.get("SectionPlan", {}).get("properties", {})
    # group fields → the live layout groups
    _set_array_enum(sp, "target_groups", groups)
    _set_array_enum(sp, "pulse_groups", groups)
    # effect fields → placeable effect types
    _set_array_enum(sp, "effect_types", effect_types)
    _set_scalar_enum(sp, "effect_family", effect_types)
    _set_scalar_enum(sp, "accent_effect", [""] + list(effect_types))
    # scene / stem / pulse / palette
    _set_scalar_enum(sp, "scene_id", [""] + list(scene_ids))
    _set_scalar_enum(sp, "follow_stem", [""] + list(stems))
    _set_scalar_enum(sp, "pulse_on", ["", "beat", "onset"])
    _set_array_enum(sp, "palette", colors)
    # show-level palette colors
    _set_array_enum(defs.get("ShowPalette", {}).get("properties", {}), "colors", colors)
    schema["title"] = "Creative Brief (ShowPlan) — edit, then re-run to apply"
    return schema


def write_editable_brief(show_plan: ShowPlan, out_dir, *, groups: list[str], effect_types: list[str],
                         scene_ids: list[str], stems: list[str], colors: list[str]) -> Path:
    """Write `creative_brief.schema.json` + `creative_brief.json` (with a relative `$schema` ref) to
    `out_dir`. Returns the brief path. The `$schema` key is ignored by `ShowPlan.model_validate_json`
    on read (pydantic `extra='ignore'`), so the edited file feeds straight back into the run."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    schema = build_brief_schema(groups=groups, effect_types=effect_types, scene_ids=scene_ids,
                                stems=stems, colors=colors)
    (out / SCHEMA_NAME).write_text(json.dumps(schema, indent=1))
    brief = json.loads(show_plan.model_dump_json())
    brief = {"$schema": SCHEMA_NAME, **brief}            # relative ref; VS Code resolves it sibling
    path = out / "creative_brief.json"
    path.write_text(json.dumps(brief, indent=1))
    return path
