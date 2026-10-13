## MODIFIED Requirements

### Requirement: Produce a show plan from a song analysis
The system SHALL provide what is needed for a `ShowPlan` (the creative brief) to be authored in a Claude Code conversation from the analysis digest and the brief vocabulary: a schema enumerating the run's real choices, a validator that reports actionable errors, and skills carrying the craft guides. The plan assigns, per song section, a creative intent (target prop groups, effect family, intensity, treatment, palette, optional scene and fabric). No Director agent SHALL be invoked by the system.

#### Scenario: Plan covers the song
- **WHEN** a brief is authored for a song and validated
- **THEN** it has one or more sections covering the song, each naming target groups and an intent

#### Scenario: Plan targets valid groups
- **WHEN** the brief is validated
- **THEN** every target is a prop group the validator knows to be targetable in the current layout, or the validator reports the offending path

### Requirement: Generate placeable effect instructions
The system SHALL turn each section of the `ShowPlan` into validated effect instructions — each selecting a preset look, knob values, palette, target, layer, and time range — assembled deterministically through the preset library so the settings are valid by construction. No per-section generation agent SHALL be invoked.

#### Scenario: Instructions are assembled from presets
- **WHEN** `realize` produces instructions for a section
- **THEN** each instruction references a preset look/palette and assembles to a valid settings string (out-of-range knob values are rejected)

#### Scenario: Same brief, same instructions
- **WHEN** `realize` runs twice on an unchanged brief and analysis
- **THEN** the instruction sets are identical

### Requirement: Orchestrate as a resumable pipeline
The system SHALL expose the stages — analyze, groups, validate-brief, realize, apply, qa, stills, finalize — as independent commands over the song's cache dir, so that any stage can be re-run from the files the earlier stages left behind.

#### Scenario: End-to-end run
- **WHEN** the stages are run in order for a song
- **THEN** the run proceeds analyze → design (conversation) → realize → apply → finalize and ends with a saved sequence

#### Scenario: Resume after interruption
- **WHEN** a session is interrupted after the brief is written
- **THEN** `realize` and later stages run from the cached brief without re-analysis or re-design

### Requirement: Run without live services for testing
The system SHALL allow `realize`, `qa`, and the digest to run from fixture files (a cached analysis and a hand-written brief) with no running xLights and no model API, so the realization layers can be exercised hermetically.

#### Scenario: Fixture brief
- **WHEN** the golden fixture analysis and brief are realized in a test
- **THEN** the full realization produces effect instructions without contacting xLights or any model provider

### Requirement: Human review of the creative brief before generation
The creative brief SHALL be presented to the user in plain language in the conversation after it validates, and the user SHALL be able to request changes before `realize` runs. There SHALL be no unattended mode that skips this.

#### Scenario: Attended review
- **WHEN** the brief validates
- **THEN** the user sees the section-by-section description and may ask for edits before realization

### Requirement: Effect generation follows the creative brief
Realization SHALL follow the creative brief — a section's effects reflect its assigned palette, group roles/motifs, effect direction, treatment, scene, and fabric fields.

#### Scenario: Realization reflects the brief
- **WHEN** a section is realized
- **THEN** its instructions use that section's palette and effect types, its treatment's layer set, and its fabric fields where given

### Requirement: Sequencing agents apply a best-practices guide
The sequencing guides (sequencing, effects catalog, layering) SHALL reach Claude through project-local skills that read the guide files, so that the design conversation applies them.

#### Scenario: Guide present
- **WHEN** `/xlo:design` runs with the guide files present
- **THEN** the loaded skills direct Claude to read them and the brief reflects their rules

