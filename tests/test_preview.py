"""Tests for the offline preview renderer (xlights-core/preview)."""

from __future__ import annotations

import struct

import numpy as np
import pytest
import zstandard

from xlights_core.preview import (
    Controller,
    PreviewRenderer,
    load_fseq,
    model_world_pixels,
    parse_models,
)
from xlights_core.preview.layout import Model, parse_controllers, resolve_start_channel


def _write_fseq(path, channels, frames_data: bytes, n_frames, step_ms=50):
    comp = zstandard.ZstdCompressor().compress(frames_data)
    h = bytearray(40)
    h[0:4] = b"PSEQ"
    struct.pack_into("<H", h, 4, 40)          # data_offset
    h[6], h[7] = 2, 2                          # minor, major
    struct.pack_into("<I", h, 10, channels)
    struct.pack_into("<I", h, 14, n_frames)
    h[18] = step_ms
    struct.pack_into("<I", h, 32, 0)          # block first-frame
    struct.pack_into("<I", h, 36, len(comp))  # block byte length
    path.write_bytes(bytes(h) + comp)


def test_fseq_roundtrip(tmp_path):
    # 2 frames, 6 channels (2 RGB pixels)
    raw = bytes([10, 0, 0, 0, 20, 0,  0, 30, 0, 0, 0, 40])
    f = tmp_path / "x.fseq"
    _write_fseq(f, 6, raw, 2)
    header, frames = load_fseq(f)
    assert header.channels == 6 and header.frames == 2 and header.step_ms == 50
    assert frames.shape == (2, 6)
    assert frames[0, 0] == 10 and frames[1, 1] == 30 and frames[1, 5] == 40


def test_resolve_start_channel():
    ctl = {"C1": Controller("C1", start=0, length=6), "C2": Controller("C2", start=6, length=9)}
    assert resolve_start_channel("!C1:1", ctl) == 0
    assert resolve_start_channel("!C2:4", ctl) == 9      # 6 + 4 - 1
    assert resolve_start_channel("13", ctl) == 12        # plain int, 1-based
    assert resolve_start_channel("!nope:1", ctl) is None


def test_matrix_geometry_extent():
    # Vert Matrix, 1 string x 6 pixels, scale 1 → 6 pixels in a 1x6 column
    m = Model(name="VM", display_as="Vert Matrix", start_channel=0, n_pixels=6,
              parm1=1, parm2=6, parm3=1, world_x=0, world_y=0, world_z=0,
              scale_x=1, scale_y=1, scale_z=1, rotate_x=0, rotate_y=0, rotate_z=0)
    pts = model_world_pixels(m)
    assert pts.shape == (6, 3)
    assert np.ptp(pts[:, 1]) > 0          # spans vertically


def _minimal_layout(tmp_path):
    (tmp_path / "xlights_networks.xml").write_text(
        '<Networks><Controller Id="1" Name="C1" Protocol="E131">'
        '<network MaxChannels="6"/></Controller></Networks>')
    (tmp_path / "xlights_rgbeffects.xml").write_text(
        '<xrgb><models><model name="M1" DisplayAs="Single Line" StartChannel="!C1:1" '
        'parm1="2" parm2="1" WorldPosX="0" WorldPosY="0" WorldPosZ="0" '
        'ScaleX="1" ScaleY="1" ScaleZ="1"/></models></xrgb>')


def test_parse_models_placed(tmp_path):
    _minimal_layout(tmp_path)
    ctl = parse_controllers(tmp_path / "xlights_networks.xml")
    models = parse_models(tmp_path / "xlights_rgbeffects.xml", ctl)
    assert len(models) == 1 and models[0].n_pixels == 2 and models[0].start_channel == 0


def test_parse_models_skips_unresolved(tmp_path, caplog):
    (tmp_path / "xlights_networks.xml").write_text('<Networks></Networks>')
    (tmp_path / "xlights_rgbeffects.xml").write_text(
        '<xrgb><models><model name="bad" DisplayAs="Single Line" StartChannel="!ghost:1" '
        'parm1="2" parm2="1"/></models></xrgb>')
    ctl = parse_controllers(tmp_path / "xlights_networks.xml")
    import logging
    with caplog.at_level(logging.INFO):
        models = parse_models(tmp_path / "xlights_rgbeffects.xml", ctl)
    assert models == []
    assert "skipped 1" in caplog.text   # surfaced, not silent


def test_render_frame_and_clip(tmp_path):
    _minimal_layout(tmp_path)
    raw = bytes([200, 0, 0, 0, 0, 150])     # 1 frame: pixel0 red, pixel1 blue
    f = tmp_path / "s.fseq"
    _write_fseq(f, 6, raw, 1)
    r = PreviewRenderer(f, tmp_path / "xlights_rgbeffects.xml", tmp_path / "xlights_networks.xml")
    png = r.render_frame(0, canvas=(64, 64))
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 100
    img = np.array(__import__("PIL.Image", fromlist=["Image"]).open(__import__("io").BytesIO(png)))
    assert (img.max(axis=2) > 20).sum() >= 2     # at least the 2 lit pixels above background
    clip = r.render_clip(0, 1000, canvas=(64, 64))
    assert clip is None or (clip[:4] and len(clip) > 100)   # MP4 bytes, or None if no ffmpeg
