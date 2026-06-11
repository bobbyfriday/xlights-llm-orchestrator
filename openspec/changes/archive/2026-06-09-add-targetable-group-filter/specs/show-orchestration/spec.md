## ADDED Requirements

### Requirement: The planner targets only groups that accept effects
The planner SHALL target only prop groups that the application accepts effects on, so that planned/generated sections are not left empty by un-targetable groups.

#### Scenario: Non-targetable groups are excluded
- **WHEN** the available groups are determined for planning
- **THEN** groups that the application rejects effects on are excluded from what the Director and Generator may target

### Requirement: Targetability is determined empirically and reused per layout
The set of targetable groups SHALL be determined empirically (by testing whether an effect can be placed) and reused across runs for a given prop layout, re-determined only when the layout's groups change.

#### Scenario: Reused across runs
- **WHEN** a second run uses the same layout
- **THEN** the targetable set is reused without re-testing every group

#### Scenario: Layout changed
- **WHEN** the layout's group set changes
- **THEN** the targetable set is re-determined

### Requirement: Fall back to the full group list when targetability is unknown
If targetability cannot be determined (e.g. the probe or the application is unavailable), the system SHALL fall back to using the full group list rather than failing or producing an empty set.

#### Scenario: Probe unavailable
- **WHEN** targetability cannot be determined
- **THEN** the full group list is used (no regression from prior behavior)
