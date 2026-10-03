## ADDED Requirements

### Requirement: Export a video script from a show's cached creative direction

The system SHALL produce a time-coded video script for a song from its already-cached creative brief,
without re-running any pipeline stage and without contacting xLights. The export SHALL be
deterministic and SHALL NOT invoke a language model, so that the same cached inputs always produce the
same script and the export incurs no model cost.

#### Scenario: Script produced from cache alone

- **WHEN** a video script is requested for a song whose creative brief is cached
- **THEN** the system writes a script covering the song, with no pipeline stage re-run and no model call

#### Scenario: Deterministic output

- **WHEN** a script is generated twice from unchanged cached inputs
- **THEN** both runs produce identical content

#### Scenario: Missing prerequisites refuse clearly

- **WHEN** a video script is requested for a song with no cached creative brief
- **THEN** the system refuses with an error naming the missing artifact, and writes no script file

### Requirement: One shot per section, spanning the cached section boundaries

The system SHALL emit one shot per section of the cached brief by default, using that section's
`start_ms` and `end_ms` verbatim. The system SHALL NOT recompute, snap, or otherwise alter the cached
boundaries.

#### Scenario: Shot spans match the cached sections

- **WHEN** a script is generated for a brief with N sections
- **THEN** the script contains N shots whose start and end times equal those sections' cached boundaries

#### Scenario: Shots tile the song without gaps or overlaps

- **WHEN** the generated shots are inspected in order
- **THEN** each shot begins where the previous one ends, covering the song continuously

#### Scenario: Creative fields are carried through

- **WHEN** a section carries a look description, palette, motion and transition
- **THEN** the corresponding shot carries that description, palette, motion and transition

#### Scenario: Sections with no description are reported, not faked

- **WHEN** a cached section has an empty look description
- **THEN** the shot is still emitted with its correct timing, and the script marks it as having no description

### Requirement: Optional subdivision splits long shots on downbeats

The system SHALL accept a maximum shot duration and, when given, SHALL split any shot longer than that
maximum into consecutive parts, each aligned to a downbeat from the cached beat grid. Each part SHALL
carry its parent section's description and an identifying part index. Without that maximum, no shot
SHALL be subdivided.

#### Scenario: No subdivision by default

- **WHEN** a script is generated without a maximum shot duration
- **THEN** no section is split, regardless of its length

#### Scenario: A long section is split

- **WHEN** a maximum shot duration is supplied and a section exceeds it
- **THEN** that section becomes multiple consecutive shots, each no longer than the maximum

#### Scenario: Splits land on downbeats

- **WHEN** a section is split
- **THEN** each interior split point coincides with a downbeat from the cached beat grid

#### Scenario: Split parts preserve the section's content and coverage

- **WHEN** a section is split into parts
- **THEN** every part carries the parent section's description and a part index, and the parts together span exactly the original section

#### Scenario: Short sections are untouched

- **WHEN** a maximum shot duration is supplied and a section is shorter than it
- **THEN** that section remains a single shot

### Requirement: The script states a technical contract the returned video must satisfy

The script SHALL carry a constraints block, distinct from the creative shot content, stating the target
pixel dimensions, the frame rate, the total duration, each shot's absolute start and end in
milliseconds with its frame count, and loop points for sections that recur. The frame rate SHALL be
derived from the sequence's configured frame interval rather than assumed.

#### Scenario: Constraints are separate from creative content

- **WHEN** a generated script is inspected
- **THEN** computed constraints and per-shot creative description are distinguishable, not interleaved in one prose field

#### Scenario: Frame rate follows the sequence frame interval

- **WHEN** a script is generated for a sequence whose frame interval is 50 ms
- **THEN** the stated frame rate is 20 frames per second

#### Scenario: Shots state their frame counts

- **WHEN** a shot spans a known duration
- **THEN** the script states that shot's frame count at the stated frame rate

#### Scenario: Recurring sections declare loop points

- **WHEN** the cached brief marks two or more sections as the same recurring label
- **THEN** the script declares loop points for those sections

### Requirement: Target dimensions are supplied, never guessed

The system SHALL take the target pixel dimensions as a caller-supplied argument and SHALL refuse to
generate a script when they are absent. The system SHALL NOT substitute a default or assumed
resolution.

#### Scenario: Supplied dimensions appear in the contract

- **WHEN** the caller supplies target dimensions
- **THEN** the script's constraints state exactly those dimensions

#### Scenario: Absent dimensions refuse rather than assume

- **WHEN** no target dimensions are supplied
- **THEN** the system refuses with an error, and writes no script file

### Requirement: The contract specifies full-frame opaque footage and excludes words

Because the target matrix is dedicated to video, the script SHALL specify footage that fills the frame
and is fully opaque, and SHALL NOT request chroma-key, transparency, or compositing against underlying
content. The script SHALL state that no lyrics, titles, or other rendered text appear in the video,
because textual narrative is carried by a different prop.

#### Scenario: No keying or transparency is requested

- **WHEN** a generated script is inspected
- **THEN** it specifies full-frame opaque footage and requests no chroma-key, transparency, or compositing

#### Scenario: Text is excluded from the video

- **WHEN** a generated script is inspected
- **THEN** it states that rendered words must not appear in the footage

### Requirement: The script explains that descriptions are of a light display

The script SHALL instruct the consuming agent to render the imagery and mood that the cached
descriptions evoke, rather than depicting the lighting hardware itself, because those descriptions
describe prop-based lighting and not video content.

#### Scenario: The framing instruction is present

- **WHEN** a generated script is inspected
- **THEN** it states that the descriptions describe a light display and that the video should render their imagery and mood rather than the props

### Requirement: The script is persisted in both machine and human form

The system SHALL write the script into the song's cache directory in a machine-readable form for a
downstream consumer and a human-readable form for review, alongside the existing cached artifacts.

#### Scenario: Both forms written

- **WHEN** a script is generated successfully
- **THEN** a machine-readable script and a human-readable script are both written to the song's cache directory

#### Scenario: Regeneration replaces, never appends

- **WHEN** a script is generated for a song that already has one
- **THEN** the previous script files are replaced rather than duplicated or appended to
