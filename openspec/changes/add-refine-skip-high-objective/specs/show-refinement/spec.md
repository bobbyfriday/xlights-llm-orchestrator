## ADDED Requirements

### Requirement: Skip the refine loop when the first pass is already good

The refine loop SHALL accept the initial draft without running any judging iterations when the draft's
first-pass deterministic objective score meets or exceeds a configurable threshold. The decision SHALL
use only the objective score the loop already computes before iterating, so it SHALL NOT spend any LLM
call (no Judge, no visual critique) to decide to skip, and SHALL NOT regenerate any section. When the
draft is skipped this way, the draft is left in place as the final result and the skip SHALL be
recorded in the revision log as a finalize record marked as a high-objective skip.

The threshold SHALL be configurable through the `XLO_REFINE_SKIP_OBJECTIVE` environment variable and
SHALL be set such that a value above the maximum possible objective score (for example `101`) disables
the skip so the loop always iterates. When the first-pass objective is below the threshold, the loop
SHALL run exactly as it does without this feature — the iteration cap, plateau detection, stall
termination, and human checkpoints are unchanged.

#### Scenario: An already-good draft skips judging

- **WHEN** the refine loop starts and the draft's first-pass objective score is at or above the
  configured threshold
- **THEN** the loop accepts the draft without invoking the Judge or the visual critique and without
  regenerating any section, and records the skip in the revision log

#### Scenario: A weak draft still refines

- **WHEN** the refine loop starts and the draft's first-pass objective score is below the threshold
- **THEN** the loop proceeds to judge and regenerate as it does today, bounded by the same iteration
  cap, plateau, and stall logic

#### Scenario: The skip is tunable and disable-able

- **WHEN** `XLO_REFINE_SKIP_OBJECTIVE` is set above the maximum objective score
- **THEN** no draft can meet the threshold, so the loop always iterates (the skip is disabled)
