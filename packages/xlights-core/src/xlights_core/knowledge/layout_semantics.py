"""Semantic-group plan (SEM_ groups) + canonical render order for an xLights display.

Builds the SEM_ group plan from classified Props (spec §5), patches SEM_ group grid size,
and authors the canonical-order view / sequence render order.
Implements xlights-layout-semantics-spec.md §5, §7. See [[craft-roadmap]]."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

_NULL_RE = re.compile(r"(?i)\bnull\b")        # placeholder/non-displayed models — exclude from all groups


def is_null_model(name: str) -> bool:
    return bool(_NULL_RE.search(name or ""))


@dataclass
class Prop:
    name: str
    display_as: str
    role: str = "CUSTOM_PROP"
    res: str = "POINT"
    nodes: int = 0
    x: float = 0.0
    y: float = 0.0
    band: str = "MID"
    side: str = "CENTER"
    center_dist: float = 0.0
    sweep_order: int | None = None
    focal: bool = False
    confidence: float = 1.0
    wx: float = 0.0
    wy: float = 0.0
    groups: list[str] = field(default_factory=list)


_ROLE_GROUP = {"OUTLINE": "SEM_OUTLINE", "WINDOW": "SEM_WINDOWS", "ARCH": "SEM_ARCHES",
               "MINI_TREE": "SEM_MINITREES", "CANE": "SEM_CANES", "ICICLES": "SEM_ICICLES",
               "FLOOD": "SEM_FLOODS", "SNOWFLAKE": "SEM_SNOWFLAKES", "SPINNER": "SEM_SPINNERS",
               "PATH": "SEM_PATH"}
_NON_ENSEMBLE = ("SINGING_FACE", "SIGN")          # excluded from ensemble groups (spec §5.5)


def build_sem_groups(props: list[Prop]) -> dict[str, list[str]]:
    """The SEM_ group plan (name -> member model names), spec §5."""
    from collections import defaultdict
    byrole: dict[str, list[Prop]] = defaultdict(list)
    for p in props:
        byrole[p.role].append(p)
    g: dict[str, list[str]] = {}
    for role, gname in _ROLE_GROUP.items():                         # §5.1 role groups
        if byrole.get(role):
            g[gname] = [p.name for p in byrole[role]]
    for role in ("ARCH", "MINI_TREE", "CANE"):                      # §5.2 ordered LTR
        ordered = sorted((p for p in byrole.get(role, []) if p.sweep_order), key=lambda q: q.sweep_order)
        if len(ordered) > 1:
            g[f"{_ROLE_GROUP[role]}_LTR"] = [p.name for p in ordered]
    for band, gname in (("ROOF", "SEM_BAND_ROOF"), ("MID", "SEM_BAND_MID"), ("GROUND", "SEM_BAND_GROUND")):
        g[gname] = [p.name for p in props if p.band == band and p.role not in _NON_ENSEMBLE]
    for side, gname in (("LEFT", "SEM_SIDE_LEFT"), ("CENTER", "SEM_SIDE_CENTER"), ("RIGHT", "SEM_SIDE_RIGHT")):
        g[gname] = [p.name for p in props if p.side == side and p.role not in _NON_ENSEMBLE]
    g["SEM_ALL"] = [p.name for p in props if p.role not in _NON_ENSEMBLE]
    # Subtractive ensembles (scene cookbook §2): the bed goes on ALL-LESS-* so the featured
    # prop never receives it — no blending arithmetic, no bed ghosting through the feature.
    focal = {p.name for p in props if p.focal}
    rhythm = {p.name for p in props if p.role in ("ARCH", "CANE", "MINI_TREE")}
    g["SEM_ALL_LESS_FOCAL"] = [n for n in g["SEM_ALL"] if n not in focal]
    g["SEM_ALL_LESS_FOCAL_RHYTHM"] = [n for n in g["SEM_ALL"] if n not in focal | rhythm]
    g["SEM_FOCAL"] = [p.name for p in props if p.focal]
    g["SEM_ACCENTS"] = [p.name for p in props if not p.focal and p.role not in (("OUTLINE",) + _NON_ENSEMBLE)]
    g["SEM_HOUSE"] = [p.name for p in props if p.role in ("OUTLINE", "WINDOW", "ICICLES")]
    g["SEM_YARD"] = [p.name for p in props if p.band == "GROUND" and p.role != "FLOOD"
                     and p.role not in _NON_ENSEMBLE]
    return {k: v for k, v in g.items() if v}


# xLights' default Max Grid Size (400) DOWNSCALES a group-canvas buffer whose actual extent is
# larger (SEM_ARCHES 1144, SEM_FOCAL 1111...) and WARNs on every render. 1200 covers the largest
# observed extent; the cost applies only to group-canvas effects — which are the buffer's point.
SEM_GRID_SIZE = 1200


def patch_sem_gridsize(rgb_path, size: int = SEM_GRID_SIZE) -> int:
    """Set GridSize on existing SEM_ groups in-place (idempotent; user groups untouched).
    Returns the number of groups updated. xLights loads it at the next restart."""
    import os
    from pathlib import Path
    p = Path(rgb_path)
    tree = ET.parse(p)
    mg = tree.getroot().find("modelGroups")
    if mg is None:
        return 0
    n = 0
    for el in mg.findall("modelGroup"):
        if el.get("name", "").startswith("SEM_") and el.get("GridSize") != str(size):
            el.set("GridSize", str(size))
            n += 1
    if n:
        tmp = p.with_suffix(p.suffix + ".tmp")
        tree.write(tmp, encoding="UTF-8", xml_declaration=True)
        os.replace(tmp, p)
    return n


# -- render order (cookbook §2 / layering guide §7): later rows WIN overlaps --------------------

_ORDER_TIERS = (
    # the whole-display base bed must render FIRST (top) so everything else paints over it —
    # ABOVE the zone beds (bands/sides), independent of the layout's model-file order
    ("base",    lambda n: n in ("SEM_ALL", "SEM_ALL_LESS_FOCAL", "SEM_ALL_LESS_FOCAL_RHYTHM")),
    ("bed",     lambda n: n.startswith(("SEM_BAND_", "SEM_SIDE_"))),    # zone beds, under features
    ("frame",   lambda n: n in ("SEM_OUTLINE", "SEM_WINDOWS", "SEM_ICICLES", "SEM_PATH", "SEM_HOUSE",
                                "SEM_YARD")),
    ("rhythm",  lambda n: n.startswith(("SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"))),
    ("other",   lambda n: True),                       # plain groups + individual models
    ("focal",   lambda n: n == "SEM_FOCAL" or "matrix" in n.lower()),
    ("accent",  lambda n: n.startswith(("SEM_SNOWFLAKES", "SEM_SPINNERS")) or "star" in n.lower()),
)


def _order_tier(name: str) -> int:
    # specific tiers checked before the "other" catch-all (index 4)
    for idx in (6, 5, 0, 1, 2, 3):
        if _ORDER_TIERS[idx][1](name):
            return idx
    return 4


def canonical_order(names: list[str]) -> list[str]:
    """Render order: beds at the TOP (painted over) → frame → rhythm → everything → focal →
    accents at the BOTTOM (win overlaps). Stable within a tier; null placeholders excluded."""
    live = [n for n in names if n and not is_null_model(n)]
    return sorted(live, key=_order_tier)     # sorted() is stable — input order breaks tier ties


def patch_view(rgb_path, view_name: str = "SEM Master") -> bool:
    """Author/update a canonical-order view in rgbeffects.xml (idempotent, atomic, best-effort).
    xLights loads views at startup — the view becomes usable on the next restart."""
    import os
    from pathlib import Path
    try:
        p = Path(rgb_path)
        tree = ET.parse(p)
        root = tree.getroot()
        names: list[str] = []
        mg = root.find("modelGroups")
        for g in (mg.findall("modelGroup") if mg is not None else []):
            names.append(g.get("name", ""))
        models = root.find("models")
        for m in (models.findall("model") if models is not None else []):
            if m.get("LayoutGroup") in (None, "Default"):
                names.append(m.get("name", ""))
        ordered = canonical_order(names)
        views = root.find("views")
        if views is None:
            views = ET.SubElement(root, "views")
        for v in list(views.findall("view")):
            if v.get("name") == view_name:
                views.remove(v)                        # idempotent replace
        ET.SubElement(views, "view", {"name": view_name, "models": ",".join(ordered)})
        tmp = p.with_suffix(p.suffix + ".tmp")
        tree.write(tmp, encoding="UTF-8", xml_declaration=True)
        os.replace(tmp, p)
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort
        log.warning("patch_view failed for %s: %s", rgb_path, exc)
        return False


def patch_xsq_render_order(xsq_path) -> bool:
    """Reorder a saved sequence's model rows canonically (timing rows keep their positions at the
    top). Atomic, best-effort — the final file gets deliberate precedence even before the
    canonical view is active in xLights."""
    import os
    from pathlib import Path
    try:
        p = Path(xsq_path)
        tree = ET.parse(p)
        root = tree.getroot()
        changed = False
        for tag in ("DisplayElements", "ElementEffects"):
            parent = root.find(tag)
            if parent is None:
                continue
            kids = list(parent)
            timing = [k for k in kids if k.get("type") == "timing"]
            model = [k for k in kids if k.get("type") == "model"]
            other = [k for k in kids if k not in timing and k not in model]
            order = {n: i for i, n in enumerate(canonical_order([k.get("name", "") for k in model]))}
            model.sort(key=lambda k: order.get(k.get("name", ""), 10**6))
            for k in kids:
                parent.remove(k)
            for k in timing + other + model:
                parent.append(k)
            changed = True
        if not changed:
            return False
        tmp = p.with_suffix(p.suffix + ".tmp")
        tree.write(tmp, encoding="UTF-8", xml_declaration=True)
        os.replace(tmp, p)
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort
        log.warning("patch_xsq_render_order failed for %s: %s", xsq_path, exc)
        return False
