## Context

The snowflakes-don't-show bug is two problems: (1) contrast — silver flakes on a navy house read as one dark mass; (2) effect choice — the "Snowflakes" particle effect is built for a large canvas and renders nothing on small per-model flake props. Both are choices the LLM makes (palette, effect_type, render_style), so the fix lives in the prompts. The user chose to STEER, not hard-enforce, to keep the "don't guarantee the chosen effects land" principle.

## Goals / Non-Goals

**Goals:** featured sparkle/snow prop groups reliably read as a bright, high-contrast focal element (white-on-blue); the LLM still drives the rest. **Non-Goals:** changing the brightness machinery (the prior dim approach was wrong); forcing color on non-feature groups.

> **Decision update:** the change began as steering-only (the user's first choice). Verification across multiple regens showed the LLM does not reliably honor the steering — silver On, ice-white Twinkle on a near-black plan, dropped snow, blue chases. The user then opted to ADD a small deterministic color floor (D6) on top of the steering. Steering + palette-respect remain; the floor guarantees the outcome.

## Decisions

**D1 — Steer at both design and realization.** The Director sets the intent (which group is the feature, its color vs the bed's); the Generator realizes it (bright On/Twinkle in white over a blue bed) and avoids the particle-effect trap. Putting it in both places means the intent survives even if one stage under-specifies.

**D2 — Name the concrete failure mode.** The prompts call out the exact anti-pattern ("silver flakes on a navy house") and the exact fix ("white flakes on a blue house"), because the abstract "use contrast" guidance already exists and didn't prevent this. Concrete beats abstract for prompt steering.

**D3 — Particle-effect caveat is realization-level.** Only the Generator (which sets effect_type + render_style) gets the "Snowflakes/Snowstorm/Meteors need a large canvas; on small props light them directly" note — the Director works in archetypes, not effect types.

**D4 — No deterministic guarantee.** Verification is "does it land on a regen," not a unit assertion of output — consistent with steering. A light test asserts the guidance strings are present in the prompts so they can't silently regress.

**D5 — Respect the LLM's explicit color (the enabling fix).** Discovered during verification: `run.py` overwrote EVERY instruction's `palette_colors` with `effect_palette(section.palette, type, index)` — an index-rotated section palette. So even when the LLM (correctly steered) lit the snow props with On in white, the rotation reassigned silver at that index. Pure prompt-steering could not win the color. The fix respects an explicitly-set `palette_colors` (fill only when empty), so the LLM's pinned white survives. This is the realization half of "steer the LLM": it removes a code override that was discarding the LLM's color judgment, rather than adding a code color rule. `effect_palette` remains the default for every instruction the LLM doesn't pin, preserving the concurrent-effect color variety it provides.

**D6 — Deterministic contrast floor (the reliability fix).** `feature_prop_contrast(instructions, section)`: when an accent/sparkle prop group (ACCENT_GROUPS = SEM_SNOWFLAKES, SEM_SPINNERS) is in `section.target_groups`, recolor its base-lighting effects (On/Twinkle/SingleStrand/Fill/Snowflakes/…) to the section's LIGHTEST resolved palette color (by `_luminance`) and raise brightness to `FEATURE_PROP_BRIGHTNESS` (150) if lower. Scoped tightly: only the accent prop groups, only base-lighting effect types, only when the group is featured — the LLM owns everything else. "Lightest of the section palette" adapts per song (white for a cool Christmas palette, light amber for a warm one) so it's a contrast floor, not a hard-coded white. Applied per section in both the generate and regen paths, after the LLM instructions + beds + accents are assembled.

## Risks / Trade-offs

- [Steering may not land every time] → accepted by the user's choice; if it proves unreliable we can revisit a contrast floor (the rejected "code" option) as a follow-up.
- [The caveat discourages legitimate particle use on real matrices] → the caveat is scoped to "small dedicated props" and explicitly blesses particle effects on large/Matrix canvases.

## Migration Plan

Prompt-only; additive. Branch `change/add-feature-prop-contrast`, PR (user merges). Verify by regenerating Christmas Canon's snow sections and confirming the flakes read.

## Open Questions

- Whether a future change should add a deterministic contrast floor for feature props if steering proves unreliable across songs.
