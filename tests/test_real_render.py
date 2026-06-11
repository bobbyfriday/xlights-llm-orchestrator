"""Tests for real-render feedback (export guard, offset, frame sampling, fallbacks)."""
import asyncio
import subprocess
from types import SimpleNamespace

import pytest

from xlights_orchestrator.pipeline import visual as V
from xlights_orchestrator.pipeline.visual import RealRender


def run(c):
    return asyncio.run(c)


class _Client:
    def __init__(self, media="/x.mp3", export_ok=True):
        self.media = media
        self.exported = []
        self.export_ok = export_ok

    async def get_open_sequence(self):
        return {"seq": "s", "media": self.media}

    async def export_video_preview(self, filename):
        self.exported.append(filename)
        return filename if self.export_ok else None


def test_guard_never_exports_media_less():
    rr = RealRender("show", 10.0)
    c = _Client(media="")
    assert run(rr.refresh(c)) is False
    assert c.exported == []                                  # the crash precondition is forbidden


def _make_clip(path, color, secs=2):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"color=c={color}:s=64x48:d={secs}", str(path)], check=True)


def test_refresh_offset_and_frames(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "_SANDBOX", tmp_path)             # sandbox → tmp
    (tmp_path / "show.xsq").write_text("<x/>")
    _make_clip(tmp_path / "show_review.mp4", "white", secs=3)  # video 3s vs song 2s → 1s lead-in
    rr = RealRender("show", 2.0)
    c = _Client()
    assert run(rr.refresh(c)) is True and c.exported == ["show_review.mp4"]
    assert 800 <= rr.offset_ms <= 1300                       # measured lead-in ≈ 1s
    png = rr.frame_png(500)                                  # song-time 0.5s → video 1.5s
    import io
    import numpy as np
    from PIL import Image
    a = np.array(Image.open(io.BytesIO(png)))[:, :, :3]
    assert (a.max(axis=2) > 30).sum() > 1000                 # white clip → lit
    # cached: second refresh with unchanged xsq does NOT re-export
    assert run(rr.refresh(c)) is True and len(c.exported) == 1


def test_sampler_prefers_real(tmp_path):
    _make_clip(tmp_path / "v.mp4", "black")
    rr = RealRender("show", 2.0)
    rr.path, rr.offset_ms = tmp_path / "v.mp4", 0
    sampler = V.make_lit_sampler(save_as="show", show_folder=None, real=rr)
    assert sampler(500) == 0                                 # black real frame → 0 lit (no fallback raise)
