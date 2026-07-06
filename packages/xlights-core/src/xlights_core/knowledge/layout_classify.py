"""Layout classifier + spatial derivation — spec §3/§4 as real code (F-E generalization).

Turns an arbitrary xLights ``rgbeffects.xml`` into classified, spatially-derived ``Prop``s:
the judgment half that used to be prose / a one-time manual step. Dependency-free (stdlib XML
only) so it lives beside the group plan in ``xlights-core/knowledge`` and runs with no LLM key.

- ``parse_props``   — one Prop per <model> in the default preview (spec §8): DisplayAs, node count
  (mirrors ``preview/layout.py``), world pos, user-group membership, StringType, submodel names.
- ``classify``      — spec §3 steps 1–4 in a fixed order, each touching only unresolved props:
  DisplayAs map → tree pixel-count → name heuristics → group-name hints. Confidence per step.
- ``capability``    — spec §2: role + geometry → a capability class (replacing "names encode
  capability"); non-RGB string → POINT override; a very large dense Custom → 2D_SURFACE matrix.
- ``derive_spatial``— spec §4: outlier exclusion FIRST, then normalize, bands/sides, sweep order,
  mirror pairs, center distance, focal flags.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from .layout_semantics import Prop

# -- spec §3 step 1: DisplayAs direct map (confidence 1.0) ---------------------------------------
DISPLAYAS_ROLE: dict[str, str] = {
    "Arches": "ARCH",
    "Icicles": "ICICLES",
    "Candy Canes": "CANE",
    "Star": "STAR",
    "Spinner": "SPINNER",
    "Matrix": "MATRIX",
    "Horiz Matrix": "MATRIX",
    "Vert Matrix": "MATRIX",
    "Window Frame": "WINDOW",
}

# -- spec §3 step 2: tree pixel-count disambiguation --------------------------------------------
MEGA_TREE_NODES = 600
_TREE_DISPLAYAS = ("Tree 360", "Tree Flat", "Tree 180")

# -- spec §3 step 3: name heuristics (case-insensitive substring, spec table verbatim) ----------
#   ordered longest/most-specific-first isn't needed — a prop resolves to the FIRST matching row.
NAME_HEURISTICS: tuple[tuple[tuple[str, ...], str], ...] = (
    # OUTLINE is checked first so "garage" beats "door" on a garage-door outline.
    (("roof", "gutter", "eave", "ridge", "outline", "peak", "fascia", "column", "garage"), "OUTLINE"),
    (("cane",), "CANE"),                                          # "Candy Cane - Left - 1" (Custom)
    (("spinner",), "SPINNER"),                                    # "Spinner 23 inch" (Custom)
    (("window", "door"), "WINDOW"),
    (("flood", "wash", "up light", "uplight"), "FLOOD"),
    (("face", "sing", "carol", "mouth"), "SINGING_FACE"),
    (("sign", "tune"), "SIGN"),
    (("drive", "walk", "path", "fence", "yard line"), "PATH"),
    (("flake",), "SNOWFLAKE"),
)

# The 16 canonical roles (spec §2) — the LLM fallback enum and validation draw from this list.
CANONICAL_ROLES = (
    "MEGA_TREE", "MINI_TREE", "ARCH", "CANE", "ICICLES", "STAR", "SPINNER", "MATRIX",
    "WINDOW", "OUTLINE", "FLOOD", "SINGING_FACE", "SIGN", "PATH", "SNOWFLAKE", "CUSTOM_PROP",
)


@dataclass
class ClassifyResult:
    """Classified props + the unresolved tail (CUSTOM_PROP @ 0.5 that need review / the LLM)."""
    props: list[Prop]                                  # every prop, with role + confidence set
    unresolved: list[Prop] = field(default_factory=list)   # the CUSTOM_PROP @ ≤0.5 tail


# ------------------------------------------------------------------------------------------------
# parse_props — dependency-free, captures what classification needs (spec §3/§4/§6, decision 1)
# ------------------------------------------------------------------------------------------------
def _node_count(display_as: str, m: ET.Element) -> int:
    """Pixel count, mirroring preview/layout.py:141-149 (Custom → grid max; Cube → p1·p2·p3;
    else p1·p2)."""
    def _pint(k: str, d: int = 1) -> int:
        try:
            return int(m.get(k, d))
        except (TypeError, ValueError):
            return d
    if display_as == "Custom":
        grid = m.get("CustomModel", "") or ""
        best = 0
        for cell in grid.replace(";", ",").split(","):
            cell = cell.strip()
            if cell:
                try:
                    best = max(best, int(cell))
                except ValueError:
                    pass
        return best
    if display_as == "Cube":
        return _pint("parm1") * _pint("parm2") * _pint("parm3")
    return _pint("parm1") * _pint("parm2")


def parse_props(rgb_path: str | Path, *, layout_group: str = "Default") -> list[Prop]:
    """One Prop per <model> in the given preview (spec §8: default preview only).

    Roles/spatial fields are left at their defaults — ``classify`` and ``derive_spatial`` fill
    them. Reverse-indexes user group membership from <modelGroups> (spec §4 group hints)."""
    root = ET.parse(rgb_path).getroot()

    # reverse index: model name -> [user group names it belongs to]
    membership: dict[str, list[str]] = {}
    mg = root.find("modelGroups")
    for g in (mg.findall("modelGroup") if mg is not None else []):
        gname = g.get("name", "")
        if gname.startswith("SEM_"):            # SEM_ groups are OUR output, never a hint source
            continue
        for member in (g.get("models", "") or "").split(","):
            member = member.strip()
            if member:
                membership.setdefault(member, []).append(gname)

    props: list[Prop] = []
    models_el = root.find("models")
    for m in (models_el.findall("model") if models_el is not None else []):
        # default preview only — a model parked in another layoutGroup is excluded (spec §8).
        if m.get("LayoutGroup") not in (None, "Default", "", layout_group):
            continue
        name = m.get("name", "")
        display_as = m.get("DisplayAs", "")
        submodels = [sm.get("name", "") for sm in m.findall("subModel") if sm.get("name")]

        def _f(k: str) -> float:
            try:
                return float(m.get(k, 0) or 0)
            except (TypeError, ValueError):
                return 0.0

        props.append(Prop(
            name=name, display_as=display_as, nodes=_node_count(display_as, m),
            wx=_f("WorldPosX"), wy=_f("WorldPosY"),
            groups=membership.get(name, []),
            string_type=m.get("StringType", ""),
            submodels=submodels,
        ))
    return props


# ------------------------------------------------------------------------------------------------
# classify — spec §3 steps 1–4, each touching only unresolved props (decision 2)
# ------------------------------------------------------------------------------------------------
def _name_role(text: str) -> str | None:
    low = (text or "").lower()
    for subs, role in NAME_HEURISTICS:
        if any(s in low for s in subs):
            return role
    return None


def _tree_role(p: Prop, props: list[Prop]) -> str:
    """MEGA_TREE if ≥600 nodes, or a SOLE tree that is the layout's largest prop; else MINI_TREE."""
    if p.nodes >= MEGA_TREE_NODES:
        return "MEGA_TREE"
    trees = [q for q in props if q.display_as in _TREE_DISPLAYAS]
    if len(trees) == 1 and p.nodes >= max((q.nodes for q in props), default=0):
        return "MEGA_TREE"
    return "MINI_TREE"


