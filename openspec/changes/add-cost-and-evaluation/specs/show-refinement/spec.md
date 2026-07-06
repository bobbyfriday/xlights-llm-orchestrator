## ADDED Requirements

### Requirement: Deterministic rendered-pixel metrics may gate the objective score
The system SHALL admit deterministic rendered-pixel metrics (coverage, motion, and music-sync computed from the compiled render data) into the objective revert/stall gate, because they are reproducible and unambiguous, while palette and section-signature metrics remain advisory.

The rendered-pixel metrics SHALL be rolled out advisory-first and only promoted to objective after a documented calibration pass, SHALL be disableable by a single kill switch that restores prior behavior, and — being strictly richer than the prior three-point coverage sampler — SHALL replace that sampler for coverage when the full render-data series is available.

#### Scenario: Rendered coverage/motion/sync gate objectively once promoted
- **WHEN** the rendered-pixel metrics are enabled and calibrated and a revision worsens rendered coverage, motion, or sync beyond the gate margin
- **THEN** that regression participates in the objective revert/stall decision like the other objective metrics

#### Scenario: Palette and signature metrics stay advisory
- **WHEN** the palette or section-signature metrics flag an issue
- **THEN** they inform the Judge and the log only and do not change the objective score

#### Scenario: Kill switch restores prior behavior
- **WHEN** the rendered-pixel metrics are disabled by the kill switch
- **THEN** refinement behaves exactly as it did before the metrics existed, using the prior deterministic checks

#### Scenario: Series supersedes the three-point sampler
- **WHEN** the full render-data series is available for a section
- **THEN** coverage is scored from the series and the three-point coverage sampler is not used for that section

### Requirement: The loop re-critiques only changed or flagged sections
The system SHALL, each refine iteration, run the cheap visual critique only on sections whose instructions changed since their last critique or that the deterministic metrics flagged, rather than re-critiquing every section, since regeneration is section-scoped.

Findings for unchanged, unflagged sections SHALL either carry forward tagged as prior-iteration or be dropped, and the change SHALL detect section change against the finalized instruction slice so whole-list passes re-trigger critique where they alter a section.

#### Scenario: Single-section regen critiques one section next iteration
- **WHEN** exactly one section was regenerated and no other section was flagged by the deterministic metrics
- **THEN** the next iteration's cheap critique runs on that one section only

#### Scenario: A whole-list pass re-triggers affected sections
- **WHEN** a whole-list finalize pass alters a section's finalized instructions
- **THEN** that section's instruction hash changes and it is re-critiqued
