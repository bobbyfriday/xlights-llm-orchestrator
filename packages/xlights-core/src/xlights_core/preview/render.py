"""Offline preview renderer — stills (PNG) and clips (MP4), no xLights.

World pixels → orthographic projection → pixel splat. Adapted from the proven
xlight-autosequencer/src/video/renderer.py (which rendered video); here a
`PreviewRenderer` precomputes the projection once and emits either a still frame
or a short silent clip at any timestamp.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from .fseq import load_fseq
from .layout import model_world_pixels, parse_controllers, parse_models

log = logging.getLogger(__name__)

_BG = (6, 6, 12)


class PreviewRenderer:
    """Load a show's render data + layout once; render stills/clips at any time."""

    def __init__(self, fseq_path: str | Path, rgbeffects_path: str | Path,
                 networks_path: str | Path) -> None:
        self.header, self.frames = load_fseq(fseq_path)
        controllers = parse_controllers(networks_path)
        models = parse_models(rgbeffects_path, controllers)
        worlds, chans = [], []
        for m in models:
            w = model_world_pixels(m)
            if w.shape[0] == 0:
                continue
            worlds.append(w)
            chans.append(m.start_channel + 3 * np.arange(m.n_pixels))
        if not worlds:
            raise ValueError("no placeable model pixels in layout")
        world = np.concatenate(worlds)
        ch = np.concatenate(chans).astype(np.int64)
        valid = ch + 2 < self.header.channels      # channel-data bound (canvas-independent)
        self.world = world[valid]
        self.ch = ch[valid]
        self.bmin = self.world.min(axis=0)
        self.bmax = self.world.max(axis=0)

    # -- projection (per canvas; cheap). 5% bbox padding so edge props don't clip. --
    def _project(self, canvas: tuple[int, int]):
        w_, h_ = canvas
        px = max(float(self.bmax[0] - self.bmin[0]), 1e-6) * 0.05
        py = max(float(self.bmax[1] - self.bmin[1]), 1e-6) * 0.05
        minx, maxx = self.bmin[0] - px, self.bmax[0] + px
        miny, maxy = self.bmin[1] - py, self.bmax[1] + py
        dx, dy = maxx - minx, maxy - miny
        sc = min(w_ / dx, h_ / dy)
        ox, oy = (w_ - sc * dx) / 2, (h_ - sc * dy) / 2
        sx = (ox + (self.world[:, 0] - minx) * sc).astype(np.int32)
        sy = (h_ - oy - (self.world[:, 1] - miny) * sc).astype(np.int32)
        inb = (sx >= 0) & (sx < w_) & (sy >= 0) & (sy < h_)
        return sx[inb], sy[inb], self.ch[inb], w_, h_

    def _frame_img(self, fi, sx, sy, ch, w_, h_) -> np.ndarray:
        img = np.empty((h_, w_, 3), dtype=np.uint8)
        img[:] = _BG
        row = self.frames[fi]
        for k in range(3):
            # maximum.at, not fancy-index assignment: several model pixels can land on
            # the same screen pixel, and an unbuffered scatter would let a dim pixel
            # written later overwrite a bright one.
            np.maximum.at(img[:, :, k], (sy, sx), row[ch + k])
        return img

    def _fi(self, t_ms: int) -> int:
        return min(max(0, t_ms // self.header.step_ms), self.header.frames - 1)

    # -- public --
    def render_frame(self, t_ms: int, canvas: tuple[int, int] = (1280, 720)) -> bytes:
        """A still PNG at `t_ms`."""
        from PIL import Image
        sx, sy, ch, w_, h_ = self._project(canvas)
        img = self._frame_img(self._fi(t_ms), sx, sy, ch, w_, h_)
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, format="PNG")
        return buf.getvalue()

    def render_clip(self, start_ms: int, end_ms: int,
                    canvas: tuple[int, int] = (640, 360), crf: int = 30) -> bytes | None:
        """A short silent MP4 over [start_ms, end_ms). Returns None if ffmpeg is absent."""
        if shutil.which("ffmpeg") is None:
            log.info("ffmpeg not found; skipping clip render")
            return None
        sx, sy, ch, w_, h_ = self._project(canvas)
        fps = max(1, round(1000 / self.header.step_ms))
        s, e = self._fi(start_ms), min(self.header.frames, max(self._fi(start_ms) + 1,
                                                               end_ms // self.header.step_ms))
        if e <= s:
            return None
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.close()
        try:
            cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                   "-s", f"{w_}x{h_}", "-r", str(fps), "-i", "pipe:0",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
                   "-pix_fmt", "yuv420p", tmp.name]
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                for fi in range(s, e):
                    p.stdin.write(self._frame_img(fi, sx, sy, ch, w_, h_).tobytes())
                p.stdin.close()
            except (BrokenPipeError, OSError) as exc:  # ffmpeg died mid-stream
                log.info("ffmpeg pipe failed; skipping clip render: %s", exc)
                p.wait()
                return None
            if p.wait() != 0:
                return None
            return Path(tmp.name).read_bytes()
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def brightest_frame_ms(self, start_ms: int, end_ms: int) -> int:
        """Timestamp of the most-lit frame in [start_ms, end_ms) — a representative still."""
        s = self._fi(start_ms)
        e = min(self.header.frames, max(s + 1, end_ms // self.header.step_ms))
        seg = self.frames[s:e][:, self.ch].astype(np.int32).sum(axis=1)
        return int((s + int(seg.argmax())) * self.header.step_ms)
