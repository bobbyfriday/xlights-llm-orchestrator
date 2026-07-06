"""xLights layout parser: rgbeffects.xml (models) + networks.xml (controllers) →
Models with per-pixel WORLD coordinates.

Ported near-verbatim from the proven xlight-autosequencer/src/video/layout.py
(the Scale×2-for-boxed vs per-pixel-for-matrix gotcha + Matrix/Arch/Custom/Cube/Star/Tree
geometry were worked out there). Added: a placed-vs-skipped model count so a
silently-incomplete layout is surfaced rather than mis-judged by the critic.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


@dataclass
class Controller:
    name: str
    start: int   # absolute 0-based start channel in the FSEQ
    length: int


@dataclass
class Model:
    name: str
    display_as: str
    start_channel: int   # absolute, 0-based
    n_pixels: int
    parm1: int
    parm2: int
    parm3: int
    world_x: float
    world_y: float
    world_z: float
    scale_x: float
    scale_y: float
    scale_z: float
    rotate_x: float
    rotate_y: float
    rotate_z: float
    x2: float = 0.0
    y2: float = 0.0
    z2: float = 0.0
    height: float = 1.0
    custom_grid: list[list[int]] = field(default_factory=list)
    custom_w: int = 0
    custom_h: int = 0


def parse_controllers(networks_path: str | Path) -> dict[str, Controller]:
    """Walk xlights_networks.xml, sort by Id, accumulate channel ranges."""
    root = ET.parse(networks_path).getroot()
    items = []
    for c in root.findall("Controller"):
        idn = int(c.attrib.get("Id", 0))
        name = c.attrib["Name"]
        net = c.find("network")
        max_ch = int(net.attrib.get("MaxChannels", 0)) if net is not None else 0
        items.append((idn, name, max_ch, c.attrib.get("Protocol", "")))
    items.sort()
    out: dict[str, Controller] = {}
    cursor = 0
    for _, name, max_ch, proto in items:
        if proto == "Player Only" or max_ch == 0:
            out[name] = Controller(name=name, start=cursor, length=0)
            continue
        out[name] = Controller(name=name, start=cursor, length=max_ch)
        cursor += max_ch
    return out


_START_PAT = re.compile(r"!([^:]+):(\d+)")


def resolve_start_channel(start_str: str, controllers: dict[str, Controller]) -> int | None:
    """Resolve `!Controller:N` to absolute 0-based channel; or parse a plain int."""
    m = _START_PAT.match(start_str.strip())
    if not m:
        try:
            return int(start_str) - 1
        except ValueError:
            return None
    name, ch = m.group(1), int(m.group(2))
    ctl = controllers.get(name)
    return None if ctl is None else ctl.start + ch - 1


def _parse_custom_model(s: str) -> tuple[list[list[int]], int, int]:
    rows = []
    width = 0
    for raw_row in s.split(";"):
        cells = []
        for c in raw_row.split(","):
            c = c.strip()
            try:
                cells.append(int(c) if c else 0)
            except ValueError:
                cells.append(0)
        rows.append(cells)
        width = max(width, len(cells))
    for r in rows:
        r.extend([0] * (width - len(r)))
    return rows, width, len(rows)


def parse_models(rgbeffects_path: str | Path,
                 controllers: dict[str, Controller]) -> list[Model]:
    """Return one Model per top-level <model>. Logs placed-vs-skipped count."""
    root = ET.parse(rgbeffects_path).getroot()
    out: list[Model] = []
    total = skipped = 0
    models_el = root.find("models")
    if models_el is None:
        log.warning("layout: no <models> element in %s", rgbeffects_path)
        return out
    for m in models_el.findall("model"):
        # Only the Default preview belongs in the render; models parked in other
        # layout groups would skew the bounding box/scale.
        if m.get("LayoutGroup") not in (None, "Default"):  # default preview only
            continue
        total += 1
        sc = resolve_start_channel(m.attrib.get("StartChannel", "1"), controllers)
        if sc is None:
            skipped += 1
            continue
        try:
            p1 = int(m.attrib.get("parm1", 1))
            p2 = int(m.attrib.get("parm2", 1))
            p3 = int(m.attrib.get("parm3", 1))
        except ValueError:
            skipped += 1
            continue

        display_as = m.attrib.get("DisplayAs", "Single Line")
        if display_as == "Custom":
            grid_str = m.attrib.get("CustomModel", "")
            grid, gw, gh = _parse_custom_model(grid_str) if grid_str else ([], 0, 0)
            n_pix = max((max(row) for row in grid if row), default=0)
        elif display_as == "Cube":
            n_pix, grid, gw, gh = p1 * p2 * p3, [], 0, 0
        else:
            n_pix, grid, gw, gh = p1 * p2, [], 0, 0

        try:
            f = lambda k, d=0.0: float(m.attrib.get(k) or d)  # noqa: E731
            out.append(Model(
                name=m.attrib.get("name", "?"), display_as=display_as,
                start_channel=sc, n_pixels=n_pix, parm1=p1, parm2=p2, parm3=p3,
                world_x=f("WorldPosX"), world_y=f("WorldPosY"), world_z=f("WorldPosZ"),
                scale_x=f("ScaleX", 1), scale_y=f("ScaleY", 1), scale_z=f("ScaleZ", 1),
                rotate_x=f("RotateX"), rotate_y=f("RotateY"), rotate_z=f("RotateZ"),
                x2=f("X2"), y2=f("Y2"), z2=f("Z2"), height=f("Height", 1),
                custom_grid=grid, custom_w=gw, custom_h=gh))
        except ValueError:
            skipped += 1
    log.info("layout: placed %d models, skipped %d (unresolved/invalid) of %d",
             len(out), skipped, total)
    return out


# ---- Per-model pixel placement in WORLD coordinates (see module docstring) ----

def _rot_matrix(rx_deg: float, ry_deg: float, rz_deg: float) -> np.ndarray:
    rx, ry, rz = np.deg2rad([rx_deg, ry_deg, rz_deg])
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float32)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float32)
    return Rz @ Ry @ Rx


def _arches_world(model: Model) -> np.ndarray:
    n = model.n_pixels
    positions = np.zeros((n, 3), dtype=np.float32)
    arches = max(model.parm1, 1)
    per_arch = max(model.parm2, 1)
    p1 = np.array([model.world_x, model.world_y, model.world_z], dtype=np.float32)
    chord = np.array([model.x2, model.y2, model.z2], dtype=np.float32)
    span = float(np.linalg.norm(chord))
    if span < 1e-3:
        return positions
    peak_dir = np.array([0, 1, 0], dtype=np.float32)
    peak_height = model.height * span * 0.5
    for ai in range(arches):
        arch_p1 = p1 + (ai / arches) * chord
        arch_chord = chord / arches
        for j in range(per_arch):
            idx = ai * per_arch + j
            if idx >= n:
                break
            t = j / max(per_arch - 1, 1)
            base = arch_p1 + arch_chord * t
            positions[idx] = base + peak_dir * peak_height * np.sin(np.pi * t)
    return positions


def _line_world(model: Model) -> np.ndarray:
    n = model.n_pixels
    positions = np.zeros((n, 3), dtype=np.float32)
    p1 = np.array([model.world_x, model.world_y, model.world_z], dtype=np.float32)
    chord = np.array([model.x2, model.y2, model.z2], dtype=np.float32)
    if np.linalg.norm(chord) < 1e-3:
        chord = np.array([max(n - 1, 1), 0, 0], dtype=np.float32)
    for i in range(n):
        positions[i] = p1 + chord * (i / max(n - 1, 1))
    return positions


def _boxed_world(model: Model, local: np.ndarray) -> np.ndarray:
    pts = local.copy()
    pts[:, 0] *= model.scale_x * 2.0
    pts[:, 1] *= model.scale_y * 2.0
    pts[:, 2] *= model.scale_z * 2.0
    if abs(model.rotate_x) + abs(model.rotate_y) + abs(model.rotate_z) > 0.01:
        pts = pts @ _rot_matrix(model.rotate_x, model.rotate_y, model.rotate_z).T
    pts[:, 0] += model.world_x
    pts[:, 1] += model.world_y
    pts[:, 2] += model.world_z
    return pts


def _parm_world(model: Model, local: np.ndarray, size: tuple[float, float, float]) -> np.ndarray:
    w, h, d = size
    pts = local.copy()
    pts[:, 0] -= w / 2
    pts[:, 1] -= h / 2
    pts[:, 2] -= d / 2
    pts[:, 0] *= model.scale_x
    pts[:, 1] *= model.scale_y
    pts[:, 2] *= model.scale_z
    if abs(model.rotate_x) + abs(model.rotate_y) + abs(model.rotate_z) > 0.01:
        pts = pts @ _rot_matrix(model.rotate_x, model.rotate_y, model.rotate_z).T
    pts[:, 0] += model.world_x
    pts[:, 1] += model.world_y
    pts[:, 2] += model.world_z
    return pts


def model_world_pixels(model: Model) -> np.ndarray:
    """Return Nx3 WORLD-coordinate positions for every pixel of this model."""
    n = model.n_pixels
    if n <= 0:
        return np.zeros((0, 3), dtype=np.float32)
    da = model.display_as

    if da == "Arches":
        return _arches_world(model)
    if da == "Single Line":
        return _line_world(model)
    if da == "Custom" and model.custom_grid:
        local = np.zeros((n, 3), dtype=np.float32)
        for r, row in enumerate(model.custom_grid):
            for c, pix in enumerate(row):
                if 0 < pix <= n:
                    local[pix - 1] = (c, model.custom_h - 1 - r, 0)
        return _parm_world(model, local, (model.custom_w, model.custom_h, 1))
    if da in ("Horiz Matrix", "Vert Matrix"):
        strings = max(model.parm1, 1)
        per_string = max(model.parm2, 1)
        strands = max(model.parm3, 1)
        per_strand = max(per_string // strands, 1)
        local = np.zeros((n, 3), dtype=np.float32)
        if da == "Vert Matrix":
            cols, rows = strings * strands, per_strand
            for i in range(n):
                string, in_string = i // per_string, i % per_string
                strand, in_strand = in_string // per_strand, in_string % per_strand
                x = string * strands + strand
                y = in_strand if strand % 2 == 0 else (per_strand - 1 - in_strand)
                local[i] = (x, rows - 1 - y, 0)
        else:
            cols, rows = per_strand, strings * strands
            for i in range(n):
                string, in_string = i // per_string, i % per_string
                strand, in_strand = in_string // per_strand, in_string % per_strand
                y = string * strands + strand
                x = in_strand if strand % 2 == 0 else (per_strand - 1 - in_strand)
                local[i] = (x, rows - 1 - y, 0)
        return _parm_world(model, local, (cols, rows, 1))
    if da == "Cube":
        w, h, d = max(model.parm1, 1), max(model.parm2, 1), max(model.parm3, 1)
        per_face = w * h
        local = np.zeros((n, 3), dtype=np.float32)
        for i in range(n):
            slab, within = i // per_face, i % per_face
            r, c = within // w, within % w
            local[i] = ((c + 0.5) / w - 0.5, 0.5 - (r + 0.5) / h, (slab + 0.5) / d - 0.5)
        return _boxed_world(model, local)
    if da == "Star":
        local = np.zeros((n, 3), dtype=np.float32)
        for i in range(n):
            ring, within = i // max(model.parm2, 1), i % max(model.parm2, 1)
            radius = 0.5 * (ring + 1) / max(model.parm1, 1)
            angle = 2 * np.pi * within / max(model.parm2, 1) - np.pi / 2
            local[i] = (radius * np.cos(angle), radius * np.sin(angle), 0)
        return _boxed_world(model, local)
    if da.startswith("Tree"):
        local = np.zeros((n, 3), dtype=np.float32)
        strings, per = max(model.parm1, 1), max(model.parm2, 1)
        for s in range(strings):
            base_angle = 2 * np.pi * s / strings
            for j in range(per):
                idx = s * per + j
                if idx >= n:
                    break
                t = j / max(per - 1, 1)
                radius = 0.5 * (1 - t)
                angle = base_angle + t * np.pi
                local[idx] = (radius * np.cos(angle), t - 0.5, radius * np.sin(angle))
        return _boxed_world(model, local)

    local = np.zeros((n, 3), dtype=np.float32)
    for i in range(n):
        local[i] = (i / max(n - 1, 1), 0, 0)
    return _parm_world(model, local, (max(n, 1), 1, 1))
