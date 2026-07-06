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

# -- metric rhythm + instrument overlay -------------------------------------
# The METRIC RING: each beat of the bar lights the next group, so the bar walks across prop
# FAMILIES (beat 1 → arches, 2 → canes, 3 → mini-trees, 4 → sparkle). Filtered to available;
# the brief's pulse_groups override it. Distinct prop-type per beat = the meter you can see.
METRIC_RING = (SEM_ARCHES, SEM_CANES, SEM_MINITREES, SEM_SNOWFLAKES)
# The backbeat (2 & 4) answers the downbeat on a CONTRASTING group. Prefer the spatial SIDE
# groups (they sweep across, distinct from the prop-family ring), then the point accents. When
# every preferred group is already taken by the ring/sparkle, the selector falls back to a ring
# family other than the downbeat anchor (see select_rhythm_groups) so the backbeat still reads.
BACKBEAT_GROUP_PREFERENCE = (SEM_SIDE_CENTER, SEM_SIDE_LEFT, SEM_SIDE_RIGHT,
                             SEM_SPINNERS, SEM_SNOWFLAKES)
# The bass foundation rides the low band (low sound → low props).
BASS_BAND_GROUP = SEM_BAND_GROUND
# Stems that are MELODIC leads (route to the hero focal prop, never the metric walk).
MELODIC_STEMS = ("guitar", "piano", "vocals")


# -- F-E derived choreography vocabulary -------------------------------------
# The rhythm sublayers used to import the constants above directly — this layout's opinion baked
# in by tuple ORDER. `derive_vocabulary(manifest)` ranks the rhythm families a DIFFERENT layout
# actually has (by count, spatial spread, node budget), so the beat anchor is chosen by ranking,
# not by accident. Absent a manifest, `DEFAULT_VOCAB` == today's constants → byte-identical output.
from dataclasses import dataclass  # noqa: E402 — kept beside the vocabulary it defines


@dataclass(frozen=True)
class ChoreoVocabulary:
    """The per-run choreography vocabulary the deterministic rhythm layers draw from."""
    metric_ring: tuple[str, ...] = METRIC_RING
    backbeat_preference: tuple[str, ...] = BACKBEAT_GROUP_PREFERENCE
    bed_preference: tuple[str, ...] = BED_PREFERENCE
    peak_broad: tuple[str, ...] = PEAK_BROAD_GROUPS
    accent_groups: tuple[str, ...] = ACCENT_GROUPS
    hero_group: str = HERO_GROUP
    bass_band_group: str = BASS_BAND_GROUP


# The no-manifest fallback AND the tie-break prior. Equals today's constants EXACTLY (the golden
# pipeline snapshot asserts byte-stability), so a run with no manifest is unchanged.
DEFAULT_VOCAB = ChoreoVocabulary()

# The role → SEM_ role-group name map (mirrors knowledge/layout_semantics._ROLE_GROUP), so the
# derivation can name the groups a manifest's roles imply without importing xlights-core here.
_ROLE_TO_GROUP = {"ARCH": SEM_ARCHES, "CANE": SEM_CANES, "MINI_TREE": SEM_MINITREES,
                  "SNOWFLAKE": SEM_SNOWFLAKES, "SPINNER": SEM_SPINNERS}
_GROUP_TO_ROLE = {v: k for k, v in _ROLE_TO_GROUP.items()}
# The rhythm-cell families the metric ring may walk across (true accent/chase props, NOT frames
# like OUTLINE/WINDOW which read as a bed, not a beat).
_RHYTHM_FAMILY_ROLES = ("ARCH", "CANE", "MINI_TREE", "SNOWFLAKE", "SPINNER")


