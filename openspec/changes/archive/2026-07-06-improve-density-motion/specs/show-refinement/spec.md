## ADDED Requirements

### Requirement: A fabric-stats canary guards against fabric re-inversion
QA SHALL include a hermetic fabric-stats canary over the golden fixture that asserts loose bounds on the motion-vs-punctuation shares of energetic sections, so a future change cannot silently re-invert the fabric back toward punctuation-dominated placement. The canary SHALL evaluate only energetic sections and SHALL exempt deliberately quiet/`rest`/`gesture` sections, so improve-musicality Phase 2's deliberate sparseness never registers as a density regression. The bounds SHALL be the single enforced copy of the fabric targets, with the analysis doc carrying the prose rationale.

#### Scenario: A re-inverting change trips the canary
- **WHEN** a change lowers the golden fixture's energetic-section motion share below the canary floor (or raises On+Twinkle above its ceiling)
- **THEN** the canary test fails, naming the regressed share

#### Scenario: Deliberate sparseness does not trip it
- **WHEN** a quiet, rest, or gesture section in the fixture is sparse or punctuation-light by design
- **THEN** the canary does not count it against the fabric bounds (only energetic full/feature sections are asserted)
