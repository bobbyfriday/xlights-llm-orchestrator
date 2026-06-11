## ADDED Requirements

### Requirement: Design-implicated defects escalate to a design revision
When a section's objective violations implicate the brief's own choices (or persist after regeneration), the loop SHALL revise that section's design before regenerating, rather than re-realizing the flawed design.

#### Scenario: Brief-chosen effect violates the rules
- **WHEN** a rules violation names an effect type that the section's brief specifies
- **THEN** the section design is revised (violation text in hand) and generation realizes the new design

#### Scenario: Bounded
- **WHEN** a section has already been redesigned this run
- **THEN** it is not redesigned again (regeneration only)

### Requirement: The corrected design persists
A design revised during refinement SHALL be written back to the design cache at finalize.

#### Scenario: Re-run keeps the fix
- **WHEN** a later run loads the cached design
- **THEN** it contains the revised sections
