## ADDED Requirements

### Requirement: Separate the mix into instrument stems
The system SHALL, when stem separation is enabled and available, separate the song into instrument stems (vocals, drums, bass, other) and make them available for measurement and inspection.

#### Scenario: Stems produced
- **WHEN** stem separation is enabled and the dependency/model is available
- **THEN** the analysis yields the four instrument stems

#### Scenario: Stems are inspectable
- **WHEN** stems are produced
- **THEN** the separated stem audio is persisted so it can be listened to / inspected

### Requirement: Measure each stem
The system SHALL compute, per stem, an energy arc and onset times.

#### Scenario: Per-stem features
- **WHEN** stems are produced
- **THEN** each stem carries its own energy arc and onset list

### Requirement: Derive per-section instrument prevalence
The system SHALL aggregate per-stem energy over each analysis section to report, per section, each stem's share and the dominant instrument(s).

#### Scenario: Section instrumentation
- **WHEN** stems are produced and the analysis has sections
- **THEN** each section reports per-stem energy shares and its dominant instrument(s)

### Requirement: Stem analysis is optional and degrades gracefully
The system SHALL treat stem separation as optional: when it is disabled, or its dependency/model is unavailable, or it fails/times out, the analysis SHALL still complete with the existing (full-mix) measurements and simply omit stem data.

#### Scenario: Disabled or unavailable
- **WHEN** stem separation is disabled or its dependency is not installed
- **THEN** the analysis completes normally and reports no stem data

#### Scenario: Failure mid-separation
- **WHEN** stem separation is attempted but fails or times out
- **THEN** the failure is logged and the analysis still returns its full-mix measurements

### Requirement: Stem results are cached
The system SHALL cache the stems and derived stem features keyed by the song's content, so a re-run reuses them instead of re-separating.

#### Scenario: Cached re-run
- **WHEN** the same song is analyzed again with stems enabled
- **THEN** the cached stems/features are reused without re-running separation
