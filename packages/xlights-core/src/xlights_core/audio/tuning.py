"""Show-feel tuning dials for audio-structure segmentation — the core-side counterpart to
``xlights_orchestrator.pipeline.tuning`` (which can't reach down here, since core is the lower
package). These are the artistic knobs for how a song is cut into sections: the lyric refiner's
minimum/span shaping, the instrumental long-section cap, and the seam-scoring thresholds. Gathered
here so the feel can be tuned in one place without hunting through ``structure.py``.

Pure data: no imports, no logic. Mechanical constants (beat math, label formatting) stay beside
the code that uses them.
"""

from __future__ import annotations

# -- lyric refiner / span shaping --------------------------------------------------------------
MIN_SECTION_S = 6.0       # a section shorter than ~3 bars merges into its predecessor
                          # (a REAL 4-bar chorus at 133bpm is only ~7.2s — don't swallow it)
OUTRO_TAIL_S = 8.0        # split an outro when this much song remains after the last sung line
INFILL_SPAN_S = 25.0      # spans longer than this keep interior audio boundaries (instrumentals)
INFILL_EDGE_S = 10.0      # ...but only boundaries at least this far from the span's edges
LINE_NEAR_S = 2.0         # an audio boundary within this of a sung line is NOT instrumental

# -- long-section cap: a soft target, flexed onto the music's real breaks -----------------------
INSTR_TARGET_SECTION_S = 25.0  # aim a long-section cut near here — a look much past this gets boring
INSTR_SECTION_FLEX_S = 10.0    # ...but flex ±this onto a real musical break (so a cut lands in 15–35s)
INSTR_MIN_PIECE_S = 12.0       # don't shred a musical part into confetti

# -- seam scoring ------------------------------------------------------------------------------
SEAM_ENERGY_NEAR_S = 0.75      # a harmonic seam scores by the energy shift within this of it
                               # (energy_arc is ~duration/400-spaced; 0.75 covers the adjacent step
                               #  for songs up to ~10 min)
SEAM_MIN_STRENGTH_FRAC = 0.12  # a cut counts as a "real" break only if the energy shifts at least
                               # this fraction of the song's full RMS span (else it's just noise)
