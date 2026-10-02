## ADDED Requirements

### Requirement: Flat-flash share advisory
The deterministic evaluation SHALL emit an advisory (warn-severity, non-objective) finding when an energetic section's share of flat-flash effect types (On, Twinkle, Strobe, Shimmer, Lightning) exceeds the configured threshold (0.30), using the same energetic gate and quiet-treatment exemptions as the existing motion-share advisory. The finding SHALL NOT gate the objective score. (Corpus band: community flat-flash share ≈ 7.5%; ours measured 42% on 2026-07-07.)

#### Scenario: A flash-dominated energetic section warns
- **WHEN** an energetic section's instructions are 50% On/Strobe/Shimmer
- **THEN** evaluation returns a warn-severity, non-objective finding naming the section and its flat-flash share

#### Scenario: Quiet treatments are exempt
- **WHEN** a section has treatment `rest` or `gesture`
- **THEN** no flat-flash advisory is emitted for it regardless of share

#### Scenario: Score is not gated
- **WHEN** the only findings are flat-flash advisories
- **THEN** the objective score is unchanged by them
