## Context

`direction_setting(effect, direction, bar)` already flips static-direction values at bar boundaries for `bounce`; recipes carry no phase, and static `ltr`/`rtl` never flip. The carol weave's two SEM_ARCHES recipes (Left-Right + Right-Left, same groups, stacked layers) therefore cross constantly.

## Goals / Non-Goals

**Goals:** opposite-pair recipes swap directions each bar in opposite phase; an explicit `alternate` value with deterministic phase stagger; zero change to everything else. **Non-Goals:** new schema fields (phase is derived, not LLM-set); vertical counter-phase (up/down pairs — note as future if wanted); per-beat (vs per-bar) swapping.

## Decisions

**D1 — Phase is DERIVED, not a recipe field.** In `_valid_recipes`, after validation: pair chase-family recipes whose groups OVERLAP (live run 8 showed the real pattern is a pool-chasing carrier vs a single-group texture — equality was too strict) and whose EFFECTIVE directions are opposite. Effective direction = the recipe's field, else the direction implied by its resolved look's own chase-type value (frozen or knob default) — in practice the LLM builds crossing chases by picking two OPPOSED LOOKS with empty direction fields. Paired recipes are rewritten to `alternate` with phases 0/1; explicit `alternate` recipes stagger by order. Phase rides a parallel dict into `_cell`; the emitted setting overrides the look's frozen value via the placement override machinery.

**D2 — `alternate` realization**: `direction_setting(effect, "alternate", bar + phase)` = the existing static-flip path (ltr on even, rtl on odd), bypassing native-bounce types (Dual Bounce stays exclusive to `bounce`). Effects lacking an ltr/rtl pair fall back to their up/down pair, else no-op — same degradation ladder as `bounce`.

**D3 — Swap at BAR boundaries** (not per cell): sweep cells are ≥2 beats; a bar-period swap gives each direction a full traverse before reversing — the "cross, bounce, cross back" figure. Same `_BEATS_PER_BAR` derivation as everything else.

## Risks / Trade-offs

- [Upgrade fires on an intentional constant-cross design] → the pair pattern (exact same groups, exactly opposite static directions) is overwhelmingly the LLM reaching for "crossing chases"; if a constant cross is ever wanted, the recipes can use different group orderings or one layer `bounce`. Accepted.
- [Phase misalignment when cell_beats differ between the pair] → bar index derives from each recipe's own slots; identical groups + chase family ⇒ floored to the same ≥2 beats; a mismatched pair (2 vs 4) still swaps on bar boundaries, just with different cell granularity — musically coherent. Tested.

## Migration Plan

Weaver-only; rides the PR train. Rollback = revert.

## Open Questions

- Whether the accent layer's bar-alternating walk should counter-phase against the carrier sweep (opposing layers of motion) — deferred until the user sees this change.
