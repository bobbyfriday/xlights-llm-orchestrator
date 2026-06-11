## ADDED Requirements

### Requirement: Beat accents contrast the wash
Beat accents SHALL be colored to contrast the section's wash, rather than reusing the wash's colors.

#### Scenario: Multi-color section
- **WHEN** a section has two or more colors
- **THEN** the wash uses the calmer/darker colors and the beat accents use a brighter, distinct color

#### Scenario: Single-color section
- **WHEN** a section has one color
- **THEN** the beat accents use a brightened/contrasting variant so they still read against the wash

### Requirement: An accent on about every beat, bounded
An accent SHALL be placed on approximately every beat of a section (not heavily downsampled), with an upper bound so a long section cannot place an unbounded number of effects.

#### Scenario: Normal section
- **WHEN** a section has ~32 beats
- **THEN** roughly that many accents are placed (not capped to a small fraction)

#### Scenario: Very long section
- **WHEN** a section has far more beats than the upper bound
- **THEN** the accents are bounded to the upper limit

### Requirement: Bar starts are emphasized
Bar starts SHALL be emphasized relative to other beats.

#### Scenario: Downbeat vs off-beat
- **WHEN** a beat is a bar start
- **THEN** it produces a larger hit (more groups) than an in-between beat
