## ADDED Requirements

### Requirement: Section palettes are contrast-floored at realization

After the show-level color script has finalized the section palettes, the pipeline SHALL floor
each section palette for LED legibility: when the palette's chromatic hues all cluster within the
minimum hue spread (60°), a complementary anchor color SHALL be injected into the section palette
before effects are generated, so the wash and multi-color effects span hues — not just the rhythm
layer's alternation pair. All-achromatic palettes (whites/grays only) SHALL pass through
unchanged, preserving deliberate white-dominant looks. The floor SHALL be deterministic and
idempotent, and the injected color SHALL be snapped to the nearest chromatic named color when one
is hue-close, falling back to the raw complement hex otherwise.

#### Scenario: All-warm palette gains a cool anchor

- **WHEN** a section's palette is gold + amber + warm white and effects are generated
- **THEN** the realized section palette contains one added complementary color and its chromatic
  hue spread is at least 60°, and the wash/multi-color effects draw from the floored palette

#### Scenario: White-dominant palette is left alone

- **WHEN** a section's palette contains only achromatic colors (e.g. warm white + white)
- **THEN** no color is injected and the palette is unchanged

#### Scenario: Already-contrasting palette is left alone

- **WHEN** a section's palette already spans at least 60° of chromatic hue
- **THEN** the palette is unchanged

#### Scenario: The floor is idempotent

- **WHEN** the floor pass runs again on an already-floored plan (cache reuse, refine-loop
  re-script)
- **THEN** no additional colors are injected

## MODIFIED Requirements

### Requirement: Beat accents contrast the wash

Beat accents SHALL be colored to contrast the section's wash, rather than reusing the wash's
colors. When the section palette carries no chromatic color at all, the accent alternation pair
SHALL contrast by value — the two most value-separated colors, synthesizing a dimmed variant of
the brightest color when every color is near-white — never two near-white colors.

#### Scenario: Multi-color section

- **WHEN** a section has two or more colors
- **THEN** the wash uses the calmer/darker colors and the beat accents use a brighter, distinct color

#### Scenario: Single-color section

- **WHEN** a section has one color
- **THEN** the beat accents use a brightened/contrasting variant so they still read against the wash

#### Scenario: All-achromatic section

- **WHEN** a section's palette contains only whites/grays (no chromatic color)
- **THEN** the accent alternation pair separates by value (e.g. white against a dimmed variant),
  not two near-white colors, and no hue is injected
