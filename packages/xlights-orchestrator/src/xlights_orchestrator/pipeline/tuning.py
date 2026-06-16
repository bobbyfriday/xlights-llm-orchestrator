"""Show-feel tuning dials — the deterministic layers' "voice" in one place.

These are the artistic knobs (brightness ranges, energy thresholds, accent density, the
weave's cell budget) that shape how a show reads, gathered here so the feel can be tuned
without hunting through the algorithm modules. Structural/mechanical constants (effect
parameter maps, layer caps, bar math) deliberately stay beside the code that uses them.

Scale note: brightness values are on xLights' 0–400 scale (100 = normal); intensity inputs
are normalized 0..1 (a section's energy).
"""

from __future__ import annotations

# -- brightness (0–400 scale) -----------------------------------------------
WASH_MIN_B, WASH_MAX_B = 50.0, 180.0   # section wash: dim in quiet sections, boost in loud ones
BED_BRIGHTNESS_FACTOR = 0.6            # the ensemble bed sits UNDER the features
FEATURE_PROP_BRIGHTNESS = 150.0        # featured sparkle/snow props pop above the bed
FLASH_BRIGHTNESS = 300.0               # the white climax flash — a bright pop
WEAVE_BED_BRIGHTNESS = "60"            # the woven section-spanning bed (static C_SLIDER_Brightness)

# -- energy thresholds (0..1 intensity) -------------------------------------
ESCALATION_BOOST = 0.25                # how much a final recurrence can lift effective intensity
RHYTHM_FLOOR = 0.35                    # at/above this a section is rhythmic by nature
BED_INTENSITY = 0.7                    # at/above this a section carries a whole-yard bed
PEAK_BAND = 0.12                       # sections within this of max intensity = the peak
PEAK_FLOOR = 0.66                      # ...and at least this loud (a quiet show has no peak)
PEAK_BED_SPAN = 0.7                    # a wash covering this fraction already IS the lit yard

# -- density & restraint ----------------------------------------------------
MAX_ACCENTS_PER_SECTION = 80           # hard upper bound on beat accents per section
HERO_MAX_ONSETS = 40                   # hero hits scale with intensity, up to this (tasteful)
MIN_LIT_GROUPS = 2                     # the coverage rule never fully blacks out a section
PALETTE_DEPTH = 5                      # expanded section-palette size
# Weave cell budget: cells/min = BUDGET_BASE + intensity * BUDGET_SCALE. Peak ≈ 600/min — the
# community's ~1,300/min was per-prop rows; ours weaves group rows (~15 targets), so scaled.
BUDGET_BASE = 120.0
BUDGET_SCALE = 480.0

# -- durations (ms) ---------------------------------------------------------
ACCENT_MS = 250                        # a short beat-accent punctuation
FLASH_MS = 150                         # a brief full-display white hit
HIT_CELL_MS = 1200                     # a hit-class effect cell is at most this long
