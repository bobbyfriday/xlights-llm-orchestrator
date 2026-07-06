## MODIFIED Requirements

### Requirement: Preset-backed effect placement
The system SHALL place effects from the preset library by assembling settings from a chosen look and knob values (validated per knob) and a chosen palette, so callers do not author raw settings strings. A gated raw-settings path MAY be offered as an escape hatch. The system SHALL ALSO offer a code-templated (non-catalog) direct-placement path (`place_direct`) for the asset-bound effect types (`DIRECT_TYPES`) whose settings cannot come from the mined catalog: it takes a settings string built by the code-owned builders, validates it syntactically (parser round-trip, known key kinds), merges `extra_settings` with the same first-occurrence-wins override semantics as the preset path, resolves the palette via `palette_from_colors`, then adds the effect — sharing the extracted merge and timing/target guards with `place_preset` so the two paths never drift.

#### Scenario: Place a preset
- **WHEN** a caller places an effect by look, knob values, and palette
- **THEN** the system assembles a valid settings string (rejecting any out-of-constraint knob value) and places the effect with that palette

#### Scenario: Raw placement is gated
- **WHEN** a caller uses the raw-settings path
- **THEN** it is clearly distinguished from preset-backed placement

#### Scenario: Place a code-templated direct effect
- **WHEN** a caller places an asset-bound effect via `place_direct` with a builder-produced settings string, optional palette colors, and optional `extra_settings`
- **THEN** the system validates the string syntactically, merges `extra_settings` with the same override precedence as `place_preset`, colors it via `palette_from_colors`, and adds the effect — raising `PresetPlacementError` on `worked=false` and `ValueError` on bad timing/target

#### Scenario: The direct and preset paths share behavior
- **WHEN** the same `extra_settings` are supplied to `place_direct` and `place_preset`
- **THEN** both produce identical merged settings and identical palette handling, because the merge and guard logic is shared (extracted helpers, not copies) and the preset path's existing tests and the golden fixture pass unchanged

### Requirement: Validate a preset against a running xLights
The system SHALL validate a preset by placing it on a dedicated scratch sequence in a running xLights, rendering, and reporting whether it was accepted — where accepted means the effect was added (placement reported as worked) and the sequence rendered successfully. Validation SHALL require that no user sequence is open and SHALL NOT discard the user's work to make room. The system SHALL provide the same scratch-sequence validation for a code-templated direct effect (`validate_direct`) — clean slate, place the frozen template, render, assert it was accepted — used once per template per xLights upgrade rather than per run.

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

#### Scenario: A direct template is validated live
- **WHEN** `validate_direct` places the frozen Text template on the Matrix model of a scratch sequence and renders
- **THEN** it reports whether the placement worked and the render succeeded, on the same clean-slate protocol as `validate_preset`, and is invoked per template per xLights upgrade rather than per show run
