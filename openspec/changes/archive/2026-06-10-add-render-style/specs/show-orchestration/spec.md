## ADDED Requirements

### Requirement: The Generator chooses each effect's render style
The Generator SHALL choose a render/buffer style per effect (informed by the layering guide), and that choice SHALL be applied to the placed effect.

#### Scenario: LLM-chosen style applied
- **WHEN** the Generator specifies a render style for an effect
- **THEN** the placed effect uses that buffer style

### Requirement: Render style is iterable in the refine loop
The render style SHALL be re-choosable when a section is regenerated, so the Generator can change it in response to critique (e.g. a section reading dark/sparse).

#### Scenario: Dark section regenerated
- **WHEN** the critic flags a section as dark/sparse and it is regenerated
- **THEN** the Generator may assign a different render style

### Requirement: No effect renders on the sparse default
When no render style is specified (or for code-generated effects), a deterministic fallback SHALL be applied so an effect is never left on the unset (sparse group-canvas) default.

#### Scenario: Unspecified style
- **WHEN** an effect has no chosen render style
- **THEN** a sensible default buffer style is applied
