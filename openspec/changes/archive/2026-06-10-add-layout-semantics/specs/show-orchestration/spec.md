## ADDED Requirements

### Requirement: Semantic role/ensemble groups exist in the layout
The layout SHALL contain semantic groups (`SEM_*`) derived from each model's role, spatial band/side, sweep order, and ensemble membership, generated from `rgbeffects.xml`.

#### Scenario: Role and ensemble groups
- **WHEN** the layout is processed
- **THEN** role groups (e.g. `SEM_ARCHES`), band/side groups, ordered `_LTR` groups, and ensemble groups (`SEM_ALL`, `SEM_FOCAL`, `SEM_ACCENTS`, `SEM_HOUSE`, `SEM_YARD`) are present

### Requirement: A layout manifest is emitted
A `layout_semantics.json` manifest SHALL be written describing each prop's role, capability, position, and the groups, for the planner to consume.

#### Scenario: Manifest written
- **WHEN** the generator runs
- **THEN** `layout_semantics.json` is written with per-prop role/res/pos and the group membership

### Requirement: The planner targets semantic groups
The planner SHALL target `SEM_*` groups (roles/ensembles) rather than the removed numbered taxonomy.

#### Scenario: Whole-display ensemble
- **WHEN** a high-energy section wants the full display
- **THEN** it can target the `SEM_ALL`/ensemble group

### Requirement: Layout edits are safe and idempotent
Editing the layout SHALL back up the file first, be idempotent (re-running replaces only `SEM_` groups), and leave non-numbered user groups untouched.

#### Scenario: Re-run
- **WHEN** the generator runs twice
- **THEN** the `SEM_` groups are replaced (not duplicated) and the plain user groups are unchanged
