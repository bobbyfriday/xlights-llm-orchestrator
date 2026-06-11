## ADDED Requirements

### Requirement: Effect speed scales with section energy
Section effects SHALL have their speed scaled by the section's intensity — slower when quiet, faster when loud.

#### Scenario: Quiet vs loud
- **WHEN** two sections differ in intensity
- **THEN** the lower-intensity section's effects are given a lower speed than the higher-intensity section's

#### Scenario: Applied regardless of preset
- **WHEN** an effect's preset omits a speed setting
- **THEN** a speed is still applied (appended) using the effect's speed key
