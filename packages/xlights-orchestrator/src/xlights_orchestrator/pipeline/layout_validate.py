"""F-E slice 5 — offline §7 validation of an onboarded layout (deterministic-first).

No xLights: synthesize the test frames' channel data directly, render them through the offline
preview renderer, and gate the command on a DETERMINISTIC sweep-centroid check + structural checks.
A role-color contact sheet PNG is written for human/vision inspection (advisory).

- ``write_fseq_v2_uncompressed`` — a minimal uncompressed FSEQ v2 writer the read side
  ``preview/fseq.load_fseq`` round-trips (comp type 0, channel data at data_offset).
- ``role_color_frames`` / ``sweep_frames`` — synthetic frames (spec §7.1 / §7.3).
- ``check_sweep`` — per frame the lit-pixel world-x centroid must be strictly increasing.
- ``structural_checks`` — every SEM_ member exists; no SEM_ group empty; SEM_ALL excludes
  SINGING_FACE/SIGN; every _LTR member order matches its sweep_order.
- ``role_color_sheet`` — a labeled contact sheet PNG (needs the [preview] extra).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

# ROLE → an RGB triple chosen hue-distant so adjacent roles read apart on the contact sheet.
ROLE_COLORS: dict[str, tuple[int, int, int]] = {
    "MEGA_TREE": (0, 255, 0), "MINI_TREE": (0, 180, 90), "ARCH": (255, 0, 0),
    "CANE": (255, 120, 0), "ICICLES": (0, 200, 255), "STAR": (255, 255, 0),
    "SPINNER": (200, 0, 255), "MATRIX": (255, 255, 255), "WINDOW": (0, 90, 255),
    "OUTLINE": (255, 0, 200), "FLOOD": (120, 120, 120), "SINGING_FACE": (255, 200, 200),
    "SIGN": (180, 255, 0), "PATH": (0, 255, 180), "SNOWFLAKE": (200, 220, 255),
    "CUSTOM_PROP": (100, 100, 100),
}
_FALLBACK_COLOR = (255, 255, 255)


# ------------------------------------------------------------------------------------------------
# FSEQ v2 uncompressed writer (round-trips preview/fseq.load_fseq)
# ------------------------------------------------------------------------------------------------
def write_fseq_v2_uncompressed(path, frames, frame_ms: int = 50) -> Path:
    """Write an uncompressed FSEQ v2 (PSEQ) file. ``frames`` is a [num_frames, channels] uint8
    array-like. Header matches preview/fseq.load_fseq's uncompressed branch (comp type 0)."""
    import numpy as np
    arr = np.asarray(frames, dtype=np.uint8)
    if arr.ndim != 2:
        raise ValueError("frames must be [num_frames, channels]")
    num_frames, channels = arr.shape
    data_offset = 40
    h = bytearray(data_offset)
    h[0:4] = b"PSEQ"
    struct.pack_into("<H", h, 4, data_offset)     # data offset
    h[6], h[7] = 0, 2                             # minor, major (v2)
    struct.pack_into("<I", h, 10, channels)
    struct.pack_into("<I", h, 14, num_frames)
    h[18] = frame_ms & 0xFF
    # bytes 20-21 stay 0: compression type 0 (uncompressed), no block index.
    p = Path(path)
    p.write_bytes(bytes(h) + arr.tobytes())
    return p


# ------------------------------------------------------------------------------------------------
# synthetic frames (spec §7.1 role-color, §7.3 sweep)
# ------------------------------------------------------------------------------------------------
def _channel_map(models) -> dict[str, tuple[int, int]]:
    """model name → (start_channel, n_pixels) from parsed preview Models."""
    return {m.name: (m.start_channel, m.n_pixels) for m in models}


