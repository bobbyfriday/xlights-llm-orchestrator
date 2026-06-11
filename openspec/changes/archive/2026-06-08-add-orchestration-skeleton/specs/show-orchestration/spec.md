## ADDED Requirements

### Requirement: Produce a show plan from a song analysis
The system SHALL transform a `SongAnalysis` into a `ShowPlan` that assigns, per song section, a creative intent (target prop groups, effect family, intensity) — driven by an LLM Director agent.

#### Scenario: Plan covers the song
- **WHEN** a `SongAnalysis` is given to the Director
- **THEN** the system produces a `ShowPlan` with one or more sections, each naming target groups and an intent

#### Scenario: Plan targets valid groups
- **WHEN** the Director chooses targets
- **THEN** the targets are prop groups that exist in the current layout

### Requirement: Generate placeable effect instructions
The system SHALL turn each section of the `ShowPlan` into validated effect instructions — each selecting a preset look, knob values, palette, target, layer, and time range — assembled through the preset library so the settings are valid by construction.

#### Scenario: Instructions are assembled from presets
- **WHEN** the Generator produces instructions for a section
- **THEN** each instruction references a preset look/palette and assembles to a valid settings string (out-of-range knob values are rejected)

### Requirement: Place effects without removing any
The system SHALL place generated effects additively — on prop groups, on distinct layers and/or non-overlapping time ranges — and SHALL NOT depend on removing or replacing existing effects (the automation API cannot remove effects).

#### Scenario: Additive placement
- **WHEN** multiple effects are placed
- **THEN** they are arranged so none requires deleting another (distinct layers and/or non-overlapping times)

#### Scenario: Skip effects xLights will not place
- **WHEN** an effect type or instruction is not accepted by xLights (reported as not placed)
- **THEN** the system skips it and continues, rather than aborting the run

### Requirement: Agent roles are routable to different model providers
The system SHALL resolve each agent role to a model via configuration, so a role can be served by different providers (e.g. Claude or Gemini) without code changes.

#### Scenario: Default routing
- **WHEN** no override is configured
- **THEN** each role uses its default model

#### Scenario: Re-route a role
- **WHEN** a role's model is changed in configuration
- **THEN** that role runs on the newly configured provider/model with no code change

### Requirement: Orchestrate as a resumable pipeline
The system SHALL run the stages — analyze, design, generate, apply, render, finalize — as an ordered pipeline whose state can be persisted and resumed.

#### Scenario: End-to-end run
- **WHEN** the pipeline is run for a song
- **THEN** it proceeds analyze → design → generate → apply → render → finalize and ends with a rendered sequence

#### Scenario: Resume after interruption
- **WHEN** a run is interrupted and restarted
- **THEN** it can resume from persisted state rather than restarting from scratch

### Requirement: Never discard the user's open work
The system SHALL create its working sequence without discarding any sequence the user already has open, refusing or pausing rather than forcing.

#### Scenario: User sequence open
- **WHEN** a sequence is already open when a run starts
- **THEN** the system does not force it closed; it refuses with a clear message (or uses an explicitly sanctioned path)

### Requirement: Run without live services for testing
The system SHALL allow its pipeline to run with stubbed agent outputs (no real model calls), so the flow can be exercised without an LLM API key.

#### Scenario: Stubbed agents
- **WHEN** the pipeline runs with test/stub models
- **THEN** the full analyze→render flow executes and produces effect instructions without contacting a real LLM provider
