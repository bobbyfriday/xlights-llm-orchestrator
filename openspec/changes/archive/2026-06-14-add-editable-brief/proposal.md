## Why

The director's creative brief is the show's plan, and the user wants to review/edit it and sign off before effects are generated. The brief already round-trips through `creative_brief.json` (the cached `ShowPlan` the pipeline reads back) — editing it and re-running already works — but raw JSON editing is error-prone: no list of valid groups/effects/scenes/colors, no validation, easy to typo a group name or an out-of-range intensity.

`ShowPlan` is a pydantic model, so we get a JSON Schema for free. Enriching that schema with the run's actual vocabulary (the live layout groups, placeable effect types, cookbook scene IDs, the song's stems, the named-color palette) turns `creative_brief.json` into a guided edit in any schema-aware editor (VS Code especially): enum dropdowns, autocomplete, hover docs, inline validation, and color-name completion — with zero custom UI.

## What Changes

- **Brief schema generator (code):** `brief_schema.build_brief_schema(...)` returns `ShowPlan`'s JSON Schema enriched with `enum`s drawn from runtime vocab — `target_groups`/`pulse_groups` → live groups, `effect_family`/`effect_types`/`accent_effect` → placeable types, `scene_id` → cookbook scene IDs, `follow_stem` → the song's stems, `pulse_on` → beat/onset, section + show `palette` → named colors. Intensity keeps its 0–1 bounds.
- **Editable brief emit (code):** when the brief is written, also write `creative_brief.schema.json` beside it and add a relative `"$schema": "creative_brief.schema.json"` key to `creative_brief.json`. The pipeline ignores the extra key on read (pydantic `extra='ignore'`), so the edited file feeds straight back in.
- **Scene-ID list (code):** `scene_ids()` parses the scene cookbook for `SC-NN` IDs (the `scene_id` enum source).
- **Sign-off pointer (code):** the design checkpoint message points at the editable `creative_brief.json` so the user knows where to edit and that re-running applies it.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: the creative brief SHALL be emitted as a schema-backed, human-editable `creative_brief.json` (a generated JSON Schema enumerating the run's valid groups/effects/scenes/stems/colors), and an edited brief SHALL be read back unchanged apart from the ignored `$schema` key.

## Impact

- New `pipeline`/agent module `brief_schema.py`; `agents/guide_extracts.py` (`scene_ids`); `pipeline/run.py` (emit schema + `$schema`; checkpoint message). Back-compat: the `$schema` key is ignored on load; a brief with no schema file still validates.
