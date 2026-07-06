## ADDED Requirements

### Requirement: Deterministic offline report over the revision log
The system SHALL provide a report command that reads the revision-log JSONL from the cache tree and computes cost and quality metrics deterministically and offline — no LLM call, no xLights, no network — and the command SHALL NOT gate on the presence of an LLM key.

An empty cache SHALL exit successfully with a clear "no revision logs found" message. Parsing SHALL be tolerant line-by-line: a malformed line is counted and skipped, surfaced in the report, and never aborts it.

#### Scenario: Report runs with no key and no services
- **WHEN** `xlo report` is invoked with no LLM key configured, no running xLights, and no network
- **THEN** it produces the report from the on-disk revision logs alone and exits successfully

#### Scenario: Empty cache exits cleanly
- **WHEN** the cache root contains no revision logs
- **THEN** the command exits 0 with a clear "no revision logs found under <root>" message

#### Scenario: Malformed line is skipped, counted, and surfaced
- **WHEN** a revision-log file contains a line that fails to parse
- **THEN** that line is skipped, the skipped-line count appears in the report, and every other run is still reported

### Requirement: Compute once, render as terminal, HTML, and JSON
The system SHALL compute all report metrics once into a typed report model and SHALL render that same model three ways: terminal text by default (stdlib formatting, no new dependency), an optional self-contained static HTML page (no JavaScript, no external URLs), and a JSON emission of the report model that downstream tooling (the A/B harness) can consume. Renderers SHALL be formatting-only; all arithmetic lives in the compute layer.

#### Scenario: Terminal by default
- **WHEN** `xlo report` runs without format flags
- **THEN** it prints per-run rows (iterations, first→final objective, advisory, cost, cost per point, reverts, stop reason) and fleet aggregates as plain terminal tables

#### Scenario: Self-contained HTML
- **WHEN** the HTML output is requested
- **THEN** one self-contained file is written containing no scripts and no external references, rendering correctly in light and dark

#### Scenario: JSON round-trips
- **WHEN** the JSON output is requested
- **THEN** the emitted document validates back into the report model unchanged

### Requirement: Pre-telemetry logs degrade to explicit unknowns
The report SHALL fully parse revision logs written before token telemetry existed: quality metrics (trajectory, churn, reverts, skip rate) SHALL work at full fidelity, missing cost data SHALL render as `—` (never zero, never estimated), cost-derived metrics SHALL be omitted for uncosted runs, and aggregate cost totals SHALL count only costed runs with an explicit coverage caveat (e.g. "12 of 42 runs have cost data").

#### Scenario: Mixed corpus reports honest coverage
- **WHEN** the corpus mixes pre-telemetry and post-telemetry runs
- **THEN** uncosted runs show `—` in every cost cell, aggregate cost sums only the costed runs, and the report carries a caveat line stating how many of the total runs have cost data

#### Scenario: No proxy costs are fabricated
- **WHEN** a run's records carry no usage or cost fields
- **THEN** the report never substitutes an estimated cost for that run

### Requirement: Cost per quality point is defined for every gain
The report SHALL compute cost per objective point gained as refine spend divided by objective gain, and SHALL define the zero-or-negative-gain case as the rendering `∞ (no gain)` — never a division error — with skip-gate runs excluded from the cost-per-point aggregate by construction.

#### Scenario: Zero gain renders infinity
- **WHEN** a run's objective gain is zero or negative
- **THEN** its cost per point renders as `∞ (no gain)` and the report completes without error

#### Scenario: Skip-gate runs carry no cost-per-point
- **WHEN** a run was accepted at iteration 0 by the skip-high-objective gate
- **THEN** it is counted in the skip-gate hit rate but contributes nothing to the cost-per-point aggregate

### Requirement: Runs are grouped by run identifier and attributed to their model routing
The report SHALL treat one append-mode revision-log file as holding many runs, grouping records by run identifier (never by file), and SHALL attribute each run to the per-role model routing recorded in its own records so cost and quality can be compared across routings. A run without a finalize record SHALL be summarized from its last iteration and flagged incomplete.

#### Scenario: Appended runs are separate rows
- **WHEN** one revision-log file contains records from several runs
- **THEN** each run identifier yields its own summary row with its own model-routing label

#### Scenario: Incomplete run is flagged
- **WHEN** a run has iteration records but no finalize record
- **THEN** it is summarized from its last iteration, marked incomplete, and counted separately in fleet aggregates