def classify(props: list[Prop]) -> ClassifyResult:
    """Run spec §3 steps 1–4 in order; each step touches only still-unresolved props.
    Sets ``role`` + ``confidence`` (1.0 map/tree, 0.9 name, 0.85 group hint, 0.5 unresolved)."""
    resolved: set[int] = set()

    def _set(i: int, role: str, conf: float) -> None:
        props[i].role = role
        props[i].confidence = conf
        resolved.add(i)

    # step 1 — DisplayAs direct map
    for i, p in enumerate(props):
        role = DISPLAYAS_ROLE.get(p.display_as)
        if role:
            _set(i, role, 1.0)

    # step 2 — tree pixel-count disambiguation
    for i, p in enumerate(props):
        if i in resolved:
            continue
        if p.display_as in _TREE_DISPLAYAS or p.display_as.startswith("Tree"):
            _set(i, _tree_role(p, props), 1.0)

    # step 3 — name heuristics
    for i, p in enumerate(props):
        if i in resolved:
            continue
        role = _name_role(p.name)
        if role:
            _set(i, role, 0.9)

    # step 4 — group-name hints (inherit the role the user group's name matches)
    for i, p in enumerate(props):
        if i in resolved:
            continue
        for gname in p.groups:
            role = _name_role(gname)
            if role:
                _set(i, role, 0.85)
                break

    # unresolved tail → CUSTOM_PROP @ 0.5 (review / LLM), never silently into a group.
    unresolved: list[Prop] = []
    for i, p in enumerate(props):
        if i not in resolved:
            p.role = "CUSTOM_PROP"
            p.confidence = 0.5
            unresolved.append(p)

    # capability class from role + geometry (spec §2), stored on Prop.res for the plan/manifest.
    for p in props:
        p.res = capability(p.role, p.nodes, p.string_type)

    return ClassifyResult(props=props, unresolved=unresolved)


