## ADDED Requirements

### Requirement: The creative direction defines a color palette mapped to the song
The creative direction SHALL define a color palette and how it maps to the song's sections and moods, with the mapping justified by the song's dynamics and harmony.

#### Scenario: Palette mapping
- **WHEN** the creative direction is produced
- **THEN** it includes a core palette and a per-section palette whose choices reflect the section's energy/mood

### Requirement: The creative brief conveys the show in plain, non-musical terms
The creative brief SHALL include a plain-language description of what the light show conveys to a viewer — its overall visual/emotional experience and a per-section sense of what is seen — expressed in everyday terms rather than musical theory, so a non-musician can understand and approve the creative intent.

#### Scenario: Lay-readable vision
- **WHEN** the creative brief is produced
- **THEN** it includes an audience-experience description (overall and per section) understandable without musical knowledge

### Requirement: Each prop group has a coherent role
The creative direction SHALL assign each prop group a role/motif (its purpose, signature style, and color treatment) that is kept consistent across the show.

#### Scenario: Group roles
- **WHEN** the creative direction is produced
- **THEN** each group used in the show has a stated role/motif that recurs coherently across sections

### Requirement: Per-section direction is grounded in the song description
Each section's direction SHALL be grounded in the song description — citing that section's dynamics, instrumentation, and accents — and SHALL NOT invent narrative or genre unsupported by the analysis.

#### Scenario: Grounded section
- **WHEN** a section's direction is produced
- **THEN** its rationale references the section's real intensity/instrumentation/accents

#### Scenario: No fabrication
- **WHEN** the song is instrumental or otherwise lacks supporting evidence
- **THEN** the direction does not invent lyrics, a story, or a genre not supported by the song description

### Requirement: Key musical moments receive deliberate choreography
The creative direction SHALL give the song's key moments — accents, the climax, and any featured lyric moments — deliberate visual choreography tied to their timestamps.

#### Scenario: Key moments
- **WHEN** the song has accents/a climax/featured lyric moments
- **THEN** the direction specifies a deliberate treatment for them at their times

### Requirement: Human review of the creative brief before generation
The system SHALL produce a human-readable creative brief and pause for human review/approval (with the ability to correct) before generating effects, unless running unattended.

#### Scenario: Attended run
- **WHEN** the creative direction is produced in an attended run
- **THEN** the pipeline pauses and presents the creative brief for review/approval before generation

#### Scenario: Unattended run
- **WHEN** running unattended
- **THEN** the brief is written and generation proceeds without pausing

### Requirement: Effect generation follows the creative brief
Effect generation SHALL follow the creative brief — a section's generated effects reflect its assigned palette, group roles/motifs, and effect direction.

#### Scenario: Generation reflects the brief
- **WHEN** a section is generated
- **THEN** the generator is given that section's palette, group motifs, and effect direction to follow
