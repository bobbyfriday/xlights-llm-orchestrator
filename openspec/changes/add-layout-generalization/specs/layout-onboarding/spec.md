## ADDED Requirements

### Requirement: Onboard an arbitrary layout with one guided command
The system SHALL provide an `xlo init-layout` command that onboards an arbitrary xLights layout to the `SEM_` semantic vocabulary by analyzing its `rgbeffects.xml`, reviewing low-confidence classifications, writing the `SEM_` groups, emitting a manifest, and validating the result.
The command SHALL run fully deterministically with no LLM key configured (classification steps 1–4), and SHALL NOT require xLights to be running (it requires xLights closed for the write step).

#### Scenario: Deterministic run without an LLM key
- **WHEN** `xlo init-layout` is run against a show folder with no LLM key configured (or `--no-llm`)
- **THEN** props are classified via steps 1–4 (DisplayAs map, tree pixel-count, name heuristics, group hints), the unresolved tail defaults to `CUSTOM_PROP` and enters the review queue, and the command completes without contacting an LLM

#### Scenario: Command does not assume xLights is running
- **WHEN** `xlo init-layout` starts and xLights is not running
- **THEN** the command proceeds (it does not open an `XLightsClient` run session), locating the show folder from `--show-folder` or a prompt rather than requiring the automation port

### Requirement: Props are classified by role from the layout file
The system SHALL classify each model in the default preview into a role by applying, in order, a DisplayAs direct map, a tree pixel-count disambiguation, name-substring heuristics, and user-group name hints, assigning a confidence to each step (1.0 for map/tree, 0.9 for name, 0.85 for group hint, 0.5 for an unresolved `CUSTOM_PROP`).
Each step SHALL touch only props not yet resolved by an earlier step.

#### Scenario: DisplayAs maps directly to a role
- **WHEN** a model's DisplayAs is one of the mapped types (e.g. Arches, Icicles, Candy Canes, Star, Spinner, Matrix, Window Frame)
- **THEN** it is classified to the corresponding role at confidence 1.0

#### Scenario: Tree size disambiguates mega vs mini
- **WHEN** a tree model has at least 600 nodes, or is the sole tree and the layout's largest prop
- **THEN** it is classified `MEGA_TREE`, otherwise `MINI_TREE`

#### Scenario: Name heuristics and group hints resolve the tail
- **WHEN** an unresolved prop's name matches a heuristic substring (e.g. "roof" → OUTLINE) or its user group's name does (e.g. member of "All Outline" → OUTLINE)
- **THEN** it is classified to that role at 0.9 (name) or 0.85 (group hint)

#### Scenario: Unresolved props default to CUSTOM_PROP for review
- **WHEN** no step resolves a prop
- **THEN** it is set to `CUSTOM_PROP` at confidence 0.5 and appears in the review queue, never silently in a group

### Requirement: Capability classes are derived from role and geometry
The system SHALL derive each prop's capability class from its role, node count, and string type rather than from its name — mapping to `2D_SURFACE`, `2D_RADIAL`, `LINEAR_HIGH`, `LINEAR_LOW`, `POINT`, or `SPECIAL`.
A non-RGB string type SHALL override to `POINT` regardless of role, and a very large dense Custom model SHALL be treated as a `2D_SURFACE` matrix.

#### Scenario: Linear props split by node budget
- **WHEN** an OUTLINE or PATH prop has at least 100 nodes
- **THEN** its capability is `LINEAR_HIGH`, otherwise `LINEAR_LOW`

#### Scenario: Non-RGB string overrides to POINT
- **WHEN** a prop has a non-RGB string type
- **THEN** its capability is `POINT` regardless of its role

### Requirement: Spatial fields are derived from world positions
The system SHALL derive each prop's spatial fields — normalized position, band, side, sweep order, mirror partner, center distance, and focal flag — from the models' world positions, excluding outliers before normalization.
Outlier or zero-node models SHALL be excluded from the bounding box and added to review so a parked model does not stretch normalization.

#### Scenario: Outlier is excluded before normalization
- **WHEN** a model sits more than twice the display span outside the main bounding box (or has zero nodes)
- **THEN** it is excluded from the bbox, added to the review list, and does not affect the normalized positions of the other props

#### Scenario: Bands, sides, and sweep order populate
- **WHEN** spatial derivation runs on a multi-instance role
- **THEN** each prop gets a band (GROUND/MID/ROOF at 0.33/0.66), a side (LEFT/CENTER/RIGHT at 0.45/0.55), and members of ordered roles get `sweep_order = 1..N` left-to-right

#### Scenario: Mirror pairs are recorded both ways
- **WHEN** two props of the same role are mirrored around the centerline within tolerance (|x1+x2−1| ≤ 0.05 and |y1−y2| ≤ 0.05)
- **THEN** each prop's `mirror_of` names the other

#### Scenario: Inverted preview is corrected by invert-x
- **WHEN** the layout's preview is horizontally inverted
- **THEN** running with `--invert-x` flips the x axis so sweep order and mirror pairs derive consistently

### Requirement: Low-confidence classifications are reviewed before the manifest is final
The system SHALL present every prop below 0.8 confidence, and every excluded outlier, in a review queue offering the role enum, "accept as CUSTOM_PROP", or "exclude"; unresolved items SHALL remain in the manifest's `review` array and SHALL NOT be written silently into a group.
An unattended run (`--yes`) SHALL accept the suggestions but still record them in `review`, and the command SHALL warn when the manifest ships with a non-empty `review`.

#### Scenario: Low-confidence prop is queued
- **WHEN** a prop is classified below 0.8 confidence
- **THEN** it is offered in the review queue and is recorded in the manifest's `review` array until resolved

