## ADDED Requirements

### Requirement: Sequence lifecycle
The system SHALL create, open, save, and close xLights sequences through the automation API, and SHALL report lifecycle failures as typed conditions.

#### Scenario: Create a new sequence
- **WHEN** a caller creates a new sequence with a duration and frame timing
- **THEN** the system opens a new empty sequence ready to receive effects

#### Scenario: Save requires a name when unnamed
- **WHEN** a caller saves a sequence that has never been named without providing a name
- **THEN** the system reports that a name is required rather than saving silently

#### Scenario: Open already-open without override
- **WHEN** a caller creates a new sequence while one is already open and does not request override
- **THEN** the system reports that a sequence is already open rather than discarding it

### Requirement: Do not discard unsaved open work without confirmation
The system SHALL NOT discard the user's currently-open or unsaved sequence as an implicit side effect. Operations that would discard open or unsaved work (creating over an open sequence, closing with unsaved changes) SHALL require explicit confirmation from the caller.

#### Scenario: Closing with unsaved changes is gated
- **WHEN** a caller closes a sequence that has unsaved changes without explicit confirmation
- **THEN** the system refuses and reports the unsaved changes rather than discarding them

#### Scenario: Overwriting open work is opt-in
- **WHEN** a caller creates a new sequence over open work
- **THEN** the system proceeds only if the caller explicitly opted in to discard the open sequence

### Requirement: Place an effect on a target
The system SHALL place an effect onto a target that exists as an element of the open sequence, on a given layer, over a start/end time range, and SHALL require a sequence to be open. The target being present in the layout is necessary but not sufficient — it must be an element of the open sequence.

#### Scenario: Effect placed on an open sequence
- **WHEN** a caller places an effect on a target that is an element of the open sequence, over a valid time range
- **THEN** the effect is added to that target's layer

#### Scenario: No sequence open
- **WHEN** a caller places an effect while no sequence is open
- **THEN** the system reports a "no sequence open" condition rather than failing opaquely

#### Scenario: Target not in the layout
- **WHEN** a caller targets a model or group name that does not exist in the layout
- **THEN** the system rejects the request before contacting xLights (a cheap pre-check)

#### Scenario: Target not an element of the open sequence
- **WHEN** a caller targets a model that exists in the layout but is not an element of the open sequence
- **THEN** the system reports a distinct "target not in sequence" condition

#### Scenario: Placement not accepted
- **WHEN** xLights accepts the request but reports the effect was not added (e.g. an overlapping effect on the layer, or an unusable effect/layer)
- **THEN** the system treats it as a failure and surfaces it, rather than reporting success

### Requirement: Preset-backed effect placement
The system SHALL place effects from the preset library by assembling settings from a chosen look and knob values (validated per knob) and a chosen palette, so callers do not author raw settings strings. A gated raw-settings path MAY be offered as an escape hatch.

#### Scenario: Place a preset
- **WHEN** a caller places an effect by look, knob values, and palette
- **THEN** the system assembles a valid settings string (rejecting any out-of-constraint knob value) and places the effect with that palette

#### Scenario: Raw placement is gated
- **WHEN** a caller uses the raw-settings path
- **THEN** it is clearly distinguished from preset-backed placement

### Requirement: Serialize all mutations
The system SHALL serialize all sequence-mutating operations so that concurrent callers cannot interleave writes to the single shared open sequence. Read operations SHALL remain unaffected.

#### Scenario: Concurrent writes are serialized
- **WHEN** multiple mutating operations are issued concurrently
- **THEN** they are applied one at a time, never interleaved

### Requirement: Render the open sequence
The system SHALL render the currently open sequence and report success, and SHALL report a "no sequence open" condition when none is open.

#### Scenario: Render succeeds
- **WHEN** a caller renders with a sequence open
- **THEN** the system renders it and reports success

#### Scenario: Render with no sequence open
- **WHEN** a caller renders with no sequence open
- **THEN** the system reports a "no sequence open" condition rather than failing opaquely

### Requirement: Validate a preset against a running xLights
The system SHALL validate a preset by placing it on a dedicated scratch sequence in a running xLights, rendering, and reporting whether it was accepted — where accepted means the effect was added (placement reported as worked) and the sequence rendered successfully. Validation SHALL require that no user sequence is open and SHALL NOT discard the user's work to make room.

#### Scenario: Preset accepted
- **WHEN** a preset (look + knob values + palette) is placed and the effect is added and the sequence renders successfully
- **THEN** the system reports acceptance

#### Scenario: Preset not accepted
- **WHEN** the placement is not accepted (not added) or rendering fails
- **THEN** the system reports the preset as not accepted, with the details

#### Scenario: Validation requires a clean slate
- **WHEN** a user sequence is open
- **THEN** validation refuses and asks the caller to close it, rather than forcing it closed

#### Scenario: Validation isolates user work
- **WHEN** validation runs
- **THEN** it uses a disposable scratch sequence (discarded afterward) and does not modify or save the user's sequences
