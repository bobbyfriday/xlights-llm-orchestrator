## ADDED Requirements

### Requirement: Generate a video script from a show's cached artistic direction

The system SHALL produce a time-coded video script for a song from its already-cached `MusicBrief` and
`ShowPlan`, driven by an LLM Videographer agent whose output is a validated structured type. The script
SHALL be generatable without re-running analysis, interpretation, planning, or generation, and without
any xLights write operation.

#### Scenario: Script produced from cache alone

- **WHEN** a video script is requested for a song whose brief and show plan are cached
- **THEN** the system returns a script covering the song, with no analysis, planning, or generation stage re-run

#### Scenario: Missing prerequisites refuse clearly

- **WHEN** a video script is requested for a song with no cached show plan
- **THEN** the system refuses with an error naming the missing artifact, and writes no script file

#### Scenario: Malformed agent output never reaches a file

- **WHEN** the Videographer returns output that does not satisfy the script's structured type
- **THEN** validation fails and no script artifact is written

### Requirement: Shot timings derive from the musical grid, never from the model

The system SHALL compute every shot's absolute start and end time in code from the song's real section
boundaries and bar grid. The Videographer SHALL express shot placement only in bar-relative terms within
a named section, and SHALL NOT supply absolute timestamps. Resolved shots SHALL lie within their owning
section's span.

#### Scenario: Shot times are resolved from bar offsets

- **WHEN** the Videographer returns a shot with a bar offset and a length in bars for a section
- **THEN** the system resolves that shot's `start_ms` and `end_ms` from the section's real bar grid

#### Scenario: A shot cannot escape its section

- **WHEN** a returned shot's bar offset and length would extend beyond its section's end
- **THEN** the resolved shot is clamped to the section end

#### Scenario: Overlapping shots are reconciled

- **WHEN** two resolved shots in the same section overlap in time
- **THEN** the earlier shot is truncated at the later shot's start, leaving no overlap

#### Scenario: Degenerate sections still yield a shot

- **WHEN** every shot returned for a section resolves to zero length
- **THEN** the system emits a single shot spanning that section

#### Scenario: Shots tile their section without gaps

- **WHEN** the resolved shots for a section leave a trailing gap before the section end
- **THEN** the final shot is extended to the section end

### Requirement: The script states a technical contract the returned video must satisfy

The script SHALL carry a constraints block, separate from creative prose, stating at minimum: the target
pixel dimensions, the frame rate, the total duration, each shot's absolute start and end in milliseconds,
loop points for sections that recur, and guidance on what the target resolution cannot legibly carry. The
frame rate SHALL be derived from the sequence's configured frame interval rather than assumed.

#### Scenario: Constraints are separate from creative content

- **WHEN** a generated script is inspected
- **THEN** computed constraints and per-shot creative description are distinguishable, not interleaved in one prose field

#### Scenario: Frame rate follows the sequence frame interval

- **WHEN** a script is generated for a sequence whose frame interval is 50 ms
- **THEN** the stated frame rate is 20 frames per second

#### Scenario: Recurring sections declare loop points

- **WHEN** the brief's repetition map marks two or more sections as the same recurring label
- **THEN** the script declares loop points for those sections

#### Scenario: Low-resolution limits are stated

- **WHEN** a script is generated for a matrix at or near the minimum media resolution
- **THEN** the constraints state that fine detail, small text, and recognizable faces will not read at that size

### Requirement: Target resolution is discovered or declared, never guessed

The system SHALL determine the matrix's real pixel dimensions by probing the layout, SHALL accept an
explicit caller-supplied size, and SHALL refuse to generate a script when neither is available. The
system SHALL NOT substitute a default or assumed resolution into the script's constraints.

#### Scenario: Dimensions probed from the layout

- **WHEN** the matrix model's dimensions can be read from the layout
- **THEN** the script's constraints state those dimensions

#### Scenario: Explicit size overrides the probe

- **WHEN** the caller supplies an explicit target size
- **THEN** the script's constraints state the supplied size and no probe is required

#### Scenario: Unknown dimensions refuse rather than assume

- **WHEN** the matrix dimensions can neither be probed nor were supplied by the caller
- **THEN** the system refuses with an error naming both remedies, and writes no script file

#### Scenario: Probed dimensions are reused

- **WHEN** dimensions have been probed for a layout
- **THEN** a later request for the same layout reuses them without re-probing

### Requirement: The script is persisted in both machine and human form

The system SHALL write the script into the song's cache directory in a machine-readable form for a
downstream consumer and a human-readable form for review, alongside the existing cached artifacts.

#### Scenario: Both forms written

- **WHEN** a script is generated successfully
- **THEN** a machine-readable script and a human-readable script are both written to the song's cache directory

#### Scenario: Regeneration replaces, never appends

- **WHEN** a script is generated for a song that already has one
- **THEN** the previous script files are replaced rather than duplicated or appended to

### Requirement: Script generation is opt-in and its cost is accounted

Script generation SHALL NOT occur during a normal show run. The Videographer's token usage SHALL be
recorded in the same telemetry the cost report reads, and the role SHALL be routed to a model that has a
price entry so that generating a script never renders a run's reported cost unknown.

#### Scenario: A normal run makes no Videographer call

- **WHEN** a show is generated without explicitly requesting a video script
- **THEN** no Videographer invocation occurs and no script artifact is written

#### Scenario: Usage is recorded for reporting

- **WHEN** a script is generated
- **THEN** the Videographer's token usage is recorded under its own role in the telemetry the cost report reads

#### Scenario: The role is priced

- **WHEN** the configured Videographer model is checked against the price table for any supported provider
- **THEN** a price entry exists for that model
