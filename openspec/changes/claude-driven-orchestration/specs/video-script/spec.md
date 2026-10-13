## MODIFIED Requirements

### Requirement: Generate a storyboard from a song's cached story material

The system SHALL produce a video storyboard for a song from a story Claude writes under the video skill (`video_story.json`: logline, recurring motifs, one beat per brief section, no time fields) plus the cached lyrics and the validated creative brief, by validating the story and resolving it to timed shots, without re-running any pipeline stage and without contacting xLights.

#### Scenario: Storyboard produced from cache

- **WHEN** `xlo video-plan` is requested for a song whose analysis, brief, and story are cached
- **THEN** the system writes a storyboard covering the song with no pipeline stage re-run

#### Scenario: Missing prerequisites refuse clearly

- **WHEN** a required cached artifact (analysis, brief, or story) is absent
- **THEN** the system refuses with an error naming it, and writes no script file

#### Scenario: Malformed story never reaches a file

- **WHEN** the story fails validation (a missing beat, a time field, an unknown section)
- **THEN** no script file is written and the error names the section or field

### Requirement: Persisted, opt-in and accounted

The system SHALL write a machine-readable and a human-readable script to the song's cache directory, replacing any previous one, and SHALL NOT run video planning during a normal show flow unless requested.

#### Scenario: Both forms written

- **WHEN** a script is generated
- **THEN** JSON and Markdown forms are written to the song's cache directory, replacing prior ones

#### Scenario: Normal runs unaffected

- **WHEN** a show is made without requesting a video
- **THEN** no story is written and no planning occurs
