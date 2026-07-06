"""Deterministic per-group render metrics from the compiled `.fseq` (I8 Tier 0).

The `.fseq` IS the true render — the exact per-node RGB of every frame. This module reduces it
to per-group brightness / lit-fraction / motion time-series in one vectorized pass, reading
CHANNEL VALUES (not the projected preview image). It therefore needs only FILE PATHS and numpy —
**no xLights client, no orchestrator import** (an F-J-alignment contract: keep this dependency-free
so a future headless-render path can reuse it verbatim). Unknown/empty groups are omitted; a group
whose members resolve to no channels is dropped.

`group_channel_index` joins `parse_models()` start_channel/n_pixels with the `<modelGroups>`
membership from rgbeffects.xml (recursively — a group may contain groups). `FseqSeries` computes,
per group g and frame t:
  - brightness  B[g][t] = mean over g's node max(R,G,B)   (matches the coverage sampler's proxy)
  - lit fraction L[g][t] = fraction of g's nodes with max(R,G,B) > lit_threshold (30)
  - motion      M[g][t] = mean over g's nodes of |v[t] - v[t-1]|   (frame-to-frame change)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from .fseq import load_fseq
from .layout import parse_controllers, parse_models

LIT_THRESHOLD = 30           # a node counts as "lit" above this max(R,G,B) (matches make_lit_sampler)


def _model_channels(rgbeffects_path, networks_path) -> dict[str, np.ndarray]:
    """model name -> the array of its per-node channel START indices (channel-bound to the fseq
    is the caller's job). Mirrors render.py's `start_channel + 3*arange(n_pixels)`."""
    controllers = parse_controllers(networks_path)
    models = parse_models(rgbeffects_path, controllers)
    out: dict[str, np.ndarray] = {}
    for m in models:
        if m.n_pixels <= 0:
            continue
        out[m.name] = m.start_channel + 3 * np.arange(m.n_pixels, dtype=np.int64)
    return out


def _group_members(rgbeffects_path) -> dict[str, list[str]]:
    """group name -> its raw `models=` member list (names may be models OR nested groups)."""
    root = ET.parse(rgbeffects_path).getroot()
    mg = root.find("modelGroups")
    out: dict[str, list[str]] = {}
    for g in (mg.findall("modelGroup") if mg is not None else []):
        name = g.get("name", "")
        members = [x.strip() for x in (g.get("models", "") or "").split(",") if x.strip()]
        if name:
            out[name] = members
    return out


def group_channel_index(rgbeffects_path, networks_path,
                        groups: list[str] | None = None) -> dict[str, np.ndarray]:
    """group name -> the concatenated per-node channel start indices of its member models.

    Resolves nested groups recursively (a modelGroup may list other groups). `groups` filters to
    a subset (unknown names omitted); None resolves every modelGroup. A group that resolves to no
    channels is dropped (never a blind entry). Channels are the START of each node's RGB triple.
    """
    rgbeffects_path, networks_path = Path(rgbeffects_path), Path(networks_path)
    model_ch = _model_channels(rgbeffects_path, networks_path)
    members = _group_members(rgbeffects_path)

    def resolve(name: str, seen: set[str]) -> list[int]:
        if name in model_ch:
            return list(model_ch[name])
        if name in members and name not in seen:
            seen.add(name)
            chans: list[int] = []
            for child in members[name]:
                chans.extend(resolve(child, seen))
            return chans
        return []

    want = groups if groups is not None else list(members)
    out: dict[str, np.ndarray] = {}
    for name in want:
        chans = resolve(name, set())
        if chans:
            arr = np.array(sorted(set(chans)), dtype=np.int64)
            out[name] = arr
    return out


class FseqSeries:
    """Per-group brightness / lit-fraction / motion time-series over a whole `.fseq`.

    Construct from the compiled render data + the group→channel index; slice by section time.
    Everything is float32 per-group series (the ~100 MB uint8 frame array is reduced immediately).
    """

    def __init__(self, fseq_path, group_index: dict[str, np.ndarray], *,
                 lit_threshold: int = LIT_THRESHOLD):
        header, frames = load_fseq(fseq_path)                 # frames: uint8 [num_frames, channels]
        self.step_ms = int(header.step_ms) or 50
        self.frames = int(header.frames)
        n_ch = int(header.channels)
        v = frames.astype(np.int16)                           # signed for the motion diff
        self.brightness: dict[str, np.ndarray] = {}
        self.lit: dict[str, np.ndarray] = {}
        self.motion: dict[str, np.ndarray] = {}
        self.groups: list[str] = []
        for name, starts in group_index.items():
            # each node's value proxy = max(R,G,B) at its channel triple (channel-bound)
            starts = starts[(starts + 2) < n_ch]
            if starts.size == 0:
                continue
            r = v[:, starts]; g = v[:, starts + 1]; b = v[:, starts + 2]
            node_val = np.maximum(np.maximum(r, g), b).astype(np.float32)   # [frames, nodes_g]
            self.brightness[name] = node_val.mean(axis=1)
            self.lit[name] = (node_val > lit_threshold).mean(axis=1)
            dmot = np.abs(np.diff(node_val, axis=0, prepend=node_val[:1]))
            self.motion[name] = dmot.mean(axis=1)
            self.groups.append(name)

    def _frame_slice(self, start_ms: int, end_ms: int) -> slice:
        s = max(0, int(start_ms) // self.step_ms)
        e = min(self.frames, max(s + 1, int(end_ms) // self.step_ms))
        return slice(s, e)

    def section_slice(self, start_ms: int, end_ms: int) -> dict[str, dict[str, np.ndarray]]:
        """Per-group {'brightness','lit','motion'} arrays restricted to [start_ms, end_ms)."""
        sl = self._frame_slice(start_ms, end_ms)
        return {g: {"brightness": self.brightness[g][sl], "lit": self.lit[g][sl],
                    "motion": self.motion[g][sl]} for g in self.groups}

    def frame_at(self, t_ms: int) -> int:
        return min(max(0, int(t_ms) // self.step_ms), max(0, self.frames - 1))