### Requirement: Sections are woven from beat-quantized cell recipes
Section realization SHALL realize sections as short, beat-quantized effect cells expanded deterministically from per-section cell recipes. The recipes SHALL be derived by code from the brief: the `fabric` fields (carrier, alternation, cell length in beats, blend) when present, otherwise the deterministic fallback weave (a motion-effect beat carrier over the rhythm groups plus a sparse texture from the section's effect types). Cell timing SHALL snap to the section's real beat grid.

#### Scenario: Brief fabric expands into beat-snapped cells
- **WHEN** a section's brief names a carrier and alternation (e.g. a SingleStrand ping-pong over the rhythm groups at 2 beats per cell)
- **THEN** the pipeline emits one effect instruction per cell slot, with boundaries on the section's beat times, targets rotating across the groups per the alternation, and the section palette realized per cell

#### Scenario: Fallback weave when the brief gives no fabric
- **WHEN** a section's brief carries no fabric block
- **THEN** the deterministic default weave is expanded, and realization never fails for lack of recipes

#### Scenario: Cell settings carry blend, curve, and transition keys
- **WHEN** a fabric block specifies a blend, or code assigns a motion curve or transition
- **THEN** the realized cells carry those settings keys

### Requirement: Sections compose from cookbook scenes
The brief MAY name a cookbook scene (or be explicitly freeform) per section with an archetype-to-group casting, chosen by Claude under the scenes skill, and realization SHALL realize the chosen scene's stack.

#### Scenario: Scene chosen
- **WHEN** a section's brief names a scene
- **THEN** the validator confirms the scene id and realization places its stack on the cast groups

#### Scenario: Freeform allowed
- **WHEN** no scene fits a section
- **THEN** the section may be freeform (empty scene id) and realization proceeds from the fabric and effect types

### Requirement: Placement-rule violations gate the loop
Texture-on-linear-prop, energy-band-mismatch, and overlapping-feature violations SHALL be detected as findings in `qa.json` naming the section and the violation, so the user and Claude can revise the brief. They SHALL NOT gate any stage.

#### Scenario: Texture on a linear prop
- **WHEN** a texture effect targets an arch/outline group
- **THEN** a finding names the section and the violation

#### Scenario: Energy mismatch
- **WHEN** an effect's energy band is far from its section's energy
- **THEN** a finding is raised

#### Scenario: Two features at once
- **WHEN** two high-attention effects overlap in time
- **THEN** a finding is raised

### Requirement: Entrances surface to the planner
Detected instrument entrances SHALL appear in the analysis digest with their timestamps so the design conversation can turn them into key moments.

#### Scenario: Entrance in digest
- **WHEN** an entrance is detected
- **THEN** the digest lists it with its time and instrument

### Requirement: The creative brief is emitted as a schema-backed editable file
Before the brief exists, `xlo groups` SHALL write a JSON Schema for it (`creative_brief.schema.json`) enumerating the run's actual vocabulary — the live layout groups for group fields, placeable effect types for effect fields, cellable types for `fabric.carrier`, cookbook scene IDs for `scene_id`, the song's stems for `follow_stem`, and the named colors for palette fields — keeping `intensity` bounded to 0–1. The brief Claude writes SHALL reference that schema via a relative `$schema` key so a schema-aware editor offers valid choices.

#### Scenario: Schema lists the run's real choices
- **WHEN** the schema is written for a run whose layout has groups G and whose cookbook defines scenes S
- **THEN** its group fields enumerate G and its `scene_id` field enumerates S

#### Scenario: An edited brief is read back unchanged
- **WHEN** the user edits `creative_brief.json` (which carries a `$schema` key) and runs `realize`
- **THEN** the brief loads as the edited `ShowPlan`, with the `$schema` key ignored

#### Scenario: A brief without a schema still loads
- **WHEN** a `creative_brief.json` has no `$schema` key
- **THEN** it validates and realizes exactly the same

## REMOVED Requirements

### Requirement: Agent roles are routable to different model providers
**Reason**: There are no agent roles; Claude Code performs the judgment in conversation.
**Migration**: Delete the model registry and `config.yaml`; remove `XLO_PROVIDER` and per-role model env vars from `.env.example`.

### Requirement: The Generator chooses each effect's render style
**Reason**: The Generator is removed; render style comes from the per-effect fallback (`fallback_style`).
**Migration**: None for users; `render_style` on an instruction is now always code-chosen.

### Requirement: Render style is iterable in the refine loop
**Reason**: There is no refine loop.
**Migration**: None.

### Requirement: Design-implicated defects escalate to a design revision
**Reason**: Revisions are made by editing the brief in conversation.
**Migration**: None.

### Requirement: The corrected design persists
**Reason**: The brief is the design and is the file being edited; persistence is inherent.
**Migration**: None.

### Requirement: Refined instructions persist
**Reason**: There is no refine step; `instructions.json` is always the output of the last `realize`.
**Migration**: None.

### Requirement: The per-section generator is prompted with bounded guide extracts
**Reason**: The Generator and the guide-extract slicer are removed.
**Migration**: Delete `agents/guide_extracts.py`; skills read the full guide files.

### Requirement: The refine loop stops on a plateau
**Reason**: There is no refine loop.
**Migration**: None.

### Requirement: The creative brief is editable via a local browser form
**Reason**: The conversation (and a schema-aware editor) is the editing surface.
**Migration**: Delete `brief_editor.py` and `xlo edit-brief`; edit the brief by asking Claude or in VS Code.

### Requirement: Music-interpretation agents do not receive the guide
**Reason**: There are no music-interpretation agents.
**Migration**: None.
