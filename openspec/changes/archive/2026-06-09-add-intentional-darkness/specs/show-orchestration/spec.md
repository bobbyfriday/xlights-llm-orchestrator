## ADDED Requirements

### Requirement: Lit-group coverage scales with section energy
The number of prop groups a section's wash lights SHALL scale with the section's intensity — fewer in low-intensity sections, more in high-intensity sections — leaving the rest intentionally dark.

#### Scenario: Quiet section is sparse
- **WHEN** a low-intensity section is generated
- **THEN** only a few of its groups are lit and the others are left dark

#### Scenario: Loud section is full
- **WHEN** a high-intensity section is generated
- **THEN** most/all of its groups are lit

#### Scenario: Never empty
- **WHEN** coverage is reduced
- **THEN** at least a minimum number of groups remain lit (a section is never fully blacked out by this rule)
