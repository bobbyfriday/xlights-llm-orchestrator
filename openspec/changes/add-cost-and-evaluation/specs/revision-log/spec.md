## MODIFIED Requirements

### Requirement: Capture the iteration's decisions and outcome
Each iteration record SHALL capture the findings (with their source/metric and severity), the Judge verdict, the revisions applied — distinguishing backstop-synthesized from Judge-made — the objective outcome (score before, after, and whether it was reverted), and the per-role LLM token usage spent producing that iteration.

The per-iteration usage SHALL be the tokens spent since the previous record (a delta window), recorded per role using role keys that match the record's `models` snapshot, and its fields default to empty so records predating telemetry validate unchanged.

#### Scenario: Findings, verdict, revisions, outcome
- **WHEN** an iteration produces findings, a Judge verdict, applied revisions, and an objective result
- **THEN** the record contains the findings by source, the verdict, the revisions tagged by origin, and obj_before/obj_after/reverted

#### Scenario: Backstop revisions are distinguishable
- **WHEN** a revision was synthesized by the safety-net backstop rather than the Judge
- **THEN** the record marks it as backstop-originated

#### Scenario: Per-role usage delta per iteration
- **WHEN** an iteration is recorded and token usage was captured for one or more roles
- **THEN** the record carries per-role input/output/cache token counts for exactly the tokens spent producing that iteration, keyed by role names matching the record's model snapshot

#### Scenario: Old records without usage still validate
- **WHEN** a revision-log line written before telemetry existed is parsed against the extended schema
- **THEN** it validates successfully with empty usage and no cost, and reports no cost distinct from a zero cost

## ADDED Requirements

### Requirement: The finalize record carries run token totals and estimated cost
The finalize record SHALL additionally carry the whole-run per-role token totals and an estimated run cost in USD, computed from those totals and a per-model price table, with the cost left unset (distinct from zero) whenever any role with nonzero usage has no known price.

A per-run cost summary SHALL also be surfaced for every run — including runs that never enter the refine loop — via a log line and a durable per-run usage artifact, so telemetry is not lost on non-refine or unlogged runs.

#### Scenario: Finalize totals and cost
- **WHEN** the refine loop finishes and usage was captured across the run
- **THEN** the finalize record carries per-role run totals and, when every used model is priced, an estimated total cost in USD; the per-iteration deltas sum to the run totals

#### Scenario: Unknown price yields unset cost, never zero
- **WHEN** a role with nonzero usage runs on a model absent from the price table
- **THEN** the estimated cost is left unset (unknown), never reported as zero

#### Scenario: Non-refine run still gets a summary
- **WHEN** a run completes without entering the refine loop (e.g. fully cached stages, or a manual regeneration)
- **THEN** a per-run usage summary is emitted and a durable usage artifact is written for it

### Requirement: The record attributes the run's terminal state when available
The revision log SHALL record the reason a run's refine loop terminated and which sections were redesigned when that information is available, and MUST remain valid when a record omits them (the fields are defaulted).

This lets analysis distinguish otherwise-identical terminal states (for example a stall stop from an iteration-cap stop) without changing loop behavior.

#### Scenario: Terminal-state attribution is optional
- **WHEN** the loop records a terminal state and a stop reason is available
- **THEN** the record carries the stop reason, and a record that omits it still validates and is treated as an unspecified stop
