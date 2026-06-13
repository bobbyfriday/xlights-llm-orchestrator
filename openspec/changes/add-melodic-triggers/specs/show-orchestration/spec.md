## ADDED Requirements

### Requirement: Triggers can key off any instrument stem
A trigger SHALL be able to fire on any instrument stem's onsets (drums, piano, bass, guitar,
vocals), selected by a `stem` field, with section eligibility by that stem's prominence. Triggers
without a `stem` SHALL default to drums (back-compat). A stem that is never prominent SHALL simply
produce no events (not an error).

#### Scenario: Piano notes drive the props
- **WHEN** a trigger specifies the piano stem on a piano-heavy song
- **THEN** it fires on the piano's onsets, rotating across the target groups so the melody walks the props, in the sections where piano is prominent

#### Scenario: Drum triggers unchanged
- **WHEN** an existing trigger names no stem
- **THEN** it fires on the drum stem exactly as before

### Requirement: Holiday songs prefer the traditional Christmas palette
The Director's palette guidance SHALL prefer a red / green / white primary palette with accent
colors for Christmas/holiday songs, unless the song's mood clearly calls for a different scheme.

#### Scenario: Christmas song palette
- **WHEN** the Director designs a show for a clearly Christmas/holiday song
- **THEN** its section palettes lean on red, green, and white as primaries with a small number of accent colors
