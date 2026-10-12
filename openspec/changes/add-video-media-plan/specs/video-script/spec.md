## MODIFIED Requirements

### Requirement: The video tells a story rather than replicating the lights

The system SHALL give the Videographer the song's story material — lyrics, narrative, themes,
sentiment, mood and featured lines — together with section structure, energy, the show palette, each
section's medium and asset group, and the procedural vocabulary, and SHALL NOT give it the per-section
lighting descriptions, motions, effect types or target groups.

#### Scenario: Story inputs are provided

- **WHEN** the agent input is built for a song with cached lyrics and narrative
- **THEN** it contains the lyrics, narrative, themes, sentiment, mood, featured lines, section energies and palette

#### Scenario: Lighting descriptions are withheld

- **WHEN** the agent input is built
- **THEN** it contains no per-section look, motion, effect type or target group text

#### Scenario: Media are provided per section

- **WHEN** the agent input is built from a media plan
- **THEN** every section line states filmed or procedural, and filmed sections name their asset group

### Requirement: Optional downbeat-aligned splitting

The system SHALL split filmed shots longer than the effective clip length (the configured clip length
times the stretch, or a user-supplied maximum) into consecutive parts whose interior boundaries fall on
cached downbeats, each part sharing the beat and carrying a part index. Procedural shots SHALL never
be split.

#### Scenario: Procedural shots never split

- **WHEN** a procedural shot exceeds any maximum
- **THEN** it is not split

#### Scenario: Long filmed shot split on downbeats

- **WHEN** a filmed shot exceeds the effective clip length
- **THEN** it becomes consecutive parts no longer than that length, split on downbeats, spanning exactly the original shot

#### Scenario: User maximum overrides the clip length for filmed shots

- **WHEN** a maximum shot duration is supplied
- **THEN** filmed shots are split at that maximum and procedural shots are unaffected

## ADDED Requirements

### Requirement: Procedural beats are renderable procedurally

The Videographer SHALL be given the procedural vocabulary, and a procedural beat SHALL NOT depict
people, faces, hands, animals or objects that must be recognized while moving. The system SHALL lint
procedural beats and procedural stand-ins for such terms and SHALL ask the model once for a rewrite
on a hit; a second hit SHALL fail validation and write no file.

#### Scenario: Person in a procedural beat triggers one retry

- **WHEN** the agent's first output describes a child in a procedural beat
- **THEN** the system requests a rewrite naming the beat and the term

#### Scenario: Repeated violation writes nothing

- **WHEN** the rewrite still describes a person in a procedural beat
- **THEN** validation fails and no script or plan file is written

#### Scenario: Filmed beats may depict people

- **WHEN** a filmed beat describes hands
- **THEN** the lint does not object

### Requirement: Filmed beats carry a procedural stand-in

Every filmed beat SHALL include a one-sentence procedural stand-in using only the procedural
vocabulary, and the procedural brief for a filmed shot SHALL be composed from that stand-in.

#### Scenario: Stand-in required

- **WHEN** a filmed beat is returned without a stand-in
- **THEN** validation fails

#### Scenario: Stand-in feeds the fallback brief

- **WHEN** a filmed shot's procedural brief is composed
- **THEN** it is built from the stand-in, not the filmed imagery

### Requirement: Motifs survive both media

The Videographer SHALL be instructed that a character may appear only in filmed beats and SHALL be
carried through procedural beats by a proxy object motif.

#### Scenario: Motif rule is in the prompt

- **WHEN** the Videographer's system prompt is inspected
- **THEN** it states the character/proxy rule and the procedural vocabulary
