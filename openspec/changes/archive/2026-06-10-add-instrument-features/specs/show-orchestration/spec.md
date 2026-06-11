## ADDED Requirements

### Requirement: Instrument entrances are detected and featured
A sustained surge of an instrument stem SHALL be detected as an entrance, and a hero prop SHALL ride that instrument's onsets with a suitable effect for a bounded feature window.

#### Scenario: Guitar entrance
- **WHEN** a stem's energy rises sharply and sustains above its entrance threshold
- **THEN** a feature is placed on the focal prop at the entrance, timed to that stem's onsets

#### Scenario: No surge
- **WHEN** a stem is already prominent (no surge) or only blips
- **THEN** no entrance is detected for it

### Requirement: Entrances surface to the planner
Detected entrances SHALL be added to the show's key moments so design and critique see them.

#### Scenario: Key moment
- **WHEN** an entrance is detected
- **THEN** a key moment of kind "entrance" exists at its time

### Requirement: Refined instructions persist
The instruction cache SHALL reflect the refined (final) instructions, not the pre-refine generation.

#### Scenario: Cached re-run
- **WHEN** a run completes refinement and a later run loads the cache
- **THEN** the loaded instructions are the refined ones
