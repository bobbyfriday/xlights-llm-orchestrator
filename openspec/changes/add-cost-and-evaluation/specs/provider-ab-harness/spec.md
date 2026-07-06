## ADDED Requirements

### Requirement: Run one song through multiple provider routings under controlled conditions
The system SHALL provide an A/B command that runs one fixture song through two or more provider-routing arms under controlled conditions: arms run sequentially, always unattended (no interactive gate), with repeats interleaved across arms rather than batched per arm, and a strict preflight SHALL verify that every provider named by any arm has its API key before any arm spends anything.

A malformed arm specification or an unknown role/provider SHALL fail at parse time, before any spend.

#### Scenario: Interleaved unattended arms
- **WHEN** `xlo ab` runs two arms with repeats
- **THEN** the runs execute sequentially in interleaved order (A,B,A,B) with no interactive prompt, each producing its own run in the shared revision log

#### Scenario: Missing key refuses before spend
- **WHEN** any arm names a provider whose API key is absent
- **THEN** the command refuses to start and no arm runs

#### Scenario: Bad arm spec dies at parse time
- **WHEN** an arm specification names an unknown role or provider
- **THEN** parsing fails with an error before any pipeline run begins

### Requirement: Per-role provider overrides route and log truthfully
The system SHALL resolve each role's provider as: role-specific environment override, then global provider override, then config default — so a mixed arm can route individual roles to different providers, and the per-role model snapshot recorded into every revision-log record SHALL reflect the true per-role mix.

#### Scenario: One role rerouted
- **WHEN** a role-specific override names one provider while the global override names another
- **THEN** only that role routes to the role-specific provider and every other role follows the global override

#### Scenario: Mixed arm is labeled truthfully
- **WHEN** a mixed arm (e.g. a Gemini base with the judge overridden to Anthropic) runs
- **THEN** the logged models snapshot shows the judge on Anthropic and the other roles on Gemini

### Requirement: LLM-stage caches are namespaced by the model routing
The system SHALL namespace every LLM-stage cache artifact (song description, creative brief, instructions, visual-review bundles) under a fingerprint of the active per-role model routing, with NO fallback read of the legacy un-namespaced path, so two routings can never read each other's artifacts. Deterministic, provider-independent artifacts (song analysis, the layout-fingerprinted targetable-groups probe, the revision log) SHALL remain shared across routings.

This is a BREAKING cache-layout change: existing per-song LLM caches go cold once and regenerate on the next run.

#### Scenario: Provider switch does not reuse the other provider's briefs
- **WHEN** a run under one provider populated the cache and a second run starts with `XLO_PROVIDER` set to a different provider
- **THEN** the second run does not read the first provider's cached song description, creative brief, or instructions, and regenerates them under its own fingerprint directory

#### Scenario: Shared artifacts stay shared
- **WHEN** two arms of an A/B run the same song
- **THEN** both use the same song-analysis and targetable-groups cache paths while their LLM-stage artifacts live in distinct fingerprint directories

#### Scenario: No legacy-path fallback
- **WHEN** a namespaced artifact is absent but a pre-change un-namespaced artifact exists
- **THEN** the pipeline treats the stage as uncached and regenerates rather than reading the legacy path

### Requirement: Arms hold the deterministic inputs constant
The harness SHALL analyze the song once and inject the same song analysis into every arm, SHALL warm the targetable-groups probe once before the first arm, SHALL give each run a distinct per-arm sequence save name so arms never overwrite each other's output, and SHALL write an A/B manifest incrementally after each completed run so an interrupted A/B keeps the data for the runs that finished.

#### Scenario: One analysis shared by identity
- **WHEN** an A/B with repeats runs
- **THEN** the audio analysis runs once and every arm receives the same analysis object, with no arm re-paying or re-racing the group probe

#### Scenario: Interrupted A/B keeps completed runs
- **WHEN** an A/B is aborted partway through its runs
- **THEN** the manifest on disk is valid and lists every run completed so far

### Requirement: Results are reported as distributions, never single numbers
The harness SHALL report each metric per arm as a median with a min–max range across repeats — never as a single number — SHALL report an arm-vs-arm delta smaller than either arm's range as indistinguishable, and SHALL NOT apply statistical significance tests in v1. Results SHALL land in the shared reporting surface (grouped by run identifier and models snapshot) plus the A/B manifest.

#### Scenario: Medians and ranges per arm
- **WHEN** an A/B with three repeats per arm completes
- **THEN** the summary shows, for each metric and arm, the median and the min–max range across that arm's runs

#### Scenario: Overlapping ranges are indistinguishable
- **WHEN** the difference between two arms' medians is smaller than either arm's own range
- **THEN** the summary reports the comparison as indistinguishable rather than declaring a winner
