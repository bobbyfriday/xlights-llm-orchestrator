## ADDED Requirements

### Requirement: The creative brief is editable via a local browser form
The orchestrator SHALL provide a local browser form that edits the creative brief using widgets generated from the brief schema — dropdowns for enum fields, multi-selects for array-of-enum fields, color swatches for the palette, a slider for intensity — and writes edits back to `creative_brief.json`. The save SHALL preserve the `$schema` reference and every field the form does not render, and SHALL reject a structurally invalid edit without writing.

#### Scenario: Edit a section's scene and palette via widgets
- **WHEN** the user opens the brief editor and changes a section's scene (dropdown) and palette (color rows)
- **THEN** Save writes those changes to `creative_brief.json` while leaving unrendered fields (e.g. group_motifs) and the `$schema` key intact

#### Scenario: Invalid edit is rejected
- **WHEN** a save would produce a brief that is not a valid ShowPlan
- **THEN** the server rejects it with an error shown in the form and does not overwrite the file

#### Scenario: Launch from the CLI
- **WHEN** the user runs `xlo edit-brief --song <mp3>` (or `--brief <path>`)
- **THEN** the editor serves that song's cached brief and opens it in the browser
