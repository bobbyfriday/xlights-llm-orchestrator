## Why

The deterministic beat layer (`pipeline/beats.py`) reads the music narrowly and ignores most of what
the layout knows. It listens to a single "prominent stem", hits *all* rhythm props together on the
downbeat then rotates *one* group on off-beats, fires sparkle on every bar, and selects rhythm groups
from a flat hardcoded tuple (`RHYTHM_POOL = arches+canes+minitrees`) — discarding each prop's
capability (linear/point/matrix), band (roof/mid/ground), and side that `build_sem_groups` already
computes. The result reads as a generic chase, not the song's groove, and on calm sections its 250ms
"On" pops flash (the residual the mood-fades work could not reach, since fades only touched woven
cells). There is also no notion of the bar's *meter* as a spatial structure, and no backbeat.

## What Changes

Restructure the deterministic rhythm into two deliberate, separable layers plus phrasing modulation:

- **Meter backbone — prop-family-per-beat.** Map each beat of the bar to a distinct rhythm group in a
  fixed order (4/4: arches→1, canes→2, mini-trees→3, a 4th→4), pulsing that group on its beat so the
  bar *walks across the prop families* and the meter is visible. Discrete pulses on whole SEM_ groups
  (per-model-safe; no within-group buffer chase — the `_LTR` groups don't render a chase and per-model
  can't travel). Honors the real `beats_per_bar` (non-4/4). Replaces the "downbeat hits all + offbeat
  rotates one" scheme.
- **Groove overlay — instrument-mapped, on top of the backbone.**
  - **Backbeat** (beats 2 & 4): a distinct accent on a contrasting group — the snare feel.
  - **Sparkle**: snowflake/spinner props ride the **top-magnitude drum onsets** (onset strength from
    the stem's energy at the onset, reusing the trigger layer's `energy_at`), not every bar.
  - **Hero**: `SEM_FOCAL` rides the prominent **melodic** stem (guitar/piano/vocals — not drums/bass),
    on its real onsets, so the focal prop follows the tune.
  - **Bass foundation**: a low pulse on `SEM_BAND_GROUND` on bass onsets (low sound → low props).
- **Phrasing-aware accents.** The resolved section phrasing (`resolve_phrasing`, from mood-fades)
  modulates every accent gesture: **legato** lengthens + soft-fades (`soft_edge_settings`) + sparsens
  toward downbeats; **staccato** stays crisp. This softens the calm-section flashing the cell fades
  could not reach.
- **Instrument → layer routing** is explicit and tunable (a small routing helper + dials in
  `tuning.py`), so e.g. piano (a melodic lead that may be arpeggiated/sustained) routes to the hero
  overlay on its real onsets — never forced onto the per-beat metric walk — and stays a dial we adjust
  after seeing it on a real render.

## Capabilities

### New Capabilities
<!-- none — restructures existing deterministic rhythm behavior -->

### Modified Capabilities
- `show-orchestration`: the beat-accent requirements are restructured — accents become a meter
  backbone (prop-family-per-beat) plus an instrument-mapped groove overlay (backbeat, top-hit sparkle,
  melodic hero, bass foundation), phrasing-modulated, with rhythm-group selection derived from the
  layout's role/capability/band rather than a flat tuple.

## Impact

- `packages/xlights-orchestrator/.../pipeline/beats.py` — `place_beat_accents` restructured into the
  meter backbone + groove-overlay sublayers; new group-selection and instrument-routing helpers.
- `packages/xlights-orchestrator/.../pipeline/semantic_groups.py` — role/capability-aware group
  selection (the metric ring, the band/accent roles).
- `packages/xlights-orchestrator/.../pipeline/tuning.py` — routing + density/sparkle dials.
- Reuses `resolve_phrasing` / `soft_edge_settings` (weave) and `energy_at` (triggers).
- Hermetic tests for: the per-beat ring mapping (incl. non-4/4), backbeat positions, top-magnitude
  sparkle selection, melodic-vs-percussive stem routing, phrasing modulation, carrier-covers dedup,
  and the still-section guard. Golden snapshot regenerated. Live-verify on `dj play a christmas
  song.mp3` (drum-heavy — exercises the groove overlay) and `christmas canon.mp3` (piano — exercises
  melodic hero routing). Lands via PR.
