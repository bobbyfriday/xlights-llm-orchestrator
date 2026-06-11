## ADDED Requirements

### Requirement: Generation places beat-synchronized accent effects
Generation SHALL place beat- or onset-synchronized accent effects within sections, timed to the music's beats or the section's prominent instrument, in addition to the section's sustained effects.

#### Scenario: Accents on the beat
- **WHEN** a section is generated
- **THEN** short accent effects are placed within it at times aligned to the section's beats or its prominent instrument's onsets

### Requirement: Rhythmic choices are directable with a default
The rhythm groups, the followed instrument, and the accent effect SHALL be directable from the creative brief, and SHALL fall back to a sensible default when not specified.

#### Scenario: Directed by the brief
- **WHEN** the brief specifies the rhythm groups / followed instrument / accent effect for a section
- **THEN** the placed accents use those

#### Scenario: Default when unspecified
- **WHEN** the brief does not specify rhythmic intent for a section
- **THEN** generation uses a default (the section's prominent instrument and the layout's rhythm groups)

### Requirement: Accent density is bounded
The number of accent effects placed in a section SHALL be bounded so the total effect count and placement time stay reasonable (dense beats/onsets are downsampled).

#### Scenario: Dense section
- **WHEN** a section has many beats/onsets
- **THEN** the accents are capped/downsampled rather than placing one per beat without limit