def role_color_frames(manifest, models):
    """One frame per role present: that role's member channels lit at its hue-distant color, the
    rest dark (spec §7.1). Returns (frames uint8[R, C], labels list[str])."""
    import numpy as np
    chmap = _channel_map(models)
    total_channels = max((s + 3 * n for s, n in chmap.values()), default=0)
    props = getattr(manifest, "props", None) or []
    by_role: dict[str, list[str]] = {}
    for p in props:
        by_role.setdefault(p.role, []).append(p.id)
    roles = [r for r in by_role if any(m in chmap for m in by_role[r])]
    frames = np.zeros((len(roles), total_channels), dtype=np.uint8)
    for i, role in enumerate(roles):
        r, g, b = ROLE_COLORS.get(role, _FALLBACK_COLOR)
        for name in by_role[role]:
            if name not in chmap:
                continue
            sc, n = chmap[name]
            for px in range(n):
                base = sc + 3 * px
                if base + 2 < total_channels:
                    frames[i, base], frames[i, base + 1], frames[i, base + 2] = r, g, b
    return frames, roles


def sweep_frames(group_members, models):
    """K frames for an ordered group: member i lit ALONE (white) in frame i (spec §7.3)."""
    import numpy as np
    chmap = _channel_map(models)
    members = [m for m in group_members if m in chmap]
    total_channels = max((s + 3 * n for s, n in chmap.values()), default=0)
    frames = np.zeros((len(members), total_channels), dtype=np.uint8)
    for i, name in enumerate(members):
        sc, n = chmap[name]
        for px in range(n):
            base = sc + 3 * px
            if base + 2 < total_channels:
                frames[i, base:base + 3] = 255
    return frames, members


# ------------------------------------------------------------------------------------------------
# deterministic sweep-centroid check (uses the renderer's world coords)
# ------------------------------------------------------------------------------------------------
@dataclass
class SweepResult:
    ok: bool
    centroids: list[float] = field(default_factory=list)
    recommend_invert: bool = False
    detail: str = ""


def check_sweep(frames, renderer) -> SweepResult:
    """Per frame, the lit-pixel world-x centroid (``renderer.world[:,0]`` weighted by channel value)
    must be STRICTLY INCREASING across frames. Backward → the x axis is inverted → recommend
    ``--invert-x``. Pure geometry, no xLights — the offline renderer is exact for 'which pixels lit,
    where' by construction (design decision 12)."""
    import numpy as np
    world_x = renderer.world[:, 0]
    ch = renderer.ch                                  # channel index of the R component per pixel
    centroids: list[float] = []
    for fi in range(len(frames)):
        row = np.asarray(frames[fi])
        # weight each pixel by its (clamped) lit value at its R channel
        weights = np.array([int(row[c]) if c < len(row) else 0 for c in ch], dtype=float)
        if weights.sum() <= 0:
            centroids.append(float("nan"))
            continue
        centroids.append(float((world_x * weights).sum() / weights.sum()))
    valid = [c for c in centroids if c == c]          # drop NaN (dark) frames
    if len(valid) < 2:
        return SweepResult(ok=True, centroids=centroids, detail="too few lit frames to judge")
    increasing = all(b > a for a, b in zip(valid, valid[1:]))
    decreasing = all(b < a for a, b in zip(valid, valid[1:]))
    if increasing:
        return SweepResult(ok=True, centroids=centroids)
    if decreasing:
        return SweepResult(ok=False, centroids=centroids, recommend_invert=True,
                           detail="sweep centroid decreases — x axis inverted; retry with --invert-x")
    return SweepResult(ok=False, centroids=centroids,
                       detail="sweep centroid not monotonic — check member order / geometry")


# ------------------------------------------------------------------------------------------------
# structural checks (pure, no renderer needed)
# ------------------------------------------------------------------------------------------------
_NON_ENSEMBLE_ROLES = ("SINGING_FACE", "SIGN")


