## ADDED Requirements

### Requirement: Render a still preview offline (no xLights)
The system SHALL produce a still image of the show at a given time from the compiled render data and the layout geometry, without depending on the running xLights application.

#### Scenario: Render a frame
- **WHEN** a timestamp is requested with the show's compiled render data and layout available
- **THEN** the system returns a still image positioning each model's lit pixels by their layout geometry at that moment

#### Scenario: No xLights dependency
- **WHEN** the preview is rendered
- **THEN** it is produced entirely from on-disk artifacts (compiled render data + layout), with the xLights application neither running nor contacted

### Requirement: Resolve channels and geometry from the layout
The system SHALL map each model's channels to the compiled render data (resolving controller-relative start channels to absolute) and place each model's pixels using its declared geometry and scale.

#### Scenario: Channel resolution
- **WHEN** a model's start channel is controller-relative
- **THEN** it is resolved to an absolute index into the render data using the controller channel ranges

#### Scenario: Geometry placement
- **WHEN** models of different layout types (e.g. matrix, arch, boxed) are placed
- **THEN** each is positioned according to its type's geometry and scale convention

### Requirement: Critique rendered frames into scoped findings
The system SHALL critique one or more rendered frames with a multimodal model, given the show's creative intent, and return scoped findings (naming the affected section/area and a concrete issue/fix).

#### Scenario: Visual findings
- **WHEN** rendered frames and the show intent are given to the visual critic
- **THEN** it returns findings that identify visual problems (e.g. dark/empty areas, poor coverage, monotony) scoped to where they occur

#### Scenario: Frames sampled across the show
- **WHEN** frames are selected for critique
- **THEN** they represent multiple sections of the show (not a single moment)

### Requirement: The refine loop consults the visual critic before escalating to a human
The system SHALL consult the visual critic during refinement and incorporate its findings into the decision, escalating to a human only when the visual critic, deterministic QA, or the Judge flags an issue.

#### Scenario: Models evaluate first
- **WHEN** a draft is evaluated in the refine loop
- **THEN** the visual critic's findings are considered alongside the deterministic QA and Judge before any human is asked

#### Scenario: Escalate only on flagged issues
- **WHEN** the visual critic and the other checks find nothing to fix
- **THEN** the loop does not escalate to a human for that iteration

### Requirement: Visual critique is optional and degrades gracefully
The system SHALL treat visual critique as optional: when the compiled render data is unavailable or rendering fails, refinement continues using the deterministic QA and text Judge.

#### Scenario: Missing render data
- **WHEN** the show's compiled render data is not available
- **THEN** the visual critic is skipped and refinement proceeds without it
