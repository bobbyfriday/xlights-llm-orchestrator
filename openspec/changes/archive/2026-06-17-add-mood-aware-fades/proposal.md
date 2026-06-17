## Why

In low-energy / introspective sections, the cell weaver snaps cells to abutting beat
boundaries (`[beat_i, beat_{i+1})`) with hard on/off edges and no fade. On a real render this
reads as staccato "flashing" — which the visual critic and Judge repeatedly flagged on the
Christmas Canon verses (sections 4 & 5: *"rapid, erratic flashing… contradicts the stagnant
melancholy"*), a defect the refine loop could not resolve because it is a realization gap, not a
brief gap. xLights already exposes effect-level fades (`T_TEXTCTRL_Fadein/Fadeout`) and in/out
transition types, but no code path synthesizes them by mood — fades are unused, and the existing
`CellRecipe.transition` plumbing is dormant (the LLM rarely sets it).

## What Changes

- Add an optional, defaulted **`phrasing`** dial to `SectionPlan` (`"legato" | "staccato" | ""`)
  that the **Director** sets as a per-section judgment: *legato* = evolving / soft, overlapping
  fades (introspective, melancholy); *staccato* = crisp on/off (energetic, peaks). The Director
  prompt is extended to choose it.
- The **weaver owns realization**: a `phrasing` value maps deterministically to a curated
  soft-edge *transition primitive* selected in code from the cell's effect family — a linear
  opacity fade (`T_TEXTCTRL_Fadein/Fadeout`, scaled to cell length) for line/chase effects, or a
  `Dissolve` transition type (`T_CHOICE_In/Out_Transition_Type`) for textural fills/washes where a
  grainy melt reads better — plus a longer effective `cell_beats`, so legato cells breathe and
  evolve instead of snapping. The Director picks only the mood; code picks the primitive and the
  numbers. The full xLights transition menu and Director-level transition selection stay out of
  scope (the menu's shaped reveals — Wipe/Clock/Star/Zoom — mostly don't read on sparse pixel
  props).
- **Energy-gated default**: when `phrasing` is blank, the weaver infers it from
  `SectionPlan.intensity` (low → legato, high → staccato), so silent runs and cached plans still
  do the right thing without a Director change.
- Delivered in two phases. **Phase 1** (this change): the curated soft-edge primitive (fade or
  dissolve) + longer cells — a dip-to-black "evolving" feel that is simple, hermetic, and the bulk
  of the win. **Phase 2** (deferred, noted in design): true cross-layer crossfade overlap, since
  two effects cannot overlap on a single xLights layer — a real crossfade requires alternating
  cells across two layers/groups.

## Capabilities

### New Capabilities
<!-- none — this refines existing weaver/director behavior -->

### Modified Capabilities
- `show-orchestration`: the cell-weaving requirements gain mood-aware phrasing — the Director
  may direct a section's phrasing, and the weaver realizes legato phrasing as soft effect-level
  fades (defaulting from section intensity when undirected).

## Impact

- `packages/xlights-orchestrator/.../show_plan.py` — new optional `SectionPlan.phrasing` field
  (additive, defaulted; back-compatible with cached plans).
- `packages/xlights-orchestrator/.../pipeline/weave.py` — a curated `effect_family → primitive`
  map and a `soft_edge_settings()` helper; `_cell()` synthesizes the fade or dissolve from the
  resolved phrasing (only when the recipe set no explicit transition); `expand_weave()` resolves
  phrasing (Director value or intensity-derived default) and may lengthen `cell_beats`.
- `packages/xlights-orchestrator/.../agents/director.py` — prompt guidance for choosing
  `phrasing` per section.
- Settings flow through the existing `EffectInstruction.extra_settings → place_preset` plumbing;
  no transport changes.
- Hermetic tests for the phrasing→params mapping, the intensity-gated default, and the fade math.
  Live-verify on `mp3/christmas canon.mp3` sections 4/5. Lands via PR.
