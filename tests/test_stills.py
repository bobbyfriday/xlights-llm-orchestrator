"""Tests for per-section preview stills (pipeline/stills.py) over the checked-in headless fixture
(`tests/fixtures/fj_headless`: 20 frames @ 50ms, dark first half / bright second half) and a
synthetic series for the coverage-peak timestamp."""

from __future__ import annotations

import io
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("zstandard")   # the renderer needs the [preview] extra (numpy/zstandard/pillow)
pytest.importorskip("PIL")
import numpy as np
import zstandard
from PIL import Image

from xlights_orchestrator.pipeline import stills
from xlights_core.preview.metrics import FseqSeries, group_channel_index

FIXTURE = Path(__file__).parent / "fixtures" / "fj_headless"


def _sec(start, end, label="", **kw):
    return SimpleNamespace(start_ms=start, end_ms=end, label=label, intensity=0.9, **kw)


def _lit_px(png: bytes) -> int:
    a = np.array(Image.open(io.BytesIO(png)))[:, :, :3]
    return int((a.max(axis=2) > 30).sum())


# -- rendering over the fixture ------------------------------------------------

def test_one_png_per_section_named_by_index_and_label(tmp_path):
    secs = [_sec(0, 500, "Intro Verse"), _sec(500, 1000, "Chorus 1 (big!)")]
    out = tmp_path / "stills"
    paths = stills.render_stills(FIXTURE / "show.fseq", FIXTURE, secs, out)
    assert [p.name for p in paths] == ["00-intro-verse.png", "01-chorus-1-big.png"]
    assert all(p.parent == out and p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for p in paths)
    assert sorted(p.name for p in out.iterdir()) == [p.name for p in paths]
    # midpoints: 250ms falls in the dark half, 750ms in the bright half
    assert _lit_px(paths[0].read_bytes()) < _lit_px(paths[1].read_bytes())


def test_unlabeled_section_falls_back_to_section(tmp_path):
    paths = stills.render_stills(FIXTURE / "show.fseq", FIXTURE,
                                 [SimpleNamespace(start_ms=0, end_ms=1000)], tmp_path)
    assert [p.name for p in paths] == ["00-section.png"]


def test_stale_stills_are_replaced(tmp_path):
    (tmp_path / "07-old-section.png").write_bytes(b"stale")
    (tmp_path / "notes.txt").write_text("keep me")
    paths = stills.render_stills(FIXTURE / "show.fseq", FIXTURE, [_sec(0, 1000, "All")], tmp_path)
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["00-all.png", "notes.txt"] and len(paths) == 1


def test_missing_fseq_returns_empty_and_writes_nothing(tmp_path):
    out = tmp_path / "stills"
    assert stills.render_stills(tmp_path / "nope.fseq", FIXTURE, [_sec(0, 500, "x")], out) == []
    assert not out.exists()


# -- when to picture a section --------------------------------------------------

def _write_fseq(path, channels, frames_data: bytes, n_frames, step_ms=50):
    comp = zstandard.ZstdCompressor().compress(frames_data)
    h = bytearray(40)
    h[0:4] = b"PSEQ"
    struct.pack_into("<H", h, 4, 40)
    h[6], h[7] = 2, 2
    struct.pack_into("<I", h, 10, channels)
    struct.pack_into("<I", h, 14, n_frames)
    h[18] = step_ms
    h[20] = 1
    h[21] = 1
    struct.pack_into("<I", h, 32, 0)
    struct.pack_into("<I", h, 36, len(comp))
    path.write_bytes(bytes(h) + comp)


def _series(tmp_path, rows):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "xlights_networks.xml").write_text(
        '<Networks><Controller Id="1" Name="C1" Protocol="E131">'
        '<network MaxChannels="6"/></Controller></Networks>')
    (tmp_path / "xlights_rgbeffects.xml").write_text(
        '<xrgb><models>'
        '<model name="A" DisplayAs="Single Line" StartChannel="!C1:1" parm1="1" parm2="1"/>'
        '<model name="B" DisplayAs="Single Line" StartChannel="!C1:4" parm1="1" parm2="1"/>'
        '</models><modelGroups>'
        '<modelGroup name="GA" models="A"/><modelGroup name="GB" models="B"/>'
        '</modelGroups></xrgb>')
    f = tmp_path / "s.fseq"
    _write_fseq(f, 6, bytes(v for r in rows for v in r), len(rows))
    return FseqSeries(f, group_channel_index(tmp_path / "xlights_rgbeffects.xml",
                                             tmp_path / "xlights_networks.xml"))


def test_still_time_midpoint_without_series():
    assert stills.still_time(_sec(0, 500)) == 250
    assert stills.still_times([_sec(0, 500), _sec(500, 1000)]) == [250, 750]


def test_still_time_is_the_coverage_peak_of_the_targeted_groups(tmp_path):
    # GA lit only at frame 7 (350ms); GB lit only at frame 2 (100ms); 20 frames @ 50ms
    rows = [[255, 255, 255, 0, 0, 0] if i == 7 else
            [0, 0, 0, 255, 255, 255] if i == 2 else [0, 0, 0, 0, 0, 0] for i in range(20)]
    s = _series(tmp_path, rows)
    assert stills.still_time(_sec(0, 500, target_groups=["GA"]), s) == 350
    assert stills.still_time(_sec(0, 500, target_groups=["GB"]), s) == 100
    # the section's targets aren't in the series → all groups → the first peak frame wins
    assert stills.still_time(_sec(0, 500, target_groups=["SEM_NOPE"]), s) == 100
    # an all-dark span still yields an in-range timestamp (the first frame of the span)
    assert stills.still_time(_sec(500, 1000, target_groups=["GA"]), s) == 500
    assert stills.still_times([_sec(0, 500, target_groups=["GA"])], s) == [350]


def test_render_stills_pictures_the_series_peak(tmp_path):
    # the series says section 0's GA peaks at frame 15 (750ms) — in the fixture's BRIGHT half —
    # while its midpoint (250ms) would land in the DARK half
    rows = [[255, 255, 255, 0, 0, 0] if i == 15 else [0, 0, 0, 0, 0, 0] for i in range(20)]
    s = _series(tmp_path / "series", rows)
    sec = _sec(0, 1000, "whole", target_groups=["GA"])
    out = tmp_path / "stills"
    at_peak = stills.render_stills(FIXTURE / "show.fseq", FIXTURE, [sec], out, series=s)
    at_mid = stills.render_stills(FIXTURE / "show.fseq", FIXTURE, [_sec(0, 500, "mid")],
                                  tmp_path / "mid")
    assert stills.still_time(sec, s) == 750
    assert _lit_px(at_peak[0].read_bytes()) > _lit_px(at_mid[0].read_bytes())
