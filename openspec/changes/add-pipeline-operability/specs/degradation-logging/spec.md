## ADDED Requirements

### Requirement: Best-effort failures are never silently swallowed
The system SHALL log every best-effort failure at least at debug with the exception value, and SHALL never leave a silent `pass`, so that a single log filter yields a complete list of what a run gave up on. A cosmetic degradation (cache miss/write, an expected recompute, a per-call fallback inside an already-reported capability) SHALL log at debug; the loss of a whole enrichment capability SHALL log at warning. Informational level SHALL be reserved for positive progress so that scanning warnings alone surfaces every capability loss. A structural test SHALL fail any best-effort exception handler whose body neither logs, records a degradation, nor re-raises.

#### Scenario: No handler is silent
- **WHEN** the structural audit test walks the source
- **THEN** it fails on any `except` block that neither logs, records a degradation, nor re-raises

#### Scenario: Whole-capability loss is a warning
- **WHEN** an enrichment capability (e.g. stems, lyrics, the visual critic) fails entirely
- **THEN** the loss is logged at warning, distinguishable by level from cosmetic debug-level fallbacks

### Requirement: A per-run degradations collector records what was lost
The system SHALL collect per-run degradations in a best-effort, run-scoped collector keyed by a closed capability taxonomy, deduplicating repeated losses with a count and an optional stage. The collector itself SHALL never break a run: a failure inside the recording path SHALL be swallowed to a debug log, mirroring the revision log's write guard. Capability keys SHALL be a fixed, documented set (not free-form) so downstream aggregation and dashboards can rely on them.

#### Scenario: Repeated losses dedupe with a count
- **WHEN** the same capability degrades multiple times in one run (e.g. the real render is unavailable across several refine iterations)
- **THEN** the collector records one entry for that capability with an occurrence count, tagged with its stage

#### Scenario: The collector cannot take a run down
- **WHEN** recording a degradation itself raises
- **THEN** the error is swallowed to a debug log and the run continues unaffected

### Requirement: Each run emits a degradations summary and artifact
The system SHALL emit an end-of-run degradations summary and write a machine-readable degradations artifact beside the revision log at every pipeline exit, including the early-return checkpoints. The summary SHALL be logged loudly (at warning) when non-empty so a degraded run ends conspicuously, and at info ("no degradations") otherwise. The artifact write SHALL be best-effort and SHALL sit alongside the revision log and usage records so cost, degradation, and score can be correlated per run.

#### Scenario: A degraded run ends loudly with an artifact
- **WHEN** a run finishes having lost one or more capabilities
- **THEN** a warning-level summary lists each lost capability with its count and stage, and a `degradations.json` is written beside the revision log

#### Scenario: A clean run says so
- **WHEN** a run finishes with no degradations
- **THEN** an info-level "no degradations" line is emitted and the summary claims nothing was lost

### Requirement: A failed group listing fails fast rather than limping
The system SHALL treat a failed listing of the layout's groups as fatal and raise before any LLM spend, because an empty group list has no useful degraded mode — it poisons the Director prompt and produces a garbage cached brief after paying for analysis, panel, and director tokens. A failed targetability *probe* SHALL keep its sane full-list fallback; only the listing itself fails fast.

#### Scenario: An unreadable group listing aborts early
- **WHEN** listing the show's groups fails on a transport error
- **THEN** the pipeline raises before running any analyst, panel, or director call

#### Scenario: A successful-but-empty listing still returns
- **WHEN** the layout genuinely defines no groups and the listing call succeeds
- **THEN** an empty list is returned normally, not treated as a failure
