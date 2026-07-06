"""Tests for the offline preview renderer (xlights-core/preview)."""

from __future__ import annotations

import struct

import numpy as np
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
    h[20] = 1                                 # compression type: zstd (block-count high bits 0)
    h[21] = 1                                 # one compression block
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


def test_fseq_uncompressed(tmp_path):
    raw = bytes([10, 0, 0, 0, 20, 0,  0, 30, 0, 0, 0, 40])
    h = bytearray(40)
    h[0:4] = b"PSEQ"
    struct.pack_into("<H", h, 4, 40)
    h[6], h[7] = 0, 2
    struct.pack_into("<I", h, 10, 6)
    struct.pack_into("<I", h, 14, 2)
    h[18] = 50                                # bytes 20-21 stay 0: uncompressed, no blocks
    f = tmp_path / "u.fseq"
    f.write_bytes(bytes(h) + raw)
    _, frames = load_fseq(f)
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


# -- Tier 0 fseq metrics (I8) -------------------------------------------------

from xlights_core.preview.metrics import FseqSeries, group_channel_index  # noqa: E402


def _metrics_layout(tmp_path):
    """3 single-pixel models A,B,C on one controller (9 channels) + groups GA/GB/GC + nested GALL."""
    (tmp_path / "xlights_networks.xml").write_text(
        '<Networks><Controller Id="1" Name="C1" Protocol="E131">'
        '<network MaxChannels="9"/></Controller></Networks>')
    (tmp_path / "xlights_rgbeffects.xml").write_text(
        '<xrgb><models>'
        '<model name="A" DisplayAs="Single Line" StartChannel="!C1:1" parm1="1" parm2="1"/>'
        '<model name="B" DisplayAs="Single Line" StartChannel="!C1:4" parm1="1" parm2="1"/>'
        '<model name="C" DisplayAs="Single Line" StartChannel="!C1:7" parm1="1" parm2="1"/>'
        '</models>'
        '<modelGroups>'
        '<modelGroup name="GA" models="A"/>'
        '<modelGroup name="GB" models="B"/>'
        '<modelGroup name="GC" models="C"/>'
        '<modelGroup name="GALL" models="GA,GB"/>'          # nested: a group of groups
        '<modelGroup name="GEMPTY" models=""/>'             # empty → omitted
        '<modelGroup name="GGHOST" models="ghost_model"/>'  # unknown member → omitted
        '</modelGroups></xrgb>')


def _blink_fseq(tmp_path, n_frames=10):
    """A blinks white every other frame (100ms on a 50ms grid); B dim red; C dark. 9 channels."""
    rows = []
    for i in range(n_frames):
        a = 255 if i % 2 == 0 else 0
        rows += [a, a, a,        # A white/off
                 60, 0, 0,       # B constant dim red
                 0, 0, 0]        # C dark
    f = tmp_path / "m.fseq"
    _write_fseq(f, 9, bytes(rows), n_frames)
    return f


def test_group_channel_index_resolves_nested_and_omits_bad(tmp_path):
    _metrics_layout(tmp_path)
    idx = group_channel_index(tmp_path / "xlights_rgbeffects.xml", tmp_path / "xlights_networks.xml")
    assert set(idx) == {"GA", "GB", "GC", "GALL"}            # empty + unknown-member groups omitted
    assert list(idx["GA"]) == [0]                            # A's node channel start (0-based)
    assert list(idx["GB"]) == [3] and list(idx["GC"]) == [6]
    assert list(idx["GALL"]) == [0, 3]                       # nested union of GA + GB


def test_group_channel_index_filters_and_skips_unresolvable(tmp_path):
    # a model with an unresolvable StartChannel is skipped like parse_models
    (tmp_path / "xlights_networks.xml").write_text('<Networks></Networks>')
    (tmp_path / "xlights_rgbeffects.xml").write_text(
        '<xrgb><models>'
        '<model name="bad" DisplayAs="Single Line" StartChannel="!ghost:1" parm1="1" parm2="1"/>'
        '</models><modelGroups><modelGroup name="G" models="bad"/></modelGroups></xrgb>')
    idx = group_channel_index(tmp_path / "xlights_rgbeffects.xml", tmp_path / "xlights_networks.xml",
                              groups=["G", "not_a_group"])
    assert idx == {}                                         # unresolved member → dropped; unknown filtered


def test_fseq_series_motion_lit_brightness(tmp_path):
    _metrics_layout(tmp_path)
    f = _blink_fseq(tmp_path, n_frames=10)
    idx = group_channel_index(tmp_path / "xlights_rgbeffects.xml", tmp_path / "xlights_networks.xml")
    s = FseqSeries(f, idx)
    assert s.step_ms == 50 and s.frames == 10
    # motion: GA (blinking) ≫ GB (constant) ≈ 0; GC dark = 0
    assert s.motion["GA"].mean() > 100 and s.motion["GB"].mean() < 1e-6
    assert s.motion["GC"].mean() == 0.0
    # lit fraction (>30): GA lit half the frames; GB dim red 60>30 lit always; GC never
    assert abs(s.lit["GA"].mean() - 0.5) < 0.06
    assert s.lit["GB"].mean() == 1.0 and s.lit["GC"].mean() == 0.0
    # brightness proxy = max(R,G,B): GB constant 60
    assert np.allclose(s.brightness["GB"], 60.0)


def test_fseq_series_section_slice(tmp_path):
    _metrics_layout(tmp_path)
    f = _blink_fseq(tmp_path, n_frames=10)
    idx = group_channel_index(tmp_path / "xlights_rgbeffects.xml", tmp_path / "xlights_networks.xml")
    s = FseqSeries(f, idx)
    sec = s.section_slice(0, 200)          # frames 0..3 (50ms step)
    assert sec["GA"]["lit"].shape[0] == 4
    assert set(sec) == {"GA", "GB", "GC", "GALL"}
