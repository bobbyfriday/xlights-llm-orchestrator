## ADDED Requirements

### Requirement: Featured accent/sparkle prop groups are steered to pop
When a section's look centers on a dedicated accent/sparkle prop group (such as SEM_SNOWFLAKES or SEM_SPINNERS), the creative-direction prompts SHALL steer those props to be the bright, high-contrast focal element in a light color over a different-hued background bed (e.g. white snowflakes on a blue house), kept bright even in a calm section. The generator prompt SHALL also steer away from named particle effects (Snowflakes/Snowstorm/Meteors) on small dedicated props — which render nothing visible there — toward lighting the props directly, reserving particle effects for a large canvas with a high count. This is steering, not a deterministic guarantee.

#### Scenario: Snow section steered to white-on-blue
- **WHEN** the Director and Generator compose a section that features the snowflake props
- **THEN** their prompts direct the snow props to a bright light color over a contrasting bed, and direct against a particle effect that won't render on the small props

#### Scenario: Particle effects still allowed on a real canvas
- **WHEN** a section uses a particle effect on a large whole-house or Matrix canvas
- **THEN** the guidance does not discourage it (the caveat is scoped to small dedicated props)

### Requirement: An instruction's explicit color is respected
When an effect instruction carries an explicitly-chosen `palette_colors`, the orchestrator SHALL use those colors as-is rather than overwriting them with the index-rotated section palette. An instruction with no explicit `palette_colors` SHALL receive the section-palette family as before.

#### Scenario: A pinned feature color survives
- **WHEN** the generator sets `palette_colors` (e.g. white) on a feature-prop instruction
- **THEN** that color is used as-is and is not replaced by the section-palette rotation

#### Scenario: Unpinned instructions take the section family
- **WHEN** an instruction has no explicit `palette_colors`
- **THEN** it receives the expanded section palette exactly as before

### Requirement: Featured sparkle/snow props have a deterministic contrast floor
When a dedicated sparkle/snow prop group (SEM_SNOWFLAKES or SEM_SPINNERS) is among a section's target groups, the orchestrator SHALL recolor that group's base-lighting effects to the section's lightest resolved palette color and raise their brightness to a bright level, so the feature pops against the bed regardless of the LLM's color choice. This floor SHALL apply only to those accent prop groups and only when they are featured; all other groups and effect choices remain the LLM's.

#### Scenario: Snow props forced to the lightest color, bright
- **WHEN** a section targets SEM_SNOWFLAKES with a palette containing a light color
- **THEN** the snowflake props' base lighting is set to that lightest color at a bright level, while the bed and other groups keep their colors

#### Scenario: No accent group featured
- **WHEN** a section does not target a sparkle/snow prop group
- **THEN** the floor makes no change