def apply_overrides(result: ClassifyResult, overrides: dict[str, dict]) -> ClassifyResult:
    """Force a prop's role from a per-layout ``layout_overrides.json`` (migration plan / spec §6.4).

    Applied AFTER steps 1–4 and BEFORE the LLM step: a divergence from the convergence golden is
    fixed by the classifier or an explicit override, never by weakening the diff. An overridden
    prop is confidence 1.0 (a human decision) and leaves the review/unresolved queue."""
    if not overrides:
        return result
    for p in result.props:
        ov = overrides.get(p.name)
        if ov and ov.get("role") in CANONICAL_ROLES:
            p.role = ov["role"]
            p.confidence = 1.0
            p.res = capability(p.role, p.nodes, p.string_type)
    result.unresolved = [p for p in result.unresolved if p.name not in overrides]
    return result


# ------------------------------------------------------------------------------------------------
# capability — spec §2: role + geometry → capability class (decision 3)
# ------------------------------------------------------------------------------------------------
LINEAR_HIGH_NODES = 100         # OUTLINE/PATH split: dense enough for a readable chase
DENSE_CUSTOM_NODES = 400        # a whole-house Custom mesh this big reads as a matrix surface
_RGB_STRING_TYPES = ("rgb",)    # anything else (e.g. "Single Color Red", "GRB"…) is RGB-capable too


def _is_non_rgb(string_type: str) -> bool:
    """Non-RGB = a single-color/monochrome string (spec §8: overrides to POINT)."""
    st = (string_type or "").strip().lower()
    if not st:
        return False
    # xLights RGB string types contain a channel-order token (RGB/GRB/BRG/RGBW…); a mono string
    # is named "Single Color <hue>" or "Node Single Color…". Treat any "single color" as non-RGB.
    if "single color" in st or "singlecolor" in st:
        return True
    return False


def capability(role: str, nodes: int, string_type: str = "") -> str:
    """The prop's capability class (spec §2) from role + geometry, NOT its name."""
    if _is_non_rgb(string_type):                       # spec §8 override — a mono string is a POINT
        return "POINT"
    if role == "MATRIX":
        return "2D_SURFACE"
    if role in ("MEGA_TREE", "SPINNER", "STAR"):
        return "2D_RADIAL"
    if role in ("OUTLINE", "PATH"):
        return "LINEAR_HIGH" if nodes >= LINEAR_HIGH_NODES else "LINEAR_LOW"
    if role in ("ARCH", "CANE", "ICICLES", "SNOWFLAKE", "WINDOW", "MINI_TREE"):
        return "LINEAR_LOW"
    if role == "SINGING_FACE":
        return "SPECIAL"
    if role == "SIGN":
        return "2D_SURFACE"
    if role in ("FLOOD", "CUSTOM_PROP"):
        # a very large dense Custom is really a matrix surface (spec §8)
        if role == "CUSTOM_PROP" and nodes >= DENSE_CUSTOM_NODES:
            return "2D_SURFACE"
        return "POINT"
    return "POINT"


# ------------------------------------------------------------------------------------------------
# derive_spatial — spec §4: exclude outliers FIRST, then normalize (decision 5)
# ------------------------------------------------------------------------------------------------
_ORDERED_ROLES = ("ARCH", "MINI_TREE", "CANE", "WINDOW", "SNOWFLAKE", "SPINNER")
MIRROR_X_TOL = 0.05
MIRROR_Y_TOL = 0.05
FOCAL_AREA_FRACTION = 0.15      # a prop whose visual area exceeds ~15% of the display is focal


@dataclass
class SpatialSummary:
    width_units: float          # raw world-x span of the (non-outlier) bounding box
    focal_x: float              # the focal center's normalized x (mega tree, else bbox center)
    symmetric: bool             # ≥1 mirror pair found → the display is (partly) symmetric
    excluded: list[Prop] = field(default_factory=list)   # parked/zero-node models, for review