#### Scenario: Unattended run records unresolved items
- **WHEN** `--yes` is passed and props remain below 0.8
- **THEN** their suggested roles are accepted, they still appear in the manifest's `review` array, and the command warns that the manifest is not fully reviewed

### Requirement: An optional LLM fallback classifies the unresolved tail
The system SHALL, when an LLM key is configured and `--no-llm` is not set, resolve the unresolved tail with a single batched LLM call whose output role is constrained to the canonical role enum, so an invented role is a schema error rather than a silent bad group.
Any guess below 0.8 confidence, and any prop the LLM does not return, SHALL go to the review queue.

#### Scenario: Batched enum-constrained classification
- **WHEN** the deterministic steps leave an unresolved tail and an LLM key is available
- **THEN** a single batched call classifies the tail with roles drawn only from the canonical enum, and low-confidence or missing guesses route to review

#### Scenario: Fallback is skippable
- **WHEN** `--no-llm` is passed or no LLM key is configured
- **THEN** the unresolved tail defaults to `CUSTOM_PROP` and review, and no LLM call is made

### Requirement: The SEM_ groups are written idempotently with layout modes
The system SHALL write the `SEM_` model groups into `rgbeffects.xml` idempotently — taking a timestamped backup, removing every existing `SEM_`-prefixed group, appending one group per plan entry with its members, grid size, and the §5.7 layout-mode attribute, and replacing the file atomically — while never modifying non-`SEM_` (user) groups.
An unchanged layout SHALL produce a byte-level no-op write (no new backup, no write).

#### Scenario: Groups are regenerated, user groups untouched
- **WHEN** the writer runs on a layout that already has `SEM_` groups and user groups
- **THEN** the `SEM_` groups are deleted and recreated (a stale `SEM_OLD` disappears) and the user groups are left exactly as they were

#### Scenario: Ordered groups get the ordered layout mode
- **WHEN** a group name ends in `_LTR`
- **THEN** its layout-mode attribute is the ordered mode (so a chase traverses members in order), while ensemble groups get the ensemble (Per Preview) mode

#### Scenario: Unchanged layout is a no-op write
- **WHEN** the writer runs on a layout whose serialized `SEM_` subtree already matches the plan
- **THEN** no file is written and no backup is created

### Requirement: The writer refuses to run while xLights is open
The system SHALL refuse to write `rgbeffects.xml` while xLights is running, detecting a running instance by a short-timeout connectivity probe, so xLights cannot clobber the offline edit when it rewrites the file on exit.

#### Scenario: xLights is open
- **WHEN** the write step runs and the automation port answers a version probe
- **THEN** the writer refuses (or waits and polls), instructing the user to close xLights and re-run

### Requirement: A layout manifest is emitted and is version-tolerant
The system SHALL emit a `layout_semantics.json` manifest (under ~10 KB) to the show directory plus a cache copy, describing each prop's role, capability, position, sweep order, mirror partner, focal flag, and confidence, and the group membership with ordering.
Loading the manifest SHALL be tolerant — returning nothing when it is absent or its version does not match.

#### Scenario: Manifest is written to the show folder
- **WHEN** `xlo init-layout` completes the write step
- **THEN** `layout_semantics.json` (< 10 KB) exists in the show directory with per-prop role/capability/position and group membership, plus a cache copy

#### Scenario: Absent or mismatched manifest loads as nothing
- **WHEN** a consumer loads a manifest that is absent or whose version does not match
- **THEN** the load returns nothing and the consumer falls back to its no-manifest behavior

### Requirement: The onboarded groups are validated offline
The system SHALL validate the onboarded layout offline without xLights, by synthesizing role-color and sweep frames, rendering them through the offline preview renderer, and applying a deterministic sweep-centroid check plus structural checks that gate the command; a role-color contact sheet SHALL be written for inspection and, when an LLM key is present, sent to the visual critic as an advisory pass.

#### Scenario: Sweep direction is checked deterministically
- **WHEN** the validator renders an `_LTR` group's sweep frames
- **THEN** the lit-pixel world-x centroid must be strictly increasing across frames; if it decreases, the command recommends `--invert-x`

#### Scenario: Structural checks gate the command
- **WHEN** the validator runs its structural checks
- **THEN** it verifies every `SEM_` member exists as a model, no `SEM_` group is empty, `SEM_ALL` excludes SINGING_FACE/SIGN, and every `_LTR` member order matches its `sweep_order`, failing the command on a violation

#### Scenario: Contact sheet and optional vision pass
- **WHEN** validation renders the role-color frames
- **THEN** a labeled contact sheet PNG is written next to the manifest, and with an LLM key it is sent to the visual critic whose findings are advisory (printed, never auto-mutating)

### Requirement: A dry run diffs the plan against the existing layout without writing
The system SHALL support a `--dry-run` that classifies, derives, plans, and prints a three-way per-group membership diff (only-in-file / only-in-plan / member-order-changed) and the would-be manifest, without writing any file, so the current hand-built layout can be verified to converge.

#### Scenario: Dry run on the converged layout prints an empty diff
- **WHEN** `xlo init-layout --dry-run` runs against the current hand-built layout
- **THEN** it prints an empty (or explained-only) membership diff and does not write `rgbeffects.xml` or the manifest

### Requirement: Per-layout overrides record irreducible judgment calls
The system SHALL apply a per-layout `layout_overrides.json` (mapping a prop name to a forced role) after the deterministic steps and before the LLM step, so a divergence from the convergence golden is fixed by the classifier or an explicit override rather than by weakening the diff.

#### Scenario: An override forces a prop's role
- **WHEN** `layout_overrides.json` maps a prop name to a role
- **THEN** that prop takes the override role after steps 1–4 and before any LLM fallback
