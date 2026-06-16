## Why

`cap_long_segments` cuts long sections at musical seams — but the seam RANKING was weak, so cuts drifted to the ~32s cap instead of the real break. Concretely (Canon's intro): the [12s,32s] window had ~54 harmonic-change candidates (one every ~0.5s), all weighted equally (1.0), and ties broke to the LATEST time — so it cut at 31.9s (mid-phrase, energy |Δ|≈0.01), ignoring the obvious structural break at ~29s where the music drops to near-silence (28.4s) then surges back (29.1s, energy |Δ|=0.20). Effectively it "maxed out at 32" rather than finding the seam.

## What Changes

- **Score seams by energy-change strength (code):** a candidate cut's strength = how much the energy changes there (`|Δrms|` near it). Harmonic-change times are still candidates but scored by the coincident energy shift (a seam that's both a chord change and an energy jump wins); energy-delta points are candidates in their own right. The cut picks the **strongest** seam in the window, breaking ties toward the **earliest** (not latest) so it stops drifting to the cap. When a window has no energy/harmonic data at all, it falls back to even spacing near the cap as before.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: long-section cuts SHALL land on the strongest structural seam in the window (ranked by energy change), not the latest seam before the length cap.

## Impact

- `audio/structure.py` (`cap_long_segments` candidate scoring + selection). Back-compat: instrumental/lyric refiners unchanged; songs whose sections already fit are untouched. Verified on Canon: the first intro cut moves 31.9s → 29.1s (the energy re-entry), and later cuts move to energy seams (60.7s, 78.1s) instead of cap-maxing.
