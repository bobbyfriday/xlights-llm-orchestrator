## ADDED Requirements

### Requirement: Generate a storyboard from a song's cached story material

The system SHALL produce a video storyboard for a song from its cached lyrics, music brief and show
plan, using a Videographer agent whose output is a validated structured type, without re-running any
pipeline stage and without contacting xLights.

#### Scenario: Storyboard produced from cache

- **WHEN** a video script is requested for a song whose analysis, music brief and show plan are cached
- **THEN** the system writes a storyboard covering the song with no pipeline stage re-run

#### Scenario: Missing prerequisites refuse clearly

- **WHEN** a required cached artifact is absent
- **THEN** the system refuses with an error naming it, and writes no script file

#### Scenario: Malformed agent output never reaches a file

- **WHEN** the agent's output fails validation
- **THEN** no script file is written

### Requirement: The video tells a story rather than replicating the lights

The system SHALL give the Videographer the song's story material — lyrics, narrative, themes,
sentiment, mood and featured lines — together with section structure, energy and the show palette, and
SHALL NOT give it the per-section lighting descriptions, motions, effect types or target groups.

#### Scenario: Story inputs are provided

- **WHEN** the agent input is built for a song with cached lyrics and narrative
- **THEN** it contains the lyrics, narrative, themes, sentiment, mood, featured lines, section energies and palette

#### Scenario: Lighting descriptions are withheld

- **WHEN** the agent input is built
- **THEN** it contains no per-section look, motion, effect type or target group text

### Requirement: The storyboard has a through-line

The storyboard SHALL state a logline and a set of recurring visual motifs, and each beat SHALL identify
the motifs it carries and how it continues from the previous beat.

#### Scenario: Logline and motifs present

- **WHEN** a storyboard is generated
- **THEN** it contains a logline and at least one recurring motif

#### Scenario: Beats declare continuity

- **WHEN** a beat after the first is inspected
- **THEN** it names the motifs it carries and its continuity from the previous beat

### Requirement: Timing is owned by code

The system SHALL key beats by section and SHALL set every beat's start and end from the cached section
boundaries; the agent SHALL NOT supply timestamps. Each beat SHALL carry the lyric lines whose timing
falls within it.

#### Scenario: Beat spans equal cached sections

- **WHEN** a storyboard is generated for N sections
- **THEN** it contains N beats whose spans equal the cached section boundaries, tiling the song

#### Scenario: Missing or extra beats are reconciled

- **WHEN** the agent omits a section or returns an out-of-range section index
- **THEN** the omitted section inherits the previous beat and the out-of-range beat is dropped

#### Scenario: Lyrics attach to their beat

- **WHEN** a cached lyric line starts within a section
- **THEN** that line is attached to that section's beat

### Requirement: Optional downbeat-aligned splitting

The system SHALL, when a maximum shot duration is supplied, split longer beats into consecutive parts
whose interior boundaries fall on cached downbeats, each part sharing the beat and carrying a part
index; without it, no beat SHALL be split.

#### Scenario: No split by default

- **WHEN** no maximum is supplied
- **THEN** no beat is split

#### Scenario: Long beat split on downbeats

- **WHEN** a maximum is supplied and a beat exceeds it
- **THEN** it becomes consecutive parts no longer than the maximum, split on downbeats, spanning exactly the original beat

### Requirement: Technical contract

The script SHALL state the supplied target resolution, a frame rate derived from the sequence frame
interval, total and per-shot durations with frame counts, full-frame opaque footage, and that no
rendered words appear. The system SHALL refuse when no resolution is supplied.

#### Scenario: Frame rate derived

- **WHEN** the sequence frame interval is 50 ms
- **THEN** the stated frame rate is 20 fps

#### Scenario: Resolution required

- **WHEN** no target resolution is supplied
- **THEN** the system refuses and writes no file

### Requirement: Persisted, opt-in and accounted

The system SHALL write a machine-readable and a human-readable script to the song's cache directory,
replacing any previous one; SHALL NOT invoke the Videographer during a normal show run; SHALL record the
agent's token usage under its own role; and SHALL route the role to a priced model.

#### Scenario: Both forms written

- **WHEN** a script is generated
- **THEN** JSON and Markdown forms are written to the song's cache directory, replacing prior ones

#### Scenario: Normal runs unaffected

- **WHEN** a show is generated without requesting a script
- **THEN** no Videographer call occurs

#### Scenario: Role is priced

- **WHEN** the configured Videographer model is checked for each provider
- **THEN** a price entry exists
