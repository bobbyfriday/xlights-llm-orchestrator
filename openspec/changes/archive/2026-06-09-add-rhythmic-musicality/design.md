## Context

`place_beat_accents` (post-visibility) places an every-beat chase on `04_BEAT_*` in the `split_palette` accent color, downbeat = all groups. `section_rhythm` returns `beats_ms`, `prominent_stem`, `onsets_by_stem`. Unused: `SongAnalysis.chords` (`Chord{time,label}`, 193), `section.intensity`. Hero groups `08_HERO_*` are targetable. All changes stay deterministic in `beats.py`.

## Goals / Non-Goals

**Goals:** density that scales with intensity; a hero prop following the prominent stem's onsets; accent color that steps on chord changes. Additive, bounded, hermetic-testable.

**Non-Goals:** wash effect/look or wash-color-over-time; melody following; new effect types; chord re-derivation; bar detection.

## Decisions

### `section_rhythm` surfaces section chords
Add `chords_ms: list[(int ms, str label)]` (the song chords filtered to `[start_ms,end_ms)`, sorted) to the returned dict, from `sa.chords`. Empty when no chords.

### Energy-scaled density (intensity → off-beat keep)
Downbeats are always placed. For the OFF-beats, keep a fraction by `section.intensity`:
- `intensity ≤ 0.30` → keep 0 off-beats (downbeats only — sparse, calm).
- `0.30 < intensity ≤ 0.65` → keep every other off-beat.
- `intensity > 0.65` → keep all off-beats (every beat).
Implement by selecting off-beat indices with a stride from intensity (`stride = 1` dense, `2` mid, `∞`/none sparse). Still bounded by `MAX_ACCENTS_PER_SECTION` (downbeats first, then off-beats).

### Hero onset layer (follow the prominent stem)
`hero = first 08_HERO_* in available_groups else section.target_groups[0]`. Place short accents on `hero` at the prominent stem's in-window onsets (`onsets_by_stem[follow_stem]`), `_downsample`d to a bound (≤ `MAX_ACCENTS_PER_SECTION`), in the accent color, tagged `section_index`. Skip when no prominent stem/onsets or no hero. Additive to the `04_BEAT` chase (a different group, so no layer clash; the emitter bumps layers if needed).

### Chord-driven accent color
`_chord_color(t, chords_ms, colors)`: find the active chord index at `t` (rightmost chord whose time ≤ t via bisect); return `colors[idx % len(colors)]`. `colors` = the section's full realized palette (base + accent hexes from `split_palette`, deduped) so the accent steps through the section's own colors as harmony moves. When `chords_ms` is empty → return the single accent color (today's behavior). Apply to BOTH the beat chase and the hero onset hits, per-accent by its start time.

### Wiring
`place_beat_accents` gains the intensity gate on off-beats, the chord-color per accent, and appends the hero onset layer. Run.py is unchanged (it already calls `place_beat_accents(section, section_rhythm(...), available_groups)`).

## Risks / Trade-offs

- **More effects (hero layer)** — bounded by `_downsample` to ≤ cap; total still ~beat layer + ≤cap hero hits + washes. Live check asserts the total stays sane.
- **Chord color vs the base/accent contrast** — stepping through base+accent means some accents take a *base* (darker) color and may contrast the wash less at that moment; acceptable (it's the harmony moving), and the brightest accent still recurs. Could restrict to brighter colors later.
- **"N" (no-chord) spans** — treated as just another index; color still steps. Fine (it's a real harmonic state).
- **Intensity buckets are coarse** — 3 bands; a continuous map is possible later. Downbeats-always keeps even calm sections legible.
- **Hero layentry clash** — hero is usually NOT a `04_BEAT` group, so the two layers target different props; if a section's hero == a pulse group, the emitter's `_free_layer` handles overlap.

## Open Questions

- Continuous intensity→density vs 3 bands — start banded.
- Restrict chord-color cycling to the brighter (accent-ish) colors to preserve contrast vs use the full palette — start full; revisit if accents disappear into the wash on base-colored chords.
