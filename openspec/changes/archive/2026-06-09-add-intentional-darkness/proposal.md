## Why
The guide's most-repeated principle: *"contrast creates impact,"* *"darkness is a tool,"* *"verses: 2–3 active groups max,"* *"the blackout before the drop is what sells it."* We light effectively every targetable group every section, so there's no restraint and no contrast. This adds energy-gated coverage so quiet sections go sparse/dark — the deterministic backstop that guarantees restraint even if the LLM over-fills.

## What Changes
- An **energy-gated coverage cap**: the number of prop groups lit by a section's wash scales with `section.intensity` — quiet sections light only a few (the rest stay dark), loud sections light many/all. Deterministic trim of the wash instructions (drop the lower-priority groups; preserve the Director's ordering).

**Non-goals:** true silence-detection blackouts and the pre-drop blackout (need silence windows that may not apply to this song — revisit with the drop work #5); changing brightness (#2) or the beat layer.

## Capabilities
### Modified Capabilities
- `show-orchestration`: the number of simultaneously-lit prop groups scales with section energy, so quiet sections are intentionally sparse/dark (contrast), not fully lit.

## Impact
- **`xlights-orchestrator`**: a coverage-trim pass in `run.py` on the wash instructions at both generate sites. Complements the guide-injected Director's restraint with a hard cap.
- **Builds on** normalized `section.intensity`. Pairs with #2 (brightness) for the full dynamic range.
