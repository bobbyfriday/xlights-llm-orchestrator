## ADDED Requirements

### Requirement: Accent density scales with section intensity
The number of beat accents placed in a section SHALL scale with the section's intensity — quieter sections sparser, louder sections denser — while always keeping the bar-start emphasis.

#### Scenario: Quiet vs loud section
- **WHEN** two sections have the same beats but different intensity
- **THEN** the lower-intensity section places fewer accents than the higher-intensity one, and both retain downbeat accents

### Requirement: Feature-prop hits follow the prominent instrument
Beat accents SHALL be augmented by hits on a feature prop placed at the section's prominent instrument's onset times.

#### Scenario: Prominent stem present
- **WHEN** a section has a prominent stem with onsets
- **THEN** additional accents are placed on a feature prop at those onset times (bounded)

#### Scenario: No prominent stem
- **WHEN** no stem onsets are available
- **THEN** no feature-prop hits are added (the beat chase still plays)

### Requirement: Accent color follows chord changes
When chords are available, the accent color SHALL step through the section's palette as the chord changes.

#### Scenario: Chords present
- **WHEN** accents fall in different chord spans
- **THEN** their color differs across the chord changes

#### Scenario: No chords
- **WHEN** no chord data is available
- **THEN** accents use the single contrasting accent color
