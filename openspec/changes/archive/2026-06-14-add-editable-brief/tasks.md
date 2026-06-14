## 1. Schema generator

- [x] 1.1 `agents/guide_extracts.py`: `scene_ids()` — sorted unique `SC-NN` from the scene cookbook.
- [x] 1.2 New `brief_schema.py`: `build_brief_schema(*, groups, effect_types, scene_ids, stems, colors)` — `ShowPlan.model_json_schema()` enriched with enums on the constrained fields; `write_editable_brief(show_plan, out_dir, *, vocab...)` writes `creative_brief.schema.json` + `creative_brief.json` (with relative `$schema`).

## 2. Wire into the pipeline

- [x] 2.1 `pipeline/run.py`: use `write_editable_brief` at both brief-write sites (initial + post-refine), sourcing vocab from state (groups, placeable types, scene IDs, stems, named colors).
- [x] 2.2 Design-checkpoint message points at the editable `creative_brief.json` (edit + re-run to apply).

## 3. Tests (hermetic)

- [x] 3.1 `build_brief_schema` puts the given groups/effects/scenes/stems/colors as enums on the right fields; intensity keeps 0–1.
- [x] 3.2 `write_editable_brief` writes both files; `creative_brief.json` has a relative `$schema`; `ShowPlan.model_validate_json` ignores it and yields the same plan.
- [x] 3.3 Full suite passes.

## 4. Verify + land

- [x] 4.1 Live: generate Christmas Canon's brief, open `creative_brief.json` in VS Code, confirm enum dropdowns + validation; edit a field, re-run, confirm it's applied.
- [x] 4.2 Archive, commit, push, open PR (user merges).
