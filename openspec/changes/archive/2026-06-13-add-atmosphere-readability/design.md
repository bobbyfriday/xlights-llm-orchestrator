## Context

In the saved Christmas Canon, SEM_SNOWFLAKES and SEM_ALL each have an `On` (layer 0, full span, no brightness key) under a `Snowflakes` layer. The On renders opaque at 100%; Snowflakes renders flakes on a transparent background. With the flake layer on top, the bed bleeds through the gaps and the net look is "lit yard with faint specks." The verified render rules rule out an ordering fix: within a model the top layer wins (snow is already on top), and across groups the lower master-view row wins (SEM_SNOWFLAKES is far below SEM_ALL). The only lever left is the bed's brightness/opacity.

## Goals / Non-Goals

**Goals:** an atmospheric feature (snow/meteors/twinkle/fireworks) reads against its base; the brief's "still glow" survives as a dim bed rather than a full wash; the change is surgical and deterministic. **Non-Goals:** changing render order or blend machinery; touching deliberate beds (peak/ensemble/flash); a general per-effect opacity model.

## Decisions

**D1 — Dim, don't drop.** The brief wants a glow under the snow, so the bed stays — dimmed to `GLOW_BRIGHTNESS` (30 on the 0–400 scale, i.e. ~30% of normal) via a static `C_SLIDER_Brightness`, not removed. A dim base reads as atmosphere; the sprites pop against it.

**D2 — Trigger = sparse feature ABOVE an opaque bed on the SAME element.** `ATMOSPHERIC = {Snowflakes, Snowstorm, Meteors, Twinkle, Fireworks}` (sprite/particle effects that render on a transparent/near-empty background). `BED_EFFECTS = {On, Color Wash, Fill}`. For each target element, if an ATMOSPHERIC instruction overlaps a BED instruction in time AND sits on a higher layer, the bed is dimmed. Same-element only: cross-group occlusion already resolves correctly via render order (SEM_SNOWFLAKES wins over SEM_ALL), and a group's own bed is what bleeds through its own feature.

**D3 — Cap, don't skip-on-brightness.** The first instinct — "skip any bed that already has a brightness key" — fails: `run.py` applies an intensity-keyed `wash_brightness` to EVERY section wash, so every bed carries a `C_SLIDER_Brightness` already. The real intro On is at 76 (intensity 0.2 → `wash_brightness` 76), not "bare" — and 76 is still bright enough to bleed through. So instead the pass **caps**: set the coexisting bed's brightness to `min(current, GLOW_BRIGHTNESS)`. Never brightens (a bed already below the glow is left alone); a Brightness value curve on the bed is dropped so the static glow takes effect. The only guard kept is **skip beds with a blend mode set** — a `T_CHOICE_LayerMethod` (e.g. a Max-blend beat accent) is a composited add, not an occluding Normal-blend wash.

Trade-off: a deliberate `peak_fill`/`ensemble_bed` that happens to sit under an atmospheric feature also gets capped. Accepted — if the brief features delicate sprites over that bed, letting them read is the right call, and the case is rare. The energy floor that would protect peaks isn't worth the coupling.

**D4 — Apply over the assembled instructions, and on cache-load.** `dim_beds_under_atmosphere(instructions)` runs in `run.py` after instructions are assembled (generate path, over the full list once; regen path, per section), mutating bed `extra_settings` in place before emit. It also runs on the cache-load branch — capping is idempotent, so pre-existing instruction caches get the fix on the next run without regeneration.

## Risks / Trade-offs

- [A peak section that features snow over a deliberate full bed stays bright → snow won't read there] → accepted and rare; the deliberate-brightness guard intentionally favors the peak. Atmospheric features over peaks are uncommon, and forcing a peak dim would defeat peak escalation.
- [Dimming makes a "glow" too dark on some props] → 30/400 is a deliberate glow, tuned to the brief; revisit the constant if live review wants brighter.

## Migration Plan

Additive; only bare beds under atmosphere change. Branch `change/add-atmosphere-readability`, PR (user merges).

## Open Questions

- Whether `Plasma`/`Galaxy`/`Fire` (buffer-filling, not sparse) ever want the same treatment — excluded for now since they aren't transparent-background; revisit if a filled feature reads washed out over a bed.
