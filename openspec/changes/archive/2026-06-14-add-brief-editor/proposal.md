## Why

The editable brief (schema-backed `creative_brief.json`) gives dropdowns/validation in VS Code, but raw JSON is still fiddly to edit by hand. The user wants a friendlier surface — dropdowns, multi-selects, color swatches — to edit the per-section creative direction (scenes, palette, effects, look). The enriched schema we already generate is exactly what a form needs; a tiny local browser form turns it into point-and-click editing.

## What Changes

- **Brief editor server (code):** `brief_editor.serve(brief_path)` — a stdlib `http.server` that reads `creative_brief.json` + its sibling `creative_brief.schema.json`, serves a one-page form on localhost, and writes the edited brief back on Save. No framework, no CDN, no new deps.
- **Schema-driven form (code):** the page renders each section from the schema — `enum` fields → dropdowns, array-of-enum fields → multi-select chips (groups, effect_types), `palette` → color rows with name dropdowns + live swatches, `intensity` → a slider, the rest → text/area. Show-level `experience`/`concept` are textareas; advanced nested fields (group_motifs, key_moments, show palette) are preserved untouched on save.
- **Safe save (code):** Save POSTs the whole brief back; the server re-validates it as a `ShowPlan` (ignoring `$schema`), preserves the `$schema` key and every unrendered field, and writes atomically. Invalid edits are rejected with the error shown in the form.
- **CLI (code):** `xlo edit-brief --song <mp3>` (or `--brief <path>`) opens the editor in the browser.

## Capabilities

### New Capabilities

(none — this is an editing surface over the existing brief)

### Modified Capabilities

- `show-orchestration`: the creative brief SHALL be editable through a local browser form (dropdowns/multi-selects/color swatches generated from the brief schema), with edits written back to `creative_brief.json` preserving unrendered fields and the schema reference.

## Impact

- New `brief_editor.py`; `cli.py` (`edit-brief` subcommand). Reads the brief + schema JSON files (no dependency on the schema-generator code), so it works wherever those files exist. Back-compat: additive, read-modify-write of an existing file; a missing schema degrades to a text-only form.
