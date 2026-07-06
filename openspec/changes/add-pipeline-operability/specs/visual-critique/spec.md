## MODIFIED Requirements

### Requirement: Visual critique is optional and degrades gracefully
The system SHALL treat visual critique as optional: when the compiled render data is unavailable or rendering fails, refinement continues using the deterministic QA and text Judge. Such a degradation SHALL be reported to the per-run degradations collector and end-of-run summary rather than silently swallowed, so an operator can tell "the critic never ran" or "the real render was unavailable" apart from a healthy run.

#### Scenario: Missing render data
- **WHEN** the show's compiled render data is not available
- **THEN** the visual critic is skipped and refinement proceeds without it

#### Scenario: A skipped critic is recorded, not swallowed
- **WHEN** the visual critic or the real render fails or is unavailable
- **THEN** the loss is recorded to the per-run degradations collector and appears in the end-of-run summary
