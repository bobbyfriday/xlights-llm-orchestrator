## Why

`cap_long_segments` treated the long-section cap (32s) as a HARD limit: a cut could only flex
*shorter* than the cap, never past it. So a genuine structural break a few seconds beyond the cap
was unreachable, and a flat window with no break drifted to the 32s edge. The single "32" also
conflated two ideas — "a look this long starts to drag" (a soft target) and "never exceed this"
(a ceiling) — into one number.

## What Changes

- **Soft target + flex (code):** a long-section cut now AIMS for `INSTR_TARGET_SECTION_S` (25s) and
  flexes ±`INSTR_SECTION_FLEX_S` (10s) — a 15–35s window — to land on the strongest REAL energy
  break, where "real" means the energy shifts at least `SEAM_MIN_STRENGTH_FRAC` (12%) of the song's
  RMS span. Among real breaks it picks the one NEAREST the target (ties → stronger); a window with
  only weak/harmonic seams uses the nearest-to-target seam; a window with no seam falls back to a
  beat near the target (not the ceiling edge). The ceiling is `target + flex` (35s), so a clean
  30–35s stretch is left whole instead of being force-cut.
- **Tuning surface (code):** the audio-structure show-feel knobs move out of `structure.py` into a
  new `xlights_core/audio/tuning.py` — the core-side counterpart to
  `xlights_orchestrator/pipeline/tuning.py` (R4), which can't reach into the lower `xlights-core`
  package.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: long-section cuts SHALL aim for a soft target and flex onto the strongest
  REAL energy break in the window (reachable past the target), instead of taking the strongest seam
  before a hard cap.

## Impact

- `audio/structure.py` (`cap_long_segments` windowing + selection; constants now imported from
  tuning) and new `audio/tuning.py`. Back-compat: the instrumental/lyric refiners and the
  "already fits" no-op are unchanged; the `structure.*` constant names are preserved (re-exported
  via the import), so nothing downstream breaks. Tests: 3 that hard-coded `32` were updated.
  Real-audio verification (Canon: cuts move onto the energy re-entries rather than cap-maxing) is
  pending an environment with the `[audio]` extra installed.
