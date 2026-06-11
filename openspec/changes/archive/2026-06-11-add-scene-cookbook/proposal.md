## Why
The user authored `xlights-scene-cookbook.md` — named multi-prop scene recipes (SC-01 Standard Stack, SC-02 Counter-Rotating Spirals, SC-04 Drop Formula…) whose rows are display ARCHETYPES (G2-HERO, G2-RHYTHM, G0-ALL-LESS-HERO) to cast onto real groups — and began the wiring (guide registry entry, `SectionPlan.scene_id`/`scene_adaptation`). Sections composed from proven scenes beat freeform effect piles. This completes the loop.

## What Changes
- **Director** receives the cookbook and, per section, chooses a `scene_id` (or freeform) + a `scene_adaptation` casting the scene's archetype rows onto the real SEM_ groups.
- **Generator** receives the cookbook and realizes the chosen scene's stack (rows, layers, effects, render styles) using the adaptation.
- **Creative brief** renders the chosen scene per section for the human gate.
- **Subtractive groups** (cookbook §2 prerequisite): `SEM_ALL_LESS_FOCAL` and `SEM_ALL_LESS_FOCAL_RHYTHM` added to the layout-semantics builder (live after the next layout re-patch; the Director casts to nearest groups meanwhile).

**Non-goals:** deterministic scene compilation (the Generator realizes; scenes are guidance + structure, not templates); blend modes (addEffect has no blend param — layers blend Normal).

## Capabilities
### Modified Capabilities
- `show-orchestration`: sections are composed from the cookbook's named scenes — the Director picks and casts a scene per section, the Generator realizes its stack, and the brief shows the choices.
