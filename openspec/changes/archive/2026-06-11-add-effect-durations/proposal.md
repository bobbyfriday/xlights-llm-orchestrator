## Why
The effects catalog has energy bands and prop affinities but NO duration semantics — and the evidence is on screen: Shockwave (a ≤1-bar impact gesture) placed as an 88.6-second section wash reads as one slow weird ring; flat 88s On washes read static. The user's critique: effects have a natural longevity (hit / phrase / sustained), and the show needs MORE SHORT effects on beats/bars, not fewer long ones.

## What Changes
- **Duration classes** for every placeable effect: `HIT` (≤1 bar: Shockwave, Strobe, Lightning), `PHRASE` (≤8 bars: Curtain, Fill, Morph, Fan, Fireworks, Shimmer), `SUSTAINED` (unbounded: Spirals, Wave, Plasma, On, Twinkle…). Encoded in code AND added to the catalog (§2.1 + placement rule, v0.2) so the LLM sees it too.
- **A deterministic duration-normalization pass**: a HIT-class effect spanning >1.5 bars is CONVERTED into per-bar short cells (same look/colors — the section pulses with it instead of smearing it); a PHRASE-class effect is clamped to 8 bars (one gesture, the bed carries the rest).
- **Generator guidance**: hit effects are punctuation, never washes; prefer several short effects over one long static wash.

**Non-goals:** segmenting SUSTAINED washes over time (parked variation work); changing the accent layers (already short).

## Capabilities
### Modified Capabilities
- `show-orchestration`: effects respect their natural duration class — impact effects become per-bar pulses instead of section-long smears, phrase effects are bounded — so sections read as motion, not held poses.
