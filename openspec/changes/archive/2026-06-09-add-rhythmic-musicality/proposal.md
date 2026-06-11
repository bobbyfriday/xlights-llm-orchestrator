## Why

After `improve-beat-visibility`, the beat layer is an every-beat chase on `04_BEAT_*` in a contrasting accent color with downbeat emphasis — visible and on-beat, but still **metronomic and uniform**. We extract rich timing data we don't use for the accents:
- **Chords** (193 `Chord{time,label}`) — the harmony moves, the color doesn't.
- **Per-stem onsets** (guitar 853, drums 716 — the *real* groove, denser/more syncopated than the 617 metronomic beats), with an energy-ranked prominent stem already computed.
- **Section intensity** (0–1) — every section currently gets the same accent density.

This change makes the accents follow the music: density that breathes with the energy, a feature prop that catches the actual notes, and color that moves with the harmony.

## What Changes

- **Energy-scaled density**: scale how many beats get an accent by `section.intensity` — a quiet section places sparser accents (downbeats + fewer off-beats), a loud section places every beat. Downbeats always kept.
- **Onset hits on a hero prop**: *in addition* to the `04_BEAT` chase, place hits on one hero/feature group (prefer `08_HERO_*`) at the prominent stem's onset times — so a feature prop pulses on the real kicks/notes while `04_BEAT` keeps the steady pulse.
- **Chord-driven accent color**: the accent color steps through the section's palette as chords change, so color *moves with the harmony* (and adds the variety the wash alone can't).

**Non-goals:** changing the wash effect/look or wash-color-over-time (accents only); melody/pitch following; new effect types; re-deriving chords; bar detection (keep derived 4/4).

## Capabilities

### Modified Capabilities
- `show-orchestration`: accent density scales with section intensity; beat accents are augmented by feature-prop hits following the section's prominent instrument; accent color follows chord changes — so the rhythm layer tracks the actual music, not a metronome.

## Impact

- **`xlights-orchestrator`**: `beats.py` (`place_beat_accents` density scaling + hero onset layer + chord-indexed color); `section_rhythm` surfaces the section's chords. Additive over the wash, bounded by the existing per-section cap.
- **Builds on** `improve-beat-visibility` (chase + `split_palette` accent), the 6-stem onsets, Chordino chords, and normalized intensities. Reuses `_accent_look`/`_downsample`.
