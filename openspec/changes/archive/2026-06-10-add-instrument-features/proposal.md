## Why
At 2:07 a guitar tears in (stem energy 39%→65% of peak, 52 onsets in 10s) and the show ignores it — the rhythm machinery is per-SECTION (one `follow_stem` for 36s), so a mid-section instrument entrance is invisible. The guide's instruction: feature the entering instrument on a hero prop ("the solo prop is the soloist"). All the data needed (per-stem energy arcs + onsets) already exists, song-agnostically.

## What Changes
- **Entrance detection** (deterministic, every song): scan each stem's energy arc for a sustained surge (≥1.5× prior level, crossing 40% of the stem's peak) → `(t_ms, stem)` entrance events, debounced per stem.
- **A feature layer**: at each entrance, the focal prop rides THAT stem's onsets for ~10s with an instrument-appropriate catalog effect (guitar→Lightning, piano→Meteors, drums→Shockwave, bass→On pulses; quiet sections → Twinkle), in the section's accent color. Survives refine regens (untagged, like the climax flashes).
- **Entrances surface as `key_moments`** (kind="entrance") so the Director/Judge see them.
- **Housekeeping**: the instructions cache is rewritten after refine (today a cached re-run resurrects pre-refine instructions).

**Non-goals:** melody following; per-stem color; vocal entrances driving faces (needs Faces presets); changing the per-section follow_stem machinery.

## Capabilities
### Modified Capabilities
- `show-orchestration`: instrument entrances are detected from the stems and featured on a hero prop riding the entering instrument's onsets — mid-section musical events get a visual answer.
