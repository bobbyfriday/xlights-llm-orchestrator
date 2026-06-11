## ADDED Requirements

### Requirement: Effects respect duration classes
Each placed effect SHALL respect its duration class: hit effects bounded to ~a bar, phrase effects to ~8 bars, sustained effects unbounded.

#### Scenario: Hit effect placed long
- **WHEN** generation produces a hit-class effect (e.g. Shockwave) spanning many bars
- **THEN** it is converted into short per-bar cells rather than one long smear

#### Scenario: Phrase effect placed long
- **WHEN** a phrase-class effect spans more than ~8 bars
- **THEN** it is clamped to its phrase length

#### Scenario: Sustained untouched
- **WHEN** a sustained-class effect spans a section
- **THEN** it is left as designed
