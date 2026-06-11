## ADDED Requirements

### Requirement: Wash brightness scales with section energy
The section's sustained (wash) effects SHALL be given a brightness that scales with the section's intensity — lower intensity dimmer, higher intensity brighter.

#### Scenario: Quiet vs loud section
- **WHEN** two sections differ in intensity
- **THEN** the lower-intensity section's wash is dimmer than the higher-intensity section's

#### Scenario: Applied regardless of preset
- **WHEN** a wash effect's preset has no brightness knob
- **THEN** the brightness is still applied (via appended settings)
