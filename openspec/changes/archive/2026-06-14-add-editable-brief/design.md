## Context

`creative_brief.json` is the cached `ShowPlan` the pipeline reads back (`ShowPlan.model_validate_json`). Editing it + re-running already applies the edit — the gap is editor ergonomics. `ShowPlan.model_json_schema()` gives a base schema; the constrained fields (groups, effect types, scenes, stems, colors) are layout/cookbook/song-dependent, so their valid values must be injected at runtime, not hardcoded as Literals.

## Goals / Non-Goals

**Goals:** a schema-backed `creative_brief.json` that gives dropdowns + validation in a schema-aware editor with no custom UI; the edited file feeds straight back into the run. **Non-Goals:** a GUI/browser form with true color-picker swatches (that's the additive "option 2", shares this same schema); a new `xlo plan` command (the edit→re-run loop already works via the cache); post-render review tooling.

## Decisions

**D1 — Runtime-enriched schema, not Literal types.** Build from `ShowPlan.model_json_schema()` and overlay `enum` arrays from the run's vocab: `target_groups`/`pulse_groups` → `available_groups`; `effect_family`/`effect_types` → placeable types; `accent_effect` → placeable types; `scene_id` → `[""] + scene_ids()`; `follow_stem` → `[""] + stem names`; `pulse_on` → `["", "beat", "onset"]`; `SectionPlan.palette` and `ShowPalette.colors` items → named colors. Keeping the models as plain `str`/`list[str]` (not `Literal`) means the schema stays advisory — a hand-typed value still loads — and the vocab can vary per run.

**D2 — `$schema` as a relative ref, ignored on read.** Write `creative_brief.schema.json` in the same dir and inject `"$schema": "creative_brief.schema.json"` as the first key of `creative_brief.json`. VS Code resolves a relative `$schema` against the file's directory. On load, pydantic's default `extra='ignore'` drops the key — verified by test — so no read-path change is needed.

**D3 — Editor target = VS Code (option 1).** A JSON file with `$schema` gives enum dropdowns, autocomplete, hover descriptions (from the pydantic field docs), and validation squiggles for free. Color fields become name dropdowns (from the 54-color vocab); true color-picker swatches need the browser form (option 2), noted as a follow-up that reuses this schema.

**D4 — One emit path.** A `write_editable_brief(show_plan, out_dir, *, vocab...)` helper writes both files; `run.py` calls it everywhere the brief is persisted (initial write + post-refine), so the schema and `$schema` never drift from the brief.

## Risks / Trade-offs

- [A model gains `extra='forbid'` later → `$schema` would break load] → covered by a test asserting an edited brief with `$schema` round-trips; if that ever changes, the test fails loudly.
- [Schema property paths shift if `ShowPlan` is refactored] → the enrich step looks up `$defs`/`properties` defensively (skips a missing field) and a test asserts the key enums are present, catching a drift.
- [Color dropdown ≠ true picker] → accepted for option 1; option 2 (browser form) adds swatches on the same schema.

## Migration Plan

Additive. Existing briefs without a schema file still load. Branch `change/add-editable-brief`, PR (user merges).

## Open Questions

- Whether to surface the brief at a friendlier path than the cache dir (a future `xlo plan --edit` could copy it out); deferred.
