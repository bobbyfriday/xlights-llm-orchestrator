## ADDED Requirements

### Requirement: Reference timing tracks for structure and rhythm
The finished sequence SHALL include reference timing tracks for the song's sections, beats, and bars, with marks at the analyzed times.

#### Scenario: Section, beat, and bar tracks
- **WHEN** a sequence is finalized
- **THEN** it contains a Section track (labeled sections), a Beat track (the beat grid), and a Bar track, each with marks at the right times

#### Scenario: Bars without detected downbeats
- **WHEN** downbeats are not detected in the analysis
- **THEN** the Bar track is derived from the beat grid (a fixed beats-per-bar)

### Requirement: Per-prominent-stem onset tracks
An onset timing track SHALL be added per prominent stem, not as a single combined track and not for every stem.

#### Scenario: Prominent stems get their own tracks
- **WHEN** stems are available
- **THEN** an onset track is added for each prominent stem (e.g. drums and the lead/bass), and near-silent stems and a combined all-onsets track are not added

### Requirement: Chord and lyric tracks when data exists
Chord and lyric timing tracks SHALL be added when that data is available, and omitted otherwise.

#### Scenario: Instrumental song
- **WHEN** there are no timed lyrics
- **THEN** no lyric track is added (and a chord track is added only if chords were analyzed)

### Requirement: Timing tracks are written offline and best-effort
Timing tracks SHALL be written without using the live automation API, and the operation SHALL be best-effort — a failure leaves a valid sequence and does not block finalize.

#### Scenario: Patch failure
- **WHEN** writing the timing tracks fails
- **THEN** the finalized sequence remains valid and usable (the failure is logged, not raised)
