"""The SEM_ semantic group vocabulary (see xlights-layout-semantics-spec).

One source of truth for the role/spatial group names the deterministic layers target,
so a rename or a new role is a single edit and a typo surfaces as an import error rather
than a silently-dark prop. Names mirror the SEM_ groups built into the layout's rgbeffects.xml.
"""

from __future__ import annotations

# -- individual group names -------------------------------------------------
SEM_ALL = "SEM_ALL"                  # the whole display
SEM_FOCAL = "SEM_FOCAL"              # the hero / focal prop(s)
SEM_HOUSE = "SEM_HOUSE"              # the house outline
SEM_BAND_GROUND = "SEM_BAND_GROUND"  # the ground-level band (a bed under the features)
SEM_SIDE_LEFT = "SEM_SIDE_LEFT"
SEM_SIDE_CENTER = "SEM_SIDE_CENTER"
SEM_SIDE_RIGHT = "SEM_SIDE_RIGHT"
SEM_ARCHES = "SEM_ARCHES"
SEM_CANES = "SEM_CANES"
SEM_MINITREES = "SEM_MINITREES"
SEM_SNOWFLAKES = "SEM_SNOWFLAKES"
SEM_SPINNERS = "SEM_SPINNERS"

# -- role groupings the layers target ---------------------------------------
RHYTHM_GROUPS = (SEM_SIDE_LEFT, SEM_SIDE_CENTER, SEM_SIDE_RIGHT)  # beat chase sweeps L→C→R
RHYTHM_POOL = (SEM_ARCHES, SEM_CANES, SEM_MINITREES)             # call-and-response rhythm cells
ACCENT_GROUPS = (SEM_SNOWFLAKES, SEM_SPINNERS)                   # sparkle props: fire on hits, dark otherwise
HERO_GROUP = SEM_FOCAL                                           # the hero onset layer rides this
FULL_DISPLAY = SEM_ALL                                          # flashes hit the whole display
WHOLE_HOUSE_GROUPS = (SEM_ALL, SEM_HOUSE)                        # trigger targets for house-wide hits

# The ensemble bed, preferred order: GROUND sits UNDER the features.
BED_PREFERENCE = (SEM_BAND_GROUND, SEM_ALL)
# The peak fill prefers the BROADEST ensemble first (deliberately the opposite order).
PEAK_BROAD_GROUPS = (SEM_ALL, SEM_BAND_GROUND)
