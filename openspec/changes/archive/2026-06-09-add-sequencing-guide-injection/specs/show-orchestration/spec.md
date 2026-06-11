## ADDED Requirements

### Requirement: Sequencing agents apply a best-practices guide
When a sequencing best-practices guide is configured, the design, generation, and critique agents SHALL apply it.

#### Scenario: Guide present
- **WHEN** a guide is configured and the Director, Generator, Visual Critic, or Judge runs
- **THEN** that agent's instructions include the guide

### Requirement: Single user-editable guide source
The guide SHALL be a single user-editable source applied to those agents, so editing it updates all of them.

#### Scenario: Edit propagates
- **WHEN** the guide file is edited
- **THEN** the agents use the updated content (no per-agent copies to maintain)

### Requirement: Missing guide is a no-op
A missing or unconfigured guide SHALL be a no-op — the agents behave exactly as without it.

#### Scenario: No guide
- **WHEN** no guide file is found
- **THEN** the agents run with their normal instructions and nothing fails

### Requirement: Music-interpretation agents do not receive the guide
The music-interpretation agents (analysis panel, synthesizer) SHALL NOT receive the sequencing guide.

#### Scenario: Analyst excluded
- **WHEN** an analysis/synthesizer agent runs
- **THEN** its instructions do not include the sequencing guide
