## ADDED Requirements

### Requirement: The pipeline emits progress through an injectable, inert-by-default stream
The pipeline SHALL emit progress events (stage bracketing, per-section generation, per-iteration scores, refine decisions, checkpoints, and a terminal done) through an injected progress bus, defaulting to an inert null bus so that unattended runs, tests, and the golden pipeline snapshot are unchanged. Emitting SHALL be best-effort and SHALL never break a run; refine events SHALL be emitted from the same record construction that feeds the revision log so the stream and the log can never disagree.

#### Scenario: Default is inert
- **WHEN** the pipeline runs unattended or under test with no progress bus supplied
- **THEN** a null bus is used, no progress surface is started, and the golden snapshot is byte-identical

#### Scenario: Events mirror the revision log
- **WHEN** a refine iteration is recorded
- **THEN** its progress event is emitted from the same record that feeds the revision log, so the two agree

#### Scenario: Emission never breaks a run
- **WHEN** emitting a progress event raises
- **THEN** the error is swallowed and the run continues

### Requirement: Evaluation can run headless against a pre-rendered fixture
The system SHALL support evaluating a show headless — without a live GUI xLights — by running the deterministic QA and metrics over a pre-rendered fixture render, and SHALL ship a checked-in fixture render plus a hermetic test that exercises this path so it can seed CI full-pipeline evaluation. This capability SHALL be scoped to read-only evaluation of an existing render; regenerating effects still requires the render engine.

#### Scenario: QA runs over a fixture without xLights
- **WHEN** the hermetic evaluation test runs against the checked-in fixture render
- **THEN** the deterministic QA and metrics are computed with no live xLights running or contacted

#### Scenario: Regeneration still needs the engine
- **WHEN** evaluation would require new or changed effects rather than reading an existing render
- **THEN** that is out of scope for the headless fixture path, which reads a pre-rendered fixture only
