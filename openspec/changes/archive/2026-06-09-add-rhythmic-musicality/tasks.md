## 1. Surface chords

- [x] 1.1 `section_rhythm` adds `chords_ms: list[(int, str)]` — `sa.chords` filtered to `[start_ms,end_ms)`, sorted by time (empty when absent)

## 2. Energy-scaled density

- [x] 2.1 In `place_beat_accents` (beat mode): always keep downbeats; for off-beats select by an intensity-derived stride — `intensity ≤ 0.30` → none; `≤ 0.65` → every other; else all. Still bounded by `MAX_ACCENTS_PER_SECTION` (downbeats first)

## 3. Hero onset layer

- [x] 3.1 `hero = next 08_HERO_* in available_groups else section.target_groups[0]`; place short accents on `hero` at the prominent stem's in-window onsets (`_downsample` to ≤ cap), accent color, tagged `section_index`; skip when no stem/onsets/hero. Append to the beat chase

## 4. Chord-driven accent color

- [x] 4.1 `_chord_color(t, chords_ms, colors)`: active-chord index at `t` (bisect rightmost ≤ t) → `colors[idx % len]`; `colors` = section's base+accent hexes (deduped); empty chords → the single accent color
- [x] 4.2 Apply per-accent (by start time) to BOTH the beat chase and the hero onset hits

## 5. Tests & verification

- [x] 5.1 Energy: intensity 0.2 → far fewer accents than intensity 0.9 (same beats); both keep downbeats
- [x] 5.2 Hero layer: prominent stem + onsets → extra accents on the hero group at onset times (bounded); none when no stem; hero prefers `08_HERO_*`
- [x] 5.3 Chord color: accents in different chord spans get different colors (cycles); single accent color when no chords
- [x] 5.4 Bounds + downbeat emphasis preserved; existing beat/visibility/palette tests still pass
- [x] 5.5 Live (combined re-run with improve-beat-visibility): re-generate mad russian → quiet intro sparse / loud sections dense; a hero prop pulses on guitar/drums onsets; accent color shifts on chord changes; bounded count, no new skips, beats still contrast the wash

> **Build result (verified live):** energy-scaled density (accents/section ramp 36→120 by intensity, downbeats always kept), hero onset layer on 08_HERO scaled by intensity (cap 40×intensity) following the prominent stem, chord-driven accent color cycling BRIGHTENED palette colors (preserves contrast, steps with harmony). 162 tests pass; placed 1268/2 skipped. Fixed two self-inflicted regressions found in the first re-run (chord-cycle reusing the wash color; hero layer 5× too dense).
