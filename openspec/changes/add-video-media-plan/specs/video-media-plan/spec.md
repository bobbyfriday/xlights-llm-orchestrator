## ADDED Requirements

### Requirement: Media are planned before the storyboard, deterministically

The system SHALL decide each section's medium (filmed or procedural) from cached structure — section
energies and the climax, featured-line hits, section labels and durations — and a clip budget, before
the Videographer is invoked and without any LLM call. The same inputs SHALL always produce the same
plan.

#### Scenario: Plan is a pure function of cache and budget

- **WHEN** a media plan is built twice from the same cached artifacts and budget
- **THEN** the two plans are identical

#### Scenario: No LLM is consulted to plan

- **WHEN** a media plan is built
- **THEN** no agent runs and no token usage is recorded

### Requirement: Filmed sections are chosen by value within the campaign budget

The system SHALL rank sections by a value score in which the climax, sections carrying featured lines,
the opening section and energy raise the score, and SHALL mark sections filmed in rank order until the
next section's asset group would exceed the campaign clip budget. Every other section SHALL be
procedural.

#### Scenario: Climax is filmed first

- **WHEN** the budget covers exactly one asset group
- **THEN** the climax section's group is the filmed one

#### Scenario: Budget is never exceeded

- **WHEN** filmed sections are chosen
- **THEN** the sum of their asset groups' clips is at most the campaign budget

#### Scenario: Zero budget is all procedural

- **WHEN** the campaign budget is zero
- **THEN** every section is procedural and the plan needs no clips

#### Scenario: Pinned sections are honoured

- **WHEN** the user pins sections as filmed
- **THEN** those sections are filmed before any ranked section, and the remainder of the budget is spent by rank

### Requirement: Repeated sections share one filmed asset

Sections with the same chorus-family label (chorus, pre-chorus, post-chorus, refrain, hook, drop)
SHALL form an asset group; sections with any other label SHALL each be their own asset. A filmed
group SHALL consume its clips once, and every member section SHALL reference the same asset.

#### Scenario: Choruses share an asset

- **WHEN** four sections are labelled chorus and the group is filmed
- **THEN** all four reference one asset and the plan counts that asset's clips once

#### Scenario: Verses with the same label are not grouped

- **WHEN** four sections are labelled verse
- **THEN** each is its own asset

### Requirement: Clip math applies to filmed sections only

A filmed asset SHALL need `ceil(duration / (clip length × max stretch))` clips at the configured clip
length and stretch. Filmed shots SHALL be split on cached downbeats at that effective length.
Procedural shots SHALL never be split regardless of duration.

#### Scenario: Clips for a long filmed section

- **WHEN** the clip length is 8 s, the stretch is 1.2 and a filmed section lasts 20.8 s
- **THEN** it needs 3 clips and is split into 3 parts on downbeats

#### Scenario: Long procedural section is one shot

- **WHEN** a procedural section lasts 57 s
- **THEN** it remains a single shot

### Requirement: A project-wide daily ledger governs what may be rendered today

The system SHALL keep an append-only ledger at the cache root with one record per generated clip
(timestamp, day in the configured quota-reset timezone, clip id, song, asset, seconds, model), and
SHALL compute remaining quota for today as the daily limit minus today's records across all songs.

#### Scenario: Remaining counts across songs

- **WHEN** 7 clips were recorded today for one song and 2 for another, with a daily limit of 10
- **THEN** remaining quota is 1

#### Scenario: Yesterday does not count

- **WHEN** records exist only for a previous day
- **THEN** remaining quota equals the daily limit

#### Scenario: Missing ledger is empty

- **WHEN** no ledger file exists
- **THEN** remaining quota equals the daily limit and nothing is created until a record is appended

### Requirement: The plan separates the campaign budget from today's quota

The storyboard SHALL be planned against the campaign clip budget, and the plan SHALL carry a promote
order of filmed assets by value so a renderer can spend today's remaining quota on the next assets.
Today's remaining quota SHALL NOT change which sections are filmed.

#### Scenario: Exhausted quota leaves the plan intact

- **WHEN** the ledger shows zero clips remaining today
- **THEN** the filmed sections are unchanged and the plan reports zero renderable today

#### Scenario: Promote order follows value

- **WHEN** two assets are filmed
- **THEN** the higher-value asset has promote rank 1

### Requirement: The plan and the renderer hand-off are persisted

The system SHALL write `media_plan.json` beside the script with the budget, ledger state at plan
time, each section's medium, asset group, value score and clips, each asset's promote rank, and for
each shot a code-composed Veo prompt (filmed) or procedural brief (procedural). The Markdown script
SHALL show each shot's medium and a media summary.

#### Scenario: Plan file written with the script

- **WHEN** a video script is generated
- **THEN** `media_plan.json` exists beside it and names every shot's medium

#### Scenario: Hand-off text contains no timestamps written by the model

- **WHEN** a shot's Veo prompt or procedural brief is inspected
- **THEN** its span and frame count come from the resolved shot, not from agent text

### Requirement: Planned media spend is priced from data

The system SHALL compute the plan's Veo seconds and estimated spend from the configured per-second
rate, and SHALL report the spend as unknown, not zero, when the rate is unpriced.

#### Scenario: Priced plan

- **WHEN** a per-second rate is configured and 3 clips of 8 s are planned
- **THEN** the plan states 24 Veo seconds and 24 × rate as the estimate

#### Scenario: Unpriced plan

- **WHEN** no per-second rate is configured
- **THEN** the estimate is unknown
