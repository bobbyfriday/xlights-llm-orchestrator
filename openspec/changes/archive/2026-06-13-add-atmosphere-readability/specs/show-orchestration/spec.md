## ADDED Requirements

### Requirement: Atmospheric features read against their base
When a sparse, transparent-background feature effect (such as Snowflakes, Snowstorm, Meteors, Twinkle, or Fireworks) coexists with an opaque wash bed (On, Color Wash, or Fill) on the same element and overlaps it in time, the orchestrator SHALL cap that bed's brightness at a low glow level so the feature remains visible. The cap SHALL never brighten a bed (a bed already dimmer than the glow is left unchanged), and SHALL skip a bed that carries a blend mode (a composited add such as a beat accent, not an occluding wash).

#### Scenario: A wash over snowflakes is capped to a glow
- **WHEN** a section places a sparse atmospheric feature on the same group as an On/Color Wash/Fill bed that overlaps it in time, and the bed's brightness is above the glow level
- **THEN** the bed is capped to the glow level so the feature reads against it instead of being washed out

#### Scenario: An already-dim bed is preserved
- **WHEN** the bed under an atmospheric feature is already dimmer than the glow level
- **THEN** the bed's brightness is left unchanged

#### Scenario: A blended accent is preserved
- **WHEN** the bed-type effect carries a blend mode (e.g. a Max-blend beat accent)
- **THEN** its brightness is left unchanged

#### Scenario: No atmospheric feature
- **WHEN** a section has no sparse/atmospheric feature coexisting with a bed
- **THEN** beds realize as before
