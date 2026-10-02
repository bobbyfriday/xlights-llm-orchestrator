## ADDED Requirements

### Requirement: Rotational effects support signed direction
The system SHALL map the abstract directions `ltr`/`rtl` to effect-native signed rotation settings for the rotational effects Spirals and Ripple (joining the already-mapped Pinwheel and Butterfly), using only corpus-observed setting keys, so that a requested direction on these effects is realized rather than silently dropped. Spin-kind motion value curves SHALL support a negative direction.

#### Scenario: A directed Spirals cell spins the requested way
- **WHEN** a weave cell recipe places Spirals with `direction: "rtl"`
- **THEN** the resulting instruction carries a negative `E_SLIDER_Spirals_Rotation` in its extra settings, overriding the look's frozen rotation at emit

#### Scenario: Per-bar alternation now applies to rotational effects
- **WHEN** a Spirals cell recipe uses `direction: "alternate"`
- **THEN** successive bars carry opposite-sign rotation values (the existing ltr/rtl per-bar flip, now resolvable for Spirals)

#### Scenario: A negative spin curve
- **WHEN** a spin-kind motion curve is requested with a negative sign
- **THEN** the emitted value curve ramps from 0 toward the parameter's negative bound, scaled by intensity

### Requirement: Same-type rotational stacks counter-rotate
When two or more instances of the SAME rotational effect (Spirals, Ripple, Pinwheel, Butterfly) overlap in time on the SAME target on different layers, the system SHALL deterministically assign opposite spin directions to successive layers — in all three placement paths (weave recipes, composite layers, generator instructions) — unless a layer carries an explicit direction, which SHALL be respected. (Community corpus: 47% of stacked Spirals pairs and 30% of stacked Pinwheel pairs run opposite directions; ours previously 0%.)

#### Scenario: Generator stacks two Spirals on the hero
- **WHEN** the generator emits two overlapping Spirals instructions on the same group and neither specifies a rotation
- **THEN** the upper layer receives the opposite spin setting from the lower layer

#### Scenario: An explicit direction is never overridden
- **WHEN** a stacked rotational instruction already carries its effect's direction key (from an LLM recipe or scene row)
- **THEN** the counter-rotation pass leaves that instruction unchanged

#### Scenario: Deterministic across runs
- **WHEN** the same instruction list is realized twice
- **THEN** the assigned spin directions are identical (no randomness; order-derived)

### Requirement: Curated composites produce real motion contrast
Every curated composite stack that combines two motion layers SHALL use direction/blend settings that are actually mapped for its effect types — a composite MUST NOT claim counter-motion through direction values that resolve to no settings.

#### Scenario: The kaleidoscope peak composite counter-rotates
- **WHEN** the peak composite `kaleidoscope` is expanded on the hero group
- **THEN** it emits two Spirals layers with opposite-sign rotation settings and a Max blend on the upper layer

#### Scenario: The bloom composite's directions resolve
- **WHEN** the `bloom` composite is expanded
- **THEN** every layer's direction resolves to a non-empty effect-native setting (Spirals signed rotation; Fan center_out)