def structural_checks(manifest, model_names) -> list[str]:
    """Deterministic gates (spec §7): every SEM_ member exists as a model; no SEM_ group empty;
    SEM_ALL excludes SINGING_FACE/SIGN; every _LTR member order matches sweep_order. Returns a list
    of violation strings (empty = pass)."""
    problems: list[str] = []
    names = set(model_names)
    props = {p.id: p for p in (getattr(manifest, "props", None) or [])}
    groups = getattr(manifest, "groups", None) or {}

    for gname, gr in groups.items():
        if not gr.members:
            problems.append(f"{gname} is empty")
        for m in gr.members:
            if m not in names:
                problems.append(f"{gname} references missing model {m!r}")

    all_grp = groups.get("SEM_ALL")
    if all_grp is not None:
        for m in all_grp.members:
            role = getattr(props.get(m), "role", None)
            if role in _NON_ENSEMBLE_ROLES:
                problems.append(f"SEM_ALL includes {role} member {m!r} (must be excluded)")

    for gname, gr in groups.items():
        if not gname.endswith("_LTR"):
            continue
        orders = [getattr(props.get(m), "sweep_order", None) for m in gr.members]
        if any(o is None for o in orders):
            problems.append(f"{gname} member missing sweep_order")
        elif orders != sorted(orders):
            problems.append(f"{gname} member order does not match sweep_order")
    return problems


# ------------------------------------------------------------------------------------------------
# role-color contact sheet (needs [preview] extras)
# ------------------------------------------------------------------------------------------------
def role_color_sheet(renderer, frames, labels, out_path, *, cell=(240, 160), cols=4) -> Path:
    """A labeled contact-sheet PNG next to the manifest — one cell per role frame (spec §7.2)."""
    from PIL import Image, ImageDraw

    n = len(labels)
    rows = (n + cols - 1) // cols
    cw, ch = cell
    sheet = Image.new("RGB", (cols * cw, rows * ch), (6, 6, 12))
    draw = ImageDraw.Draw(sheet)
    for i, label in enumerate(labels):
        png = renderer.render_frame_from(frames[i], canvas=(cw, ch - 16)) \
            if hasattr(renderer, "render_frame_from") else _render_cell(renderer, frames[i], cw, ch - 16)
        cell_img = Image.open(_bytesio(png)) if isinstance(png, (bytes, bytearray)) else png
        r, c = divmod(i, cols)
        sheet.paste(cell_img, (c * cw, r * ch + 16))
        draw.text((c * cw + 4, r * ch + 2), label, fill=(230, 230, 230))
    out = Path(out_path)
    sheet.save(out, format="PNG")
    return out


def _bytesio(b):
    import io
    return io.BytesIO(b)


# spec §7.2 vision question + the known offline-confusion failure modes (advisory prompt).
ROLE_COLOR_QUESTION = (
    "This is a labeled contact sheet of a Christmas-light layout: each cell lights ONE role's props "
    "at a distinct color, the rest dark. Does each colored region correspond to its labeled role? "
    "Watch for known misclassifications: a mega tree confused for a mini tree (or vice versa), an "
    "outline strand classified as a PATH, a dense Custom mesh that is really a matrix. Report only "
    "clear mismatches; do not invent issues. Findings are advisory."
)


def build_role_color_critique(sheet_png: bytes, labels: list[str]):
    """Build the advisory visual-critic payload (contact sheet + the §7.2 question). The CLI sends
    this to agents/visual_critic when a key is present; findings are printed, never auto-mutating."""
    from pydantic_ai import BinaryContent
    return [ROLE_COLOR_QUESTION + "\nRoles shown: " + ", ".join(labels),
            BinaryContent(data=bytes(sheet_png), media_type="image/png")]


def _render_cell(renderer, frame_row, w, h):
    """Render one synthetic frame to a PIL image using the renderer's projection + this frame's
    channel values (bypasses the renderer's own loaded frames)."""
    import numpy as np
    from PIL import Image
    sx, sy, ch, w_, h_ = renderer._project((w, h))
    row = np.asarray(frame_row)
    img = np.empty((h_, w_, 3), dtype=np.uint8)
    img[:] = (6, 6, 12)
    for k in range(3):
        vals = np.array([int(row[c + k]) if c + k < len(row) else 0 for c in ch], dtype=np.uint8)
        np.maximum.at(img[:, :, k], (sy, sx), vals)
    return Image.fromarray(img)
