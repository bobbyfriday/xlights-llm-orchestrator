# music-interpretation Specification

## Purpose
TBD - created by archiving change add-analysis-panel. Update Purpose after archive.
## Requirements
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

### Requirement: Per-section intensity is normalized to the song's dynamic range
The interpretation SHALL express each section's intensity relative to the song's own dynamic range, so the quietest section is near 0 and the loudest near 1, and SHALL indicate the values are relative.

#### Scenario: A song with a clear loud section
- **WHEN** one section is markedly louder than the rest
- **THEN** that section's intensity is near the top of the range and the quietest section near the bottom (not all clustered near zero)

### Requirement: Instrument prevalence is reported over time
The interpretation SHALL report each section's instrument/stem prevalence as shares over time (the relative power of each stem), not only the single dominant instrument.

#### Scenario: Stems available
- **WHEN** stem separation is available
- **THEN** each section reports the relative share of each stem and a phrase describing what is carrying it

#### Scenario: Stems unavailable
- **WHEN** stems are not available
- **THEN** shares are omitted and the description notes that instrumentation detail is unavailable

### Requirement: Featured lyric moments carry timestamps
When lyrics exist, the interpretation SHALL identify the standout/powerful lines with their start–end timestamps and why each lands; for instrumental tracks this SHALL be empty.

#### Scenario: Vocal track
- **WHEN** the song has timed lyrics
- **THEN** notable lines are listed with their timestamps and a reason they are featured

#### Scenario: Instrumental track
- **WHEN** the song has no lyrics
- **THEN** featured lyric moments are empty and the rest of the description is unaffected

### Requirement: A human-readable song description is produced
The system SHALL produce a human-readable description of the song covering its identity, structure (per section), dynamic arc, instrumentation over time, rhythm/accents, harmony/tension, and narrative or emotional journey.

#### Scenario: Description covers the song
- **WHEN** interpretation completes
- **THEN** a readable description is available that describes each section and the overall arc, not just raw numbers

### Requirement: Human review of the description before proceeding
The system SHALL pause for human review and approval (with the ability to correct) of the song description before proceeding to later stages, unless running unattended.

#### Scenario: Attended run
- **WHEN** interpretation completes in an attended run
- **THEN** the pipeline pauses and presents the description for review/approval before continuing

#### Scenario: Unattended run
- **WHEN** running unattended
- **THEN** the description is written and the pipeline continues without pausing

### Requirement: Surface per-section rhythm for generation
The interpretation SHALL surface, per section, the beat times and the section's prominent instrument with its onset times, so generation can place rhythmically.

#### Scenario: Section rhythm available
- **WHEN** a section is interpreted and stems are available
- **THEN** its beat times, its prominent instrument, and that instrument's onset times within the section are available to generation

#### Scenario: No stems
- **WHEN** stem data is unavailable
- **THEN** the beat times are still surfaced and the prominent instrument degrades gracefully (rhythm can still follow the beats)

### Requirement: Interpretation consumes timed lyrics
When timed lyrics exist, the interpretation SHALL produce a narrative and featured lyric moments anchored to their times, and MAY refine section labels with the lyric structure hints.

#### Scenario: Vocal song interpreted
- **WHEN** the analysis carries timed lyrics
- **THEN** the brief has a non-empty narrative and featured lyric moments with timestamps

### Requirement: Song structure derives from timed lyric section markers when available
WHEN the fetched lyrics carry section markers (e.g. Verse/Pre-Chorus/Chorus) and alignment yields timed positions for at least two of them, the analysis SHALL rebuild its structural segments from those markers — boundaries snapped to the beat grid, sections below a minimum length merged, segments labeled by the markers — with an intro segment before the first marker and an outro segment after the last sung line. The audio segmentation SHALL remain the fallback when markers are absent and SHALL in-fill boundaries inside long instrumental spans between markers.

#### Scenario: Marker-rich song gets lyric-aligned sections
- **WHEN** a song's Genius lyrics contain Verse/Pre-Chorus/Chorus/Post-Chorus markers that align against the vocal stem
- **THEN** the analysis segments match the marker boundaries (beat-snapped), carry the marker labels, and downstream interpretation/design plans one section per lyric section instead of one per coarse audio segment

#### Scenario: Instrumental and marker-less songs unchanged
- **WHEN** a song has no lyrics, or its lyrics carry fewer than two timed markers
- **THEN** the audio segmentation is used unchanged and the pipeline behaves exactly as before

#### Scenario: Lyric-labeled segments are ground truth to the analysts
- **WHEN** the structure analyst receives segments carrying lyric-derived labels
- **THEN** the labeled sections keep those labels in the interpretation (judgment is spent on themes and energy, not boundary re-derivation)

### Requirement: Instrumental songs' long sections subdivide at musical seams
WHEN a song's analysis carries no timed lyric lines (the lyric-marker refiner's complement) and any audio segment exceeds the maximum section length (~32s), that segment SHALL be subdivided into pieces between the minimum (~12s) and maximum length, cut at beat-snapped candidate seams — harmonic-change points preferred, energy-delta peaks as fallback, the beat nearest the window limit as last resort — labeled by the parent segment id plus an ordinal (e.g. "A" → "A1","A2"). Segments already within the maximum SHALL pass through untouched, the refinement SHALL be idempotent, and timed-lyric songs SHALL be unaffected.

#### Scenario: Coarse instrumental segments become bounded sub-sections
- **WHEN** an instrumental song's audio segmentation yields 60–75s segments and the analysis carries harmonic-change points and a beat grid
- **THEN** each long segment is split at beat-snapped harmonic changes into pieces no longer than the maximum and (apart from unavoidable pre-existing slivers) no shorter than the minimum, labeled A1/A2/... under the parent, and downstream interpretation/design plans one section per piece

#### Scenario: Graceful degradation of cut candidates
- **WHEN** the analysis lacks harmonic changes, energy data, or beats
- **THEN** cuts fall back in order to energy-delta peaks, then pure time-based placement, and are left unsnapped only when no beat grid exists — never producing a piece over the maximum length

#### Scenario: Lyric songs and short instrumentals unchanged
- **WHEN** a song has timed lyric lines, or every audio segment already fits the maximum section length
- **THEN** the segments are untouched and the pipeline behaves exactly as before

#### Scenario: Sub-segments are one evolving part to the analysts
- **WHEN** the structure analyst receives numbered sub-segments (e.g. A1/A2)
- **THEN** it treats them as beat-snapped subdivisions of one musical part — related but evolving looks, boundaries kept, not re-derived

