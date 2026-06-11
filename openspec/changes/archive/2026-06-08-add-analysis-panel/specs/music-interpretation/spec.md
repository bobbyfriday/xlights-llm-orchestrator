## ADDED Requirements

### Requirement: Interpret a song analysis into a MusicBrief
The system SHALL transform a raw `SongAnalysis` (objective measurements) into a `MusicBrief` containing labeled sections (with timing), a repetition map, an energy-arc summary, key/mood, candidate themes, and transition points.

#### Scenario: Produce a MusicBrief
- **WHEN** a `SongAnalysis` is interpreted
- **THEN** the system returns a `MusicBrief` with labeled sections and at least one candidate theme

#### Scenario: Sections are labeled (interpretation, not raw)
- **WHEN** the MusicBrief's sections are inspected
- **THEN** each carries a human/semantic label (e.g. verse/chorus/drop) and timing — unlike the raw analysis, which carries only algorithmic ids

### Requirement: Analysts run in parallel
The system SHALL run the analyst agents concurrently (not strictly one after another), bounded by a configurable concurrency limit, then combine their outputs.

#### Scenario: Concurrent analysis
- **WHEN** the panel analyzes a song
- **THEN** the analysts execute concurrently and all of their results are combined into the MusicBrief

#### Scenario: Bounded concurrency
- **WHEN** the panel runs
- **THEN** the number of simultaneous analyst calls does not exceed the configured limit

### Requirement: Synthesize analyst outputs into one brief
The system SHALL combine the analysts' separate outputs into a single, de-conflicted `MusicBrief` via a synthesizer step.

#### Scenario: Fusion
- **WHEN** the analysts have produced their individual outputs
- **THEN** the synthesizer merges them into one coherent MusicBrief

### Requirement: The show planner consumes the MusicBrief
The system SHALL provide the `MusicBrief` to the show planner (Director) as its input, in place of the raw analysis summary.

#### Scenario: Director plans from the brief
- **WHEN** the Director produces a ShowPlan
- **THEN** it does so from the MusicBrief's labeled sections, themes, and energy arc

### Requirement: Configurable panel size
The system SHALL allow the panel to be configured, including collapsing to a single combined analyst for cheap/fast runs.

#### Scenario: Collapse to one analyst
- **WHEN** the panel is configured to a single analyst
- **THEN** interpretation still produces a valid MusicBrief using that one analyst

### Requirement: Interpretation is cache-resumable
The system SHALL cache the interpretation result so a re-run reuses it rather than re-invoking the analysts.

#### Scenario: Cached re-run
- **WHEN** the same song is interpreted again
- **THEN** the cached MusicBrief is reused without re-calling the analyst agents

### Requirement: Acquire lyric text (optional, graceful)
The system SHALL attempt to obtain the song's lyric text from an external lyrics source, and SHALL proceed without lyrics when none can be obtained (no credential, no match, or an instrumental track) — never failing the interpretation.

#### Scenario: Lyrics available
- **WHEN** the song's artist/title resolve and lyric text is found
- **THEN** the lyric text is made available to the interpretation

#### Scenario: Lyrics unavailable
- **WHEN** no lyric source credential is configured, or no match is found
- **THEN** interpretation continues and still produces a valid MusicBrief without lyric-derived content

### Requirement: Interpret lyrics into narrative
The system SHALL, when lyric text is available, interpret it into narrative/thematic content (overall narrative, sentiment, and featured lines) and incorporate that into the `MusicBrief`.

#### Scenario: Lyric narrative in the brief
- **WHEN** lyric text was obtained for a song
- **THEN** the resulting MusicBrief carries lyric-derived narrative content (themes, sentiment, and/or featured lines)

#### Scenario: No lyric narrative for instrumentals
- **WHEN** no lyric text was obtained
- **THEN** the MusicBrief is still valid and simply omits lyric-derived narrative content

### Requirement: Extensible for additional analysts
The system SHALL allow new analyst perspectives (e.g. a future genre/cultural-reference analyst, or a word-timed lyric analyst once alignment exists) to be added to the panel without changing the MusicBrief contract for existing consumers.

#### Scenario: Add an analyst later
- **WHEN** a new analyst is added to the panel
- **THEN** the synthesizer incorporates it and the MusicBrief remains valid for the Director
