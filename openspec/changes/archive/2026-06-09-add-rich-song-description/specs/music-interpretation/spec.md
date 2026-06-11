## ADDED Requirements

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
