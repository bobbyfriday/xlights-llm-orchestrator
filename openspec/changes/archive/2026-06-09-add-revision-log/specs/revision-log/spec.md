## ADDED Requirements

### Requirement: Append a record per refine iteration
The system SHALL append one structured record per refine iteration to a durable, append-only log keyed to the song, plus a final record when the loop finishes.

#### Scenario: One record per iteration
- **WHEN** the refine loop runs N iterations
- **THEN** N iteration records (plus a finalize record) are appended to the song's revision log

#### Scenario: Durable and append-only
- **WHEN** a record is written
- **THEN** it is appended without rewriting or losing prior records, and each record is independently parseable

### Requirement: Capture the iteration's decisions and outcome
Each iteration record SHALL capture the findings (with their source/metric and severity), the Judge verdict, the revisions applied — distinguishing backstop-synthesized from Judge-made — and the objective outcome (score before, after, and whether it was reverted).

#### Scenario: Findings, verdict, revisions, outcome
- **WHEN** an iteration produces findings, a Judge verdict, applied revisions, and an objective result
- **THEN** the record contains the findings by source, the verdict, the revisions tagged by origin, and obj_before/obj_after/reverted

#### Scenario: Backstop revisions are distinguishable
- **WHEN** a revision was synthesized by the safety-net backstop rather than the Judge
- **THEN** the record marks it as backstop-originated

### Requirement: Provide a human-readable view
The system SHALL provide, alongside the programmatic log, a human-readable rendering of each iteration that conveys what was flagged, what the Judge decided, which revisions ran (and whether the Judge or the backstop drove them), what changed, and the outcome.

#### Scenario: Readable narrative per iteration
- **WHEN** an iteration is logged
- **THEN** a human-readable entry for that iteration is available describing its findings, the verdict, the revisions and their origin, and the objective outcome

#### Scenario: Both forms stay consistent
- **WHEN** an iteration is recorded
- **THEN** the human-readable entry and the programmatic record describe the same iteration

### Requirement: Capture the human decision when attended
The record SHALL capture the human checkpoint decision (e.g. approve/redirect/stop/accept) when the run is attended.

#### Scenario: Attended run
- **WHEN** a human makes a checkpoint decision during refinement
- **THEN** that decision is recorded in the iteration record

### Requirement: Logging is pure observability
Logging SHALL NOT affect refine decisions or outcomes — a run produces the same final result whether logging is enabled or disabled.

#### Scenario: Same outcome with logging on or off
- **WHEN** the same refinement runs with logging enabled and disabled
- **THEN** the final show state is identical

### Requirement: Logging is optional and degrades to no-op
The system SHALL allow logging to be disabled, in which case no log is written and the loop proceeds normally.

#### Scenario: Disabled logging
- **WHEN** logging is disabled
- **THEN** no revision log is written and refinement completes unchanged