def derive_spatial(props: list[Prop], *, invert_x: bool = False) -> SpatialSummary:
    """Fill each prop's spatial fields from world positions; return a display summary.

    Order (spec §4/§8): outlier exclusion FIRST (a parked model must not stretch normalization),
    then normalize, bands/sides, sweep order, mirror pairs, center distance, focal flags."""
    live = [p for p in props if p.nodes > 0]
    excluded = [p for p in props if p.nodes <= 0]

    if not live:
        return SpatialSummary(width_units=0.0, focal_x=0.5, symmetric=False, excluded=list(props))

    # (1) outlier exclusion — a model > 2× the display span outside the main bbox is parked.
    xs = sorted(p.wx for p in live)
    # A robust "core" span that trims the extreme(s) so one parked model can't define the span:
    # the inter-decile range for a big layout, else the range with the single min/max dropped.
    def _core_span(vals: list[float]) -> float:
        n = len(vals)
        if n >= 10:
            core = vals[n // 10: n - n // 10]
        elif n >= 3:
            core = vals[1:-1]                       # drop the single min + max
        else:
            core = vals
        return max((core[-1] - core[0]) if core else 0.0, 1e-6)
    span_x = _core_span(xs)
    # median-based center for outlier distance
    cx = xs[len(xs) // 2]
    kept: list[Prop] = []
    for p in live:
        if abs(p.wx - cx) > 2.0 * span_x and len(live) > 3:
            excluded.append(p)
        else:
            kept.append(p)
    if not kept:                                   # everything looked like an outlier → keep all
        kept = live
        excluded = [p for p in props if p.nodes <= 0]

    # (2) normalize x/y over the kept bbox; ground→top; invert_x flips x.
    minx = min(p.wx for p in kept)
    maxx = max(p.wx for p in kept)
    miny = min(p.wy for p in kept)
    maxy = max(p.wy for p in kept)
    dx = max(maxx - minx, 1e-6)
    dy = max(maxy - miny, 1e-6)
    for p in kept:
        nx = (p.wx - minx) / dx
        p.x = (1.0 - nx) if invert_x else nx
        p.y = (p.wy - miny) / dy
    for p in excluded:
        p.x, p.y = 0.0, 0.0

    # (3) bands GROUND/MID/ROOF at y cuts 0.33/0.66
    for p in kept:
        p.band = "GROUND" if p.y < 0.33 else ("MID" if p.y < 0.66 else "ROOF")

    # (4) sides LEFT <0.45, CENTER 0.45–0.55, RIGHT >0.55
    for p in kept:
        p.side = "LEFT" if p.x < 0.45 else ("CENTER" if p.x <= 0.55 else "RIGHT")

    # (5) sweep order within each multi-instance ordered role, by x (1..N)
    from collections import defaultdict
    by_role: dict[str, list[Prop]] = defaultdict(list)
    for p in kept:
        by_role[p.role].append(p)
    for role in _ORDERED_ROLES:
        members = sorted(by_role.get(role, []), key=lambda q: q.x)
        if len(members) > 1:
            for i, p in enumerate(members, start=1):
                p.sweep_order = i

    # (6) mirror pairs: same role, |x1+x2-1| ≤ tol and |y1-y2| ≤ tol → set mirror_of on BOTH.
    for role, members in by_role.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if abs(a.x + b.x - 1.0) <= MIRROR_X_TOL and abs(a.y - b.y) <= MIRROR_Y_TOL:
                    a.mirror_of, b.mirror_of = b.name, a.name
    symmetric = any(p.mirror_of for p in kept)

    # (7) center distance from the focal center (MEGA_TREE if present, else bbox center)
    mega = next((p for p in kept if p.role == "MEGA_TREE"), None)
    focal_x = mega.x if mega is not None else 0.5
    focal_y = mega.y if mega is not None else 0.5
    for p in kept:
        p.center_dist = ((p.x - focal_x) ** 2 + (p.y - focal_y) ** 2) ** 0.5

    # (8) focal flags: MEGA_TREE, MATRIX, and any prop whose visual area exceeds ~15% of the display.
    total_area = max(dx * dy, 1e-6)
    for p in kept:
        area_frac = 0.0
        # scale-derived area is unavailable here (Prop carries no scale) → approximate by node
        # budget relative to the densest prop, which correlates with on-screen area for a layout.
        max_nodes = max((q.nodes for q in kept), default=1) or 1
        area_frac = p.nodes / max_nodes
        p.focal = (p.role in ("MEGA_TREE", "MATRIX")) or (area_frac >= 0.85 and p.nodes >= 200)
        _ = total_area  # (kept for parity with spec's area language; node budget is the proxy)

    return SpatialSummary(width_units=maxx - minx, focal_x=focal_x, symmetric=symmetric,
                          excluded=excluded)
