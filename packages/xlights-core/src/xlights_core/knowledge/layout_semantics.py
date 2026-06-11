"""Derive a semantic model of an xLights display from rgbeffects.xml: classify each model into a
role + capability, compute spatial attributes, and build the SEM_ group plan + manifest.

Read-only here (classification + plan); the destructive rgbeffects edit lives in a separate patcher.
Implements xlights-layout-semantics-spec.md §2–§5. See [[craft-roadmap]]."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

_NULL_RE = re.compile(r"(?i)\bnull\b")        # placeholder/non-displayed models — exclude from all groups


def is_null_model(name: str) -> bool:
    return bool(_NULL_RE.search(name or ""))

# -- role taxonomy (spec §2) --------------------------------------------------
_DISPLAYAS_ROLE = {
    "Arches": "ARCH", "Icicles": "ICICLES", "Candy Canes": "CANE", "Star": "STAR",
    "Spinner": "SPINNER", "Matrix": "MATRIX", "Horiz Matrix": "MATRIX", "Vert Matrix": "MATRIX",
    "Window Frame": "WINDOW", "Wreath": "CUSTOM_PROP", "Sphere": "CUSTOM_PROP", "Cube": "CUSTOM_PROP",
}
_NAME_HEURISTICS = [
    (("roof", "gutter", "eave", "ridge", "outline", "peak", "fascia", "column", "garage"), "OUTLINE"),
    (("window", "door"), "WINDOW"),
    (("flood", "wash", "up light", "uplight"), "FLOOD"),
    (("face", "sing", "carol", "mouth"), "SINGING_FACE"),
    (("sign", "tune"), "SIGN"),
    (("drive", "walk", "path", "fence", "yard line"), "PATH"),
    (("flake",), "SNOWFLAKE"),
    (("spinner",), "SPINNER"),
    (("arch",), "ARCH"), (("cane",), "CANE"), (("star",), "STAR"), (("tree",), "MINI_TREE"),
    (("matrix", "panel", "grid"), "MATRIX"),
]
_ROLE_CAP = {
    "MATRIX": "2D_SURFACE", "MEGA_TREE": "2D_RADIAL", "SPINNER": "2D_RADIAL", "STAR": "2D_RADIAL",
    "OUTLINE": "LINEAR_HIGH", "PATH": "LINEAR_HIGH",
    "ARCH": "LINEAR_LOW", "CANE": "LINEAR_LOW", "ICICLES": "LINEAR_LOW", "WINDOW": "LINEAR_LOW",
    "MINI_TREE": "LINEAR_LOW", "SNOWFLAKE": "LINEAR_LOW",
    "FLOOD": "POINT", "SINGING_FACE": "SPECIAL", "SIGN": "2D_SURFACE", "CUSTOM_PROP": "POINT",
}
MEGA_TREE_NODES = 600


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


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def parse_models(rgb_path) -> list[Prop]:
    root = ET.parse(rgb_path).getroot()
    out: list[Prop] = []
    models = root.find("models")
    for m in (models.findall("model") if models is not None else []):
        if m.get("LayoutGroup") not in (None, "Default"):           # spec §8: default preview only
            continue
        p1, p2, p3 = (_f(m.get(k, 0)) for k in ("parm1", "parm2", "parm3"))
        out.append(Prop(
            name=m.get("name", ""), display_as=m.get("DisplayAs", ""),
            nodes=int(p1 * p2 * (p3 or 1)) if "Tree" in m.get("DisplayAs", "") else int(p1 * p2),
            wx=_f(m.get("WorldPosX")), wy=_f(m.get("WorldPosY"))))
    return out, {g.get("name"): (g.get("models") or "").split(",")
                 for g in (root.find("modelGroups").findall("modelGroup")
                           if root.find("modelGroups") is not None else [])}


def classify(p: Prop, group_hints: dict[str, str]) -> None:
    da = p.display_as
    role, conf = None, 1.0
    if da in _DISPLAYAS_ROLE:                                        # §3 step 1
        role = _DISPLAYAS_ROLE[da]
        if role == "CUSTOM_PROP":
            role = None
    if role is None and "Tree" in da:                               # §3 step 2
        role = "MEGA_TREE" if p.nodes >= MEGA_TREE_NODES else "MINI_TREE"
    if role is None:                                                # §3 step 3 (name)
        low = p.name.lower()
        for keys, r in _NAME_HEURISTICS:
            if any(k in low for k in keys):
                role, conf = r, 0.85
                break
    if role is None and p.name in group_hints:                      # §3 step 4 (group hint)
        role, conf = group_hints[p.name], 0.8
    if role is None:                                                # §3 → CUSTOM_PROP (review)
        role, conf = "CUSTOM_PROP", 0.5
    p.role, p.confidence, p.res = role, conf, _ROLE_CAP.get(role, "POINT")


def spatialize(props: list[Prop]) -> list[Prop]:
    """Normalize positions, exclude far-outliers (→ review), assign band/side/sweep/focal/center."""
    live = [p for p in props if p.role != "SINGING_FACE"] or props
    xs = sorted(p.wx for p in live); ys = sorted(p.wy for p in live)
    x0, x1 = xs[0], xs[-1]; y0, y1 = ys[0], ys[-1]
    spanx, spany = (x1 - x0) or 1.0, (y1 - y0) or 1.0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for p in props:
        if abs(p.wx - cx) > spanx or abs(p.wy - cy) > spany:        # §8 far-outlier → parked
            p.confidence = min(p.confidence, 0.4)
        p.x = max(0.0, min(1.0, (p.wx - x0) / spanx))
        p.y = max(0.0, min(1.0, (p.wy - y0) / spany))
        p.band = "GROUND" if p.y < 0.33 else "ROOF" if p.y > 0.66 else "MID"
        p.side = "LEFT" if p.x < 0.45 else "RIGHT" if p.x > 0.55 else "CENTER"
        p.center_dist = ((p.x - 0.5) ** 2 + (p.y - 0.5) ** 2) ** 0.5
        p.focal = p.role in ("MEGA_TREE", "MATRIX")
    # sweep order within each multi-instance role
    from collections import defaultdict
    byrole: dict[str, list[Prop]] = defaultdict(list)
    for p in props:
        byrole[p.role].append(p)
    for role, members in byrole.items():
        if role in ("ARCH", "MINI_TREE", "CANE", "WINDOW", "SNOWFLAKE", "SPINNER") and len(members) > 1:
            for i, p in enumerate(sorted(members, key=lambda q: q.x), 1):
                p.sweep_order = i
    return props


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


def analyze_layout(rgb_path) -> tuple[list[Prop], dict[str, list[str]], list[Prop], list[str]]:
    """Read-only: parse → classify → spatialize → SEM_ group plan + review list. No file edits.
    Null/placeholder models are excluded from props and every group."""
    all_props, group_models = parse_models(rgb_path)
    excluded = [p.name for p in all_props if is_null_model(p.name)]  # placeholders → no group
    props = [p for p in all_props if not is_null_model(p.name)]
    hints = {}                                                      # model name -> role from a matching group name
    for gname, members in group_models.items():
        low = gname.lower()
        for keys, r in _NAME_HEURISTICS:
            if any(k in low for k in keys):
                for mn in members:
                    hints.setdefault(mn.strip(), r)
                break
    for p in props:
        classify(p, hints)
    spatialize(props)
    groups = build_sem_groups(props)
    for name, members in groups.items():
        for mn in members:
            for p in props:
                if p.name == mn:
                    p.groups.append(name)
    review = [p for p in props if p.confidence < 0.8]
    return props, groups, review, excluded


_REMOVE_RE = re.compile(r"^(0[1-8]_|SEM_)")          # numbered taxonomy + our own SEM_ (idempotent)


def patch_rgbeffects(rgb_path, groups: dict[str, list[str]], *, ts: str) -> str | None:
    """Back up, remove the numbered (0N_) + existing SEM_ groups, add the new SEM_ groups; atomic.
    xLights MUST be closed (it rewrites this file from memory on exit). Returns the backup path."""
    import os
    import shutil
    from pathlib import Path
    p = Path(rgb_path)
    tree = ET.parse(p)
    mg = tree.getroot().find("modelGroups")
    if mg is None:
        return None
    bak = p.with_name(f"{p.stem}.{ts}.bak{p.suffix}")
    shutil.copy2(p, bak)
    for el in [e for e in mg.findall("modelGroup") if _REMOVE_RE.match(e.get("name", ""))]:
        mg.remove(el)                                # remove numbered + stale SEM_ (idempotent)
    for name, members in groups.items():
        ET.SubElement(mg, "modelGroup", {
            "selected": "0", "name": name, "layout": "minimalGrid", "GridSize": "400",
            "LayoutGroup": "Default", "models": ",".join(members)})
    tmp = p.with_suffix(p.suffix + ".tmp")
    tree.write(tmp, encoding="UTF-8", xml_declaration=True)
    os.replace(tmp, p)
    return str(bak)


def write_manifest(path, props: list[Prop], groups: dict[str, list[str]],
                   review: list[Prop], excluded: list[str], *, generated: str) -> None:
    import json
    from pathlib import Path
    LTR = {"SEM_ARCHES_LTR", "SEM_CANES_LTR", "SEM_MINITREES_LTR"}
    PER_PREVIEW = {"SEM_ALL", "SEM_FOCAL", "SEM_BAND_ROOF", "SEM_BAND_MID", "SEM_BAND_GROUND"}
    manifest = {
        "version": 1, "generated": generated,
        "display": {"traits": {
            "has_matrix": any(p.role == "MATRIX" for p in props),
            "has_megatree": any(p.role == "MEGA_TREE" for p in props),
            "arch_count": sum(p.role == "ARCH" for p in props)}},
        "props": [{"id": p.name, "role": p.role, "res": p.res, "nodes": p.nodes,
                   "pos": {"x": round(p.x, 3), "y": round(p.y, 3), "band": p.band,
                           "side": p.side, "center_dist": round(p.center_dist, 3)},
                   **({"sweep_order": p.sweep_order} if p.sweep_order else {}),
                   "focal": p.focal, "confidence": p.confidence, "groups": p.groups}
                  for p in props],
        "groups": {name: {"members": members, "ordered": name in LTR,
                          "layout_mode": "Horizontal Per Model" if name in LTR
                          else "Per Preview" if name in PER_PREVIEW else "Minimal Grid"}
                   for name, members in groups.items()},
        "excluded": excluded,
        "review": [p.name for p in review],
    }
    Path(path).write_text(json.dumps(manifest, indent=2))


# -- render order (cookbook §2 / layering guide §7): later rows WIN overlaps --------------------

_ORDER_TIERS = (
    ("bed",     lambda n: n in ("SEM_ALL", "SEM_ALL_LESS_FOCAL", "SEM_ALL_LESS_FOCAL_RHYTHM")
                          or n.startswith(("SEM_BAND_", "SEM_SIDE_"))),
    ("frame",   lambda n: n in ("SEM_OUTLINE", "SEM_WINDOWS", "SEM_ICICLES", "SEM_PATH", "SEM_HOUSE",
                                "SEM_YARD")),
    ("rhythm",  lambda n: n.startswith(("SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"))),
    ("other",   lambda n: True),                       # plain groups + individual models
    ("focal",   lambda n: n == "SEM_FOCAL" or "matrix" in n.lower()),
    ("accent",  lambda n: n.startswith(("SEM_SNOWFLAKES", "SEM_SPINNERS")) or "star" in n.lower()),
)


def _order_tier(name: str) -> int:
    # later tiers checked first so focal/accent outrank the catch-all
    for idx in (5, 4, 0, 1, 2):
        if _ORDER_TIERS[idx][1](name):
            return idx
    return 3


def canonical_order(names: list[str]) -> list[str]:
    """Render order: beds at the TOP (painted over) → frame → rhythm → everything → focal →
    accents at the BOTTOM (win overlaps). Stable within a tier; null placeholders excluded."""
    live = [n for n in names if n and not is_null_model(n)]
    return sorted(live, key=lambda n: (_order_tier(n), live.index(n)))


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
    except Exception:  # noqa: BLE001 — best-effort
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
    except Exception:  # noqa: BLE001
        return False
