## MODIFIED Requirements

### Requirement: Human checkpoints
The system SHALL support an attended mode in which it pauses at each refine decision to present the score, findings, and proposed revisions, and lets a human approve, edit or drop revisions, redirect, stop, or accept as final — the human decision overriding the Judge — with a final approval before saving. An unattended mode SHALL run to the bounded stop conditions without prompting. In attended mode the checkpoints SHALL be answerable from the live browser surface without parking the event loop, while the blocking terminal prompts remain the wired fallback for a non-browser or failed-server-bind run; unattended mode SHALL be unchanged. The run's output SHALL include the end-of-run degradations summary so a human can see what the run gave up on.

#### Scenario: Human stops the loop
- **WHEN** the human chooses stop at a checkpoint
- **THEN** refinement ends and the current best sequence is finalized

#### Scenario: Human overrides the Judge
- **WHEN** the Judge says iterate but the human accepts as final
- **THEN** no further iteration occurs

#### Scenario: Unattended mode
- **WHEN** unattended mode is selected
- **THEN** refinement proceeds without prompts, bounded by the cap and stall conditions

#### Scenario: A checkpoint answered in the browser does not park the loop
- **WHEN** an attended run reaches a checkpoint and the human answers from the browser
- **THEN** the loop resumes with that decision without having parked the event loop, and the terminal prompt remains the wired fallback when no browser is available

#### Scenario: The run reports what it lost
- **WHEN** a run completes having degraded one or more capabilities
- **THEN** the end-of-run output includes the degradations summary naming each loss
