## ADDED Requirements

### Requirement: Objective QA includes rendered lit-coverage
When a rendered preview is available, the objective QA score SHALL include a coverage metric measuring how lit the display is in high-energy sections.

#### Scenario: Dark loud section gates
- **WHEN** a high-intensity section renders near-black
- **THEN** the coverage score drops, an error finding names the section, and the objective score falls

#### Scenario: Quiet sections not penalized
- **WHEN** a low-intensity section is sparse/dark
- **THEN** coverage does not penalize it (restraint is intentional)

#### Scenario: No preview available
- **WHEN** no rendered preview exists (hermetic tests, missing renderer)
- **THEN** the QA behaves exactly as before (coverage neutral, objective unchanged)
