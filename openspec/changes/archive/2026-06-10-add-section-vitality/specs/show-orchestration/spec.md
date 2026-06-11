## ADDED Requirements

### Requirement: The beat chase spans at least two rhythm groups
The beat accent chase SHALL run across at least two groups, extending a thin brief choice with the layout's rhythm-cell groups (arches, canes, mini trees).

#### Scenario: Brief picks one group
- **WHEN** the brief's pulse_groups has a single group and rhythm-cell groups exist
- **THEN** the chase is extended so the beat alternates across ≥2 groups

### Requirement: Accent props fire on downbeats
When snowflake/spinner accent groups exist, downbeats SHALL additionally fire short hits on them (and they are otherwise left to the design).

#### Scenario: Downbeat sparkle
- **WHEN** a bar starts and an accent group is available
- **THEN** a short accent hit is placed on it at that beat

### Requirement: High-energy sections carry an ensemble bed
Sections at high intensity SHALL include a low-brightness ensemble bed wash beneath the features, unless the section already targets that ensemble.

#### Scenario: Peak section
- **WHEN** a section's effective intensity is ≥0.7 and a ground/whole-display group exists
- **THEN** a bed wash spans the section on it

### Requirement: Long energetic washes build
Wash effects longer than ~15s in high-energy sections SHALL ramp brightness rather than holding a flat level.

#### Scenario: 36-second chorus wash
- **WHEN** a long wash is placed in a high-intensity section
- **THEN** its brightness ramps upward across the effect
