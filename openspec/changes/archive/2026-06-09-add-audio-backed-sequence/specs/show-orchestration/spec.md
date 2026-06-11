## ADDED Requirements

### Requirement: The generated sequence includes the song audio
The system SHALL attach the song's audio to the generated sequence so it plays with sound.

#### Scenario: Audio attached
- **WHEN** a sequence is generated for a song
- **THEN** the open sequence has the song's audio attached and its duration matches the song

### Requirement: The sequence is named after the song
The system SHALL name the generated sequence after the song by default, deriving a safe name from the song filename, and SHALL allow a manual name override.

#### Scenario: Default name from the song
- **WHEN** a sequence is generated for `mad russian christmas.mp3` with no name override
- **THEN** the sequence is saved under a name derived from the song (e.g. `mad_russian_christmas`)

#### Scenario: Manual override
- **WHEN** a name is explicitly provided
- **THEN** that name is used instead of the song-derived one

### Requirement: Generation replaces an already-open sequence
The system SHALL replace (clean-slate) any already-open sequence when generating, rather than aborting.

#### Scenario: A sequence is already open
- **WHEN** generation runs while another sequence is open
- **THEN** generation discards the open sequence and proceeds, without requiring the user to close it first

### Requirement: Audio is attached via a readable path
The system SHALL attach audio using a path the application can read (within its accessible storage), rather than an arbitrary source path that may be inaccessible or mis-encoded.

#### Scenario: Source path is outside accessible storage or has problematic characters
- **WHEN** the song's source path is outside the application's accessible storage or contains characters that break attachment
- **THEN** the system uses a copy placed in accessible storage with a safe name so attachment succeeds

### Requirement: Fall back to an audio-less sequence on attachment failure
The system SHALL fall back to generating an audio-less sequence (and warn) if the audio cannot be attached, rather than failing the run.

#### Scenario: Audio cannot be attached
- **WHEN** the song cannot be copied or attached
- **THEN** generation continues with an audio-less sequence and surfaces a warning
