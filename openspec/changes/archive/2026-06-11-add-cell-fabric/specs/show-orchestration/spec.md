## ADDED Requirements

### Requirement: Sections are woven from beat-quantized cell recipes
Section generation SHALL realize sections as short, beat-quantized effect cells expanded deterministically from per-section cell recipes. The recipes — effect types, target groups, alternation pattern, cell length in beats, blend mode, motion value curve, and in/out transition — SHALL be directable by the generation LLM, with a deterministic fallback weave when recipes are absent or invalid. Cell timing SHALL snap to the section's real beat grid.

#### Scenario: LLM recipes expand into beat-snapped cells
- **WHEN** a section's generation output includes cell recipes (e.g. a SingleStrand chase carrier over the rhythm groups at 1 beat per cell)
- **THEN** the pipeline emits one effect instruction per cell slot, with boundaries on the section's beat times, targets rotating across the recipe's groups per its alternation pattern, and the section palette realized per cell

#### Scenario: Fallback weave when the LLM omits recipes
- **WHEN** a section's generation output carries no weave (or its recipes reference no valid groups)
- **THEN** a deterministic default weave (a motion-effect beat carrier over the rhythm groups) is expanded instead, and generation never fails or skips for lack of recipes

#### Scenario: Cell settings carry blend, curve, and transition keys
- **WHEN** a recipe specifies a blend mode, a motion curve, or a transition
- **THEN** the expanded cells carry the corresponding corpus-verified settings keys (layer blend on the upper layer; motion value curve on the effect's own parameter; in/out transition type), and unknown curve/effect combinations degrade to no extra keys rather than a placement failure

### Requirement: Cell density is bounded and scales with intensity
The number of woven cells per section SHALL be bounded by a budget that scales with section intensity and length, with even downsampling when recipes exceed it, so quiet sections weave sparsely and peaks approach community density without unbounded placement counts.

#### Scenario: Quiet vs peak density
- **WHEN** two equal-length sections weave the same recipes at intensity 0.2 and 1.0
- **THEN** the quiet section expands materially fewer cells than the peak section, and both stay within their budgets

### Requirement: The deterministic beat layer defers to a covering carrier
WHEN a section's weave contains a carrier recipe whose groups cover the rhythm pool, the deterministic beat-accent layer SHALL NOT also place its every-beat chase on those groups (downbeat sparkle and hero-onset accents remain), so the beat is carried once, not doubled.

#### Scenario: No doubled beat chase
- **WHEN** a section weaves a carrier recipe over the rhythm groups
- **THEN** the beat-accent pass emits no every-beat chase instructions for that section, while its downbeat sparkle and hero onset layers still place

### Requirement: Motion-effect share is surfaced to QA as an advisory
The placement-rules QA SHALL surface, per energetic section, an advisory finding when the share of continuous-motion effects among that section's placements falls below a threshold, visible to the Judge but never gating the objective score.

#### Scenario: Static section flagged
- **WHEN** an intensity ≥ 0.5 section's placements are predominantly static/punctuation effects
- **THEN** the QA report contains an advisory motion-share finding scoped to that section, and the objective score is unchanged by it
