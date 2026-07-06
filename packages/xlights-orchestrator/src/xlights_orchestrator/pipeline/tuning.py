"""Show-feel tuning dials — the deterministic layers' "voice" in one place.

These are the artistic knobs (brightness ranges, energy thresholds, accent density, the
weave's cell budget) that shape how a show reads, gathered here so the feel can be tuned
without hunting through the algorithm modules. Structural/mechanical constants (effect
parameter maps, layer caps) deliberately stay beside the code that uses them.

Scope also covers the refine-loop control thresholds (regression margin, stall limit,
skip-objective cutoff) and the bar-math / motion-share behavior dials — tunable behavior, kept
here beside the show-feel knobs with their provenance rather than scattered across run.py/qa.rules.

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

# -- phrasing / soft-edge transitions (legato vs staccato) ------------------
# A section's cells are either legato (soft, evolving — fades/dissolves at the edges, for calm
# introspective sections) or staccato (crisp on/off, for energetic sections). The Director may
# direct it per section; left blank, it defaults from intensity at this threshold.
PHRASING_INTENSITY_THRESHOLD = 0.5     # below this a section defaults to legato, at/above to staccato
LEGATO_FADE_FRACTION = 0.35            # legato fade time as a fraction of the cell's own length...
LEGATO_MAX_FADE_S = 1.5                # ...capped here (a long cell must not fade for many seconds)
LEGATO_BED_FADE_S = 1.0                # the section-spanning bed's gentle entrance/exit (capped)
LEGATO_CELL_BEATS_FLOOR = 2            # legato lengthens short cells so the soft edge has room to read

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
# Weave cell budget: cells/min = BUDGET_BASE + intensity * BUDGET_SCALE. Peak ≈ 600 GROUP-rows/min.
# The community's ~1,300/min was per-prop rows; ours weaves group rows, so the budget is on the
# group scale and normalized by mean group membership (~23.8 props/group) for the comparison.
# Fabric re-measurement (docs/effects-layering-analysis-2026-07.md): held at 480. Real generated
# shows already measure 68–97% motion at 187–2,528/min prop-rows — within the "≤ 2× community
# typical" peak-density band — so a BUDGET_SCALE raise is NOT warranted (denser reads as noise, the
# item's headline risk). The budget raise is the last lever; the measurement withheld permission.
BUDGET_BASE = 120.0
BUDGET_SCALE = 480.0

# -- metric rhythm + instrument overlay -------------------------------------
# Fabric re-measurement (docs/effects-layering-analysis-2026-07.md): the golden fixture's 40 `On`
# rows are 36 beat-accents (source attribution) — the accent layer IS the punctuation source. 12 → 8
# so sparkle rides fewer drum hits, rebalancing On+Twinkle down in energetic sections (shares before
# totals; carrier_covers already suppresses the every-beat chase when a carrier owns the pool).
SPARKLE_TOP_N = 8              # sparkle rides only the N strongest drum hits per section (not every bar)
BASS_MAX_ONSETS = 16           # bass-foundation pulses per section (low + sparse)
BACKBEAT_MIN_DRUM_ONSETS = 4   # need at least this many drum onsets in a section to add a backbeat
LEGATO_ACCENT_SPARSEN = 2      # a legato section keeps every Nth backbone accent (sparser, softer)
LEGATO_ACCENT_MS = 600         # legato accents breathe longer than the crisp ACCENT_MS pop

# -- durations (ms) ---------------------------------------------------------
ACCENT_MS = 250                        # a short beat-accent punctuation
FLASH_MS = 150                         # a brief full-display white hit
HIT_CELL_MS = 1200                     # a hit-class effect cell is at most this long

# -- duration-class bar math + motion-share (behavior dials) ----------------
PHRASE_BARS = 8                # a PHRASE-class effect is clamped to ~this many bars (reveal/build)
CELL_BARS = 2                 # a CELL-ABLE motion effect left long is chopped into this-bar cells
# Fabric re-measurement (docs/effects-layering-analysis-2026-07.md) energetic-section target: motion
# ≥ 0.45. Raised 0.30 → 0.40 (just under target) NOW that real shows clear it (68–97% motion), so
# the Judge defends the new fabric without being spammed on legitimately mixed sections. Energetic
# sections only (MOTION_SHARE_INTENSITY gate); quiet/rest/gesture exempt.
MOTION_SHARE_MIN = 0.40        # energetic sections below this motion-effect share advise a fabric regression (I7 lever)

# -- refine loop control ----------------------------------------------------
REGRESS_MARGIN = 1   # objective_score points; a drop beyond this reverts the revision
STALL_LIMIT = 2      # consecutive no-objective-progress iterations → terminate
# Revision-log analysis (42 runs): drafts whose first-pass objective is ≥ this gained ≈0 over the
# whole loop while paying for every Judge + visual-critique + regen iteration. Skip the loop for them.
REFINE_SKIP_OBJECTIVE = 88   # tune/disable via XLO_REFINE_SKIP_OBJECTIVE (101 = never skip)
