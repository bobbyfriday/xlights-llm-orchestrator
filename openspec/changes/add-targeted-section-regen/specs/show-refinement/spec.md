## ADDED Requirements

### Requirement: A single section can be regenerated on demand

The system SHALL provide a direct, user-invoked way to regenerate exactly one section of a previously
generated show without running the automatic refine loop. Given a song with cached artifacts (song
analysis, music brief, show plan, and instructions) and a chosen section index, the system SHALL reload
those artifacts, regenerate only the chosen section through the same per-section realization the refine
loop uses, replace that section's instruction slice, and leave every other section's instructions
unchanged. The chosen section's structure — its start time, end time, and target groups — SHALL be pinned
across the regeneration. When no cached instructions exist for the song, the system SHALL fail with a
clear message directing the user to generate the show first. An out-of-range or non-existent section index
SHALL fail loudly rather than silently doing nothing.

#### Scenario: Regenerate one section, leave the rest intact

- **WHEN** the user regenerates section `i` of a song that already has cached instructions
- **THEN** only the instructions tagged with section `i` are replaced and every instruction belonging to
  another section is byte-identical to before, and section `i`'s start time, end time, and target groups
  are unchanged

#### Scenario: Regeneration requires an existing show

- **WHEN** the user requests a section regenerate for a song that has no cached instructions
- **THEN** the system reports that the show must be generated first and makes no changes

#### Scenario: Invalid section index is rejected

- **WHEN** the user requests a section index outside the show's section range
- **THEN** the system fails with a clear error and does not modify the sequence

### Requirement: A regenerate may be steered by a free-text fix note

The on-demand single-section regenerate SHALL accept an optional free-text note describing the desired
fix (for example, "too busy, calm it down"). When a note is provided, it SHALL steer that section's
regeneration through the same revision-brief mechanism the refine loop uses to pass a section-scoped
issue to the generator. When no note is provided, the section SHALL be regenerated fresh with no
additional guidance, still pinned to its cached structure.

#### Scenario: Note steers the regeneration

- **WHEN** the user regenerates a section with a fix note
- **THEN** the note is carried into the section's revision brief and the generator regenerates that
  section in light of it

#### Scenario: Regeneration without a note rerolls the section

- **WHEN** the user regenerates a section without a note
- **THEN** the section is regenerated without extra guidance and its structure remains pinned

### Requirement: The on-demand regenerate persists the updated sequence

After regenerating a section, the system SHALL re-emit the full instruction set and re-save the sequence
— including the cached instructions and the finalized output (audio, render order, and timing-track
patches) — so the saved show reflects the change, unless the user explicitly requests that the result not
be saved. The user SHALL also be able to list the show's sections (index, time range, and label) to
choose which one to regenerate.

#### Scenario: Saved sequence reflects the regenerated section

- **WHEN** a section regenerate completes with saving enabled
- **THEN** the updated instructions are persisted and the finalized sequence on disk reflects the new
  section while preserving the others

#### Scenario: List sections to choose a target

- **WHEN** the user lists the sections of a generated show
- **THEN** the system prints each section's index, time range, and label so the user can pick one to
  regenerate
