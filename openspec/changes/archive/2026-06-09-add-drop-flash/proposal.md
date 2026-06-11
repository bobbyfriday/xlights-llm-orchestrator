## Why
The guide calls the drop "the single biggest visual moment," with the formula *"brief blackout/held strobe → white flash → full motion."* We compute `key_moments` (accent/climax) but don't punctuate them. This adds the **white flash** — a brief full-display white hit at climax/accent moments — the cheapest, highest-impact punctuation. (Call-and-response needs no new code: the beat chase already rotates `pulse_groups`, so the Director sets them to `02_GEO_Left/Right`.)

## What Changes
- A deterministic pass that places a **short white flash** across the targetable groups at each climax/accent `key_moment`, so the show hits hard on its biggest moments.

**Non-goals:** the pre-flash blackout (needs the beat layer to clear a gap — revisit); strobe holds; call-and-response code (enabled via existing `pulse_groups`).

## Capabilities
### Modified Capabilities
- `show-orchestration`: the show's climax/accent key-moments are punctuated with a brief full-display white flash, so the biggest moments land.

## Impact
- **`xlights-orchestrator`**: a `key_moment_flashes(show_plan, available_groups)` pass appended to the generated instructions in `run.py`. Reuses the On effect + white palette.
- **Builds on** `ShowPlan.key_moments` and the targetable-group set.
