## ADDED Requirements

### Requirement: Render precedence is canonical
Sequence element rows SHALL follow a canonical precedence: ensemble beds first (painted over), then frame/rhythm/role rows, with focal and accent rows last (winning overlaps).

#### Scenario: Bed vs feature overlap
- **WHEN** a bed group and the focal group light the same props
- **THEN** the focal row renders after (over) the bed

### Requirement: The canonical view drives sequence creation when available
A canonical master view SHALL be authored into the layout, and sequence creation SHALL use it when xLights has it loaded, falling back gracefully otherwise.

#### Scenario: View not yet loaded
- **WHEN** the view exists in the file but xLights hasn't restarted
- **THEN** sequence creation proceeds with the default view (no failure) and the finalize reorder still applies
