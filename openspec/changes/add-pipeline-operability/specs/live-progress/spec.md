## ADDED Requirements

### Requirement: A live browser surface renders run progress from an event stream
The system SHALL offer a local browser surface that renders a run's live progress from the pipeline's event stream, served by a stdlib-only HTTP server bound to the loopback interface on an ephemeral port. The surface SHALL show stage timeline, per-section generation, per-iteration QA scores, and refine decisions, and SHALL stream updates via Server-Sent Events so a reopened or reconnected page replays missed events by last-seen id. The server SHALL run on a daemon thread and SHALL expose no state-changing GET route.

#### Scenario: Progress renders live
- **WHEN** an attended run is in progress and the page is open
- **THEN** the stage timeline, section grid, QA score sparkline, and refine decisions update live as events arrive over SSE

#### Scenario: A reopened page catches up
- **WHEN** the page is closed and reopened mid-run
- **THEN** it replays events since the last-seen id and resumes streaming, rather than losing the run's history

#### Scenario: Loopback-only, no mutating GET
- **WHEN** the live server's routes are enumerated
- **THEN** it binds only the loopback interface on an ephemeral port and exposes no state-changing GET route

### Requirement: Approval checkpoints are answerable from the browser without parking the loop
The system SHALL let a human answer each attended approval checkpoint from the browser, and SHALL wait for that answer without parking the asyncio event loop. The pipeline SHALL emit a checkpoint event, accept the answer via a single-use token route, and resume by mapping the answer to the existing checkpoint return types, emitting a resolution event. A stale or unknown checkpoint token SHALL be rejected. The blocking terminal prompts SHALL remain wired as the fallback for a non-browser, unattended, or failed-server-bind run, and each checkpoint SHALL be mirrored to stdout with the URL; unattended mode SHALL be unchanged by construction.

#### Scenario: A checkpoint is answered in the browser
- **WHEN** the pipeline reaches an approval checkpoint and the operator approves (or edits/stops) in the browser
- **THEN** the run resumes with that decision, a resolution event is emitted, and the event loop was never parked while waiting

#### Scenario: Terminal fallback stays wired
- **WHEN** a run is unattended, launched with the no-browser flag, or the live server fails to bind
- **THEN** the original blocking terminal checkpoints are used and unattended behavior is byte-for-byte unchanged

#### Scenario: A stale token is rejected
- **WHEN** an answer arrives for an unknown or already-resolved checkpoint token
- **THEN** the route rejects it rather than resuming the run twice