def derive_vocabulary(manifest) -> ChoreoVocabulary:
    """Rank the layout's rhythm families into a choreography vocabulary (design decision 11).

    `None` → `DEFAULT_VOCAB`. RING: keep today's `METRIC_RING` order as the tie-break PRIOR for the
    families it names that the layout actually has, then fill to 4 with the highest-scoring OTHER
    rhythm families (count, x-spread, node budget) — so a layout WITH today's families reproduces
    today's constant exactly (the byte-stability safety gate), and an arch-less layout ranks its
    canes/minis in by score. BACKBEAT: SEM_SIDE_* when ≥2 sides populated, else the accent families
    not consumed by the ring. BED: SEM_BAND_GROUND if the ground band holds ≥25% of props, else
    SEM_ALL; PEAK_BROAD is the reverse. HERO: SEM_FOCAL if any focal prop.
    """
    if manifest is None:
        return DEFAULT_VOCAB
    props = list(getattr(manifest, "props", None) or [])
    if not props:
        return DEFAULT_VOCAB

    # per-role stats
    from collections import defaultdict
    by_role: dict[str, list] = defaultdict(list)
    for p in props:
        by_role[p.role].append(p)

    def _score(role: str) -> float:
        members = by_role.get(role, [])
        n = len(members)
        if n < 2:                                          # a walkable family needs ≥2 members
            return 0.0
        xs = [getattr(p.pos, "x", 0.5) for p in members]
        spread = (max(xs) - min(xs)) if xs else 0.0
        node_budget = sum(getattr(p, "nodes", 0) for p in members) / n
        return n + 2.0 * spread + min(node_budget / 100.0, 3.0)   # count, spread, readable budget

    present = {r for r in _RHYTHM_FAMILY_ROLES if _score(r) > 0}
    # (1) today's ring families, in today's order, that this layout has → the byte-stable prior.
    ring_roles = [_GROUP_TO_ROLE[g] for g in METRIC_RING
                  if g in _GROUP_TO_ROLE and _GROUP_TO_ROLE[g] in present]
    # (2) fill the remaining slots with the highest-scoring families not already in the ring.
    extra = sorted((r for r in present if r not in ring_roles), key=lambda r: -_score(r))
    ring_roles = (ring_roles + extra)[:4]
    ring = tuple(_ROLE_TO_GROUP[r] for r in ring_roles) or METRIC_RING
    ranked = sorted(present, key=lambda r: -_score(r))    # for the backbeat pool below

    # sides populated?
    sides = {getattr(p.pos, "side", "CENTER") for p in props}
    n_sides = len({s for s in sides if s in ("LEFT", "CENTER", "RIGHT")})
    if n_sides >= 2:
        backbeat = (SEM_SIDE_CENTER, SEM_SIDE_LEFT, SEM_SIDE_RIGHT) + ACCENT_GROUPS
    else:
        pool = tuple(_ROLE_TO_GROUP[r] for r in ranked if _ROLE_TO_GROUP[r] not in ring)
        backbeat = pool + ACCENT_GROUPS or BACKBEAT_GROUP_PREFERENCE

    ground = sum(1 for p in props if getattr(p.pos, "band", "MID") == "GROUND")
    if ground >= 0.25 * len(props):
        bed_pref = (SEM_BAND_GROUND, SEM_ALL)
        peak_broad = (SEM_ALL, SEM_BAND_GROUND)
    else:
        bed_pref = (SEM_ALL, SEM_BAND_GROUND)
        peak_broad = (SEM_BAND_GROUND, SEM_ALL)

    hero = SEM_FOCAL if any(getattr(p, "focal", False) for p in props) else HERO_GROUP

    # accent groups present as roles (fall back to the constant pair)
    accent = tuple(g for r, g in (("SNOWFLAKE", SEM_SNOWFLAKES), ("SPINNER", SEM_SPINNERS))
                   if by_role.get(r)) or ACCENT_GROUPS

    return ChoreoVocabulary(metric_ring=ring, backbeat_preference=backbeat, bed_preference=bed_pref,
                            peak_broad=peak_broad, accent_groups=accent, hero_group=hero,
                            bass_band_group=BASS_BAND_GROUP)
