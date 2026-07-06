"""F-E slice 5 — offline §7 validation (deterministic-first)."""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")   # validation needs the [preview] extra (numpy/pillow/zstandard)

from xlights_core.preview.fseq import load_fseq  # noqa: E402
from xlights_core.preview.layout import parse_controllers, parse_models  # noqa: E402
from xlights_orchestrator.pipeline.layout_validate import (  # noqa: E402
    check_sweep,
    role_color_frames,
    structural_checks,
    sweep_frames,
    write_fseq_v2_uncompressed,
)


def _sweep_layout(tmp_path, *, negate_x=False):
    """3 arches left→right (or right→left if negate_x) each 2 pixels, on one controller."""
    (tmp_path / "xlights_networks.xml").write_text(
        '<Networks><Controller Id="1" Name="C1" Protocol="E131">'
        '<network MaxChannels="200"/></Controller></Networks>')
    xs = [30, 18, 6] if negate_x else [6, 18, 30]
    models = "".join(
        f'<model name="Arch{i}" DisplayAs="Single Line" StartChannel="!C1:{1 + i * 6}" '
        f'parm1="1" parm2="2" ScaleX="1" ScaleY="1" WorldPosX="{x}" WorldPosY="0" '
        f'LayoutGroup="Default"/>'
        for i, x in enumerate(xs))
    rgb = tmp_path / "xlights_rgbeffects.xml"
    rgb.write_text(f'<xrgb><models>{models}</models><modelGroups/></xrgb>')
    return rgb


def _renderer(tmp_path, rgb, frames):
    from xlights_core.preview.render import PreviewRenderer
    fseq = tmp_path / "s.fseq"
    write_fseq_v2_uncompressed(fseq, frames)
    return PreviewRenderer(fseq, rgb, tmp_path / "xlights_networks.xml")


# -- FSEQ writer round-trip ---------------------------------------------------------------------
def test_fseq_uncompressed_roundtrip(tmp_path):
    frames = np.array([[10, 0, 0, 0, 20, 0], [0, 30, 0, 0, 0, 40]], dtype=np.uint8)
    f = tmp_path / "x.fseq"
    write_fseq_v2_uncompressed(f, frames, frame_ms=50)
    header, back = load_fseq(f)
    assert header.channels == 6 and header.frames == 2 and header.step_ms == 50
    assert np.array_equal(back, frames)


# -- sweep centroid check -----------------------------------------------------------------------
def test_sweep_passes_left_to_right(tmp_path):
    rgb = _sweep_layout(tmp_path)
    ctl = parse_controllers(tmp_path / "xlights_networks.xml")
    models = parse_models(rgb, ctl)
    frames, members = sweep_frames(["Arch0", "Arch1", "Arch2"], models)
    r = _renderer(tmp_path, rgb, frames)
    result = check_sweep(frames, r)
    assert result.ok and not result.recommend_invert
    assert result.centroids == sorted(result.centroids)   # strictly increasing


def test_sweep_fails_and_recommends_invert_when_x_negated(tmp_path):
    rgb = _sweep_layout(tmp_path, negate_x=True)
    ctl = parse_controllers(tmp_path / "xlights_networks.xml")
    models = parse_models(rgb, ctl)
    # member order Arch0..Arch2 but their world-x now descends → centroid decreases
    frames, _ = sweep_frames(["Arch0", "Arch1", "Arch2"], models)
    r = _renderer(tmp_path, rgb, frames)
    result = check_sweep(frames, r)
    assert not result.ok and result.recommend_invert
    assert "invert-x" in result.detail


# -- role-color frames --------------------------------------------------------------------------
def test_role_color_frames_light_only_member_channels(tmp_path):
    rgb = _sweep_layout(tmp_path)
    ctl = parse_controllers(tmp_path / "xlights_networks.xml")
    models = parse_models(rgb, ctl)
    from types import SimpleNamespace
    manifest = SimpleNamespace(props=[
        SimpleNamespace(id="Arch0", role="ARCH"),
        SimpleNamespace(id="Arch1", role="ARCH"),
        SimpleNamespace(id="Arch2", role="ARCH"),
    ])
    frames, labels = role_color_frames(manifest, models)
    assert labels == ["ARCH"]
    # ARCH color is red (255,0,0) → the R channels are lit, G/B dark
    lit = frames[0]
    assert lit[0] == 255 and lit[1] == 0     # Arch0 pixel0 R lit, G dark


# -- structural checks --------------------------------------------------------------------------
def test_structural_checks_pass_and_catch_violations():
    from types import SimpleNamespace

    def _p(name, role, order=None):
        return SimpleNamespace(id=name, role=role, sweep_order=order)

    def _g(members):
        return SimpleNamespace(members=members)

    manifest = SimpleNamespace(
        props=[_p("A", "ARCH", 1), _p("B", "ARCH", 2), _p("F", "SINGING_FACE")],
        groups={"SEM_ARCHES": _g(["A", "B"]), "SEM_ARCHES_LTR": _g(["A", "B"]),
                "SEM_ALL": _g(["A", "B"])})
    assert structural_checks(manifest, {"A", "B", "F"}) == []

    # missing model, empty group, SEM_ALL includes a face, LTR order wrong
    bad = SimpleNamespace(
        props=[_p("A", "ARCH", 2), _p("B", "ARCH", 1), _p("F", "SINGING_FACE")],
        groups={"SEM_ARCHES_LTR": _g(["A", "B"]), "SEM_ALL": _g(["A", "B", "F"]),
                "SEM_EMPTY": _g([]), "SEM_X": _g(["ghost"])})
    problems = structural_checks(bad, {"A", "B", "F"})
    joined = " ".join(problems)
    assert "empty" in joined and "missing model" in joined
    assert "SEM_ALL includes" in joined and "sweep_order" in joined


# -- contact sheet ------------------------------------------------------------------------------
def test_contact_sheet_renders(tmp_path):
    pytest.importorskip("PIL")
    rgb = _sweep_layout(tmp_path)
    ctl = parse_controllers(tmp_path / "xlights_networks.xml")
    models = parse_models(rgb, ctl)
    from types import SimpleNamespace
    manifest = SimpleNamespace(props=[SimpleNamespace(id="Arch0", role="ARCH"),
                                      SimpleNamespace(id="Arch1", role="ARCH")])
    frames, labels = role_color_frames(manifest, models)
    r = _renderer(tmp_path, rgb, frames)
    from xlights_orchestrator.pipeline.layout_validate import role_color_sheet
    out = role_color_sheet(r, frames, labels, tmp_path / "sheet.png")
    assert out.exists() and out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
