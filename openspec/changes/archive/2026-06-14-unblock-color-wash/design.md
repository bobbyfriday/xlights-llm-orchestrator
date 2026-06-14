## Context

`KNOWN_REJECTED_TYPES = {"Color Wash"}` filters Color Wash out of `placeable_effect_types()`. The exclusion was based on `addEffect` `worked=false`. Live re-test on the open canon sequence (SEM_ARCHES target, clean far-future slot, layer 9):

| name | settings | palette | worked |
|---|---|---|---|
| `Color Wash` | — | — | **true** |
| `Color Wash` | — | red/green | **true** |
| `ColorWash` | — | — | false |
| `Color wash` | — | red/green | false |

`renderAll` after placement succeeded. So the exact UI name `"Color Wash"` (with the space) places and renders; the failure was the transport, not the effect.

## Goals / Non-Goals

**Goals:** make Color Wash available (director + brief schema), keep the reject mechanism for real future cases, correct the stale guidance/memory. **Non-Goals:** forcing the director to use washes; reworking the scene-cookbook substitution doctrine (harmless if left); auditing other names (Color Wash is the only entry, and the only multi-word corpus effect that the `+` bug would have hit).

## Decisions

**D1 — Empty the set, keep the mechanism.** `KNOWN_REJECTED_TYPES: set[str] = set()` with a comment recording the re-verification. Future genuinely-unplaceable types can be re-added; the filter in `placeable_effect_types()` is unchanged.

**D2 — Trust the `worked` flag + render, as the original exclusion did.** The exclusion criterion was `worked`; it now passes, plus `renderAll` is clean — same bar, opposite result. No deeper change warranted.

**D3 — Fix the now-false example, leave the doctrine.** The generator's "Color Wash bed → dim On" substitution *example* is now factually wrong (Color Wash is placeable); reword it. The broader "substitute a non-candidate effect" rule stays — it's still correct for any effect not in a section's candidates.

## Risks / Trade-offs

- [Color Wash places but renders wrong in some buffer/style] → re-test showed a clean `renderAll`; if a specific style misbehaves it's a per-look issue, not a reason to blanket-block.
- [The re-test is environment-specific] → it ran against the user's live xLights (same build that rejected it before), so it's apples-to-apples; the encoding fix is the documented cause.

## Migration Plan

Additive. Branch `change/unblock-color-wash`, PR (user merges). A song re-run picks up Color Wash automatically.

## Open Questions

- Whether the scene cookbook / guides should now *recommend* Color Wash for beds (they currently steer around it) — a content tweak, deferred.
