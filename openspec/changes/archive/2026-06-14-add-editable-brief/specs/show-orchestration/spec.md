## ADDED Requirements

### Requirement: The creative brief is emitted as a schema-backed editable file
When the creative brief is written, the orchestrator SHALL also write a JSON Schema for it (`creative_brief.schema.json`) and reference that schema from `creative_brief.json` via a relative `$schema` key, so a schema-aware editor offers valid choices and validation. The schema SHALL enumerate the run's actual vocabulary — the live layout groups for group fields, placeable effect types for effect fields, cookbook scene IDs for `scene_id`, the song's stems for `follow_stem`, and the named colors for palette fields — and SHALL keep `intensity` bounded to 0–1.

#### Scenario: Schema lists the run's real choices
- **WHEN** the brief is written for a run whose layout has groups G and whose cookbook defines scenes S
- **THEN** the generated schema's group fields enumerate G and its `scene_id` field enumerates S, so an editor offers exactly those choices

#### Scenario: An edited brief is read back unchanged
- **WHEN** the user edits `creative_brief.json` (which carries a `$schema` key) and re-runs
- **THEN** the brief loads as the edited `ShowPlan`, with the `$schema` key ignored, and the run uses the edited values

#### Scenario: A brief without a schema still loads
- **WHEN** a `creative_brief.json` has no `$schema` key
- **THEN** it validates and runs exactly as before
