"""F-J durable artifact: the checked-in fixture .fseq + layout, run through the coverage sampler
and Tier-0-style metrics WITHOUT a live xLights — the seed of the CI full-pipeline eval suite.

Also unit-tests the spike script's pure helpers (mask projection, delta metrics, .fseq diff)
against tiny synthetic inputs, so the fidelity/CLI-render logic is verified hermetically even
though the live S1/S3 probes are XLO_LIVE-gated and never run in CI.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "fj_headless"

# make the spike script importable (scripts/ isn't a package)
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


# -- the fixture runs the offline stack + coverage QA (no live xLights) --------

def _lit_sampler_over_fixture():
    from PIL import Image
    from xlights_core.preview import PreviewRenderer
    r = PreviewRenderer(FIXTURE / "show.fseq", FIXTURE / "xlights_rgbeffects.xml",
                        FIXTURE / "xlights_networks.xml")

    def sampler(t_ms: int) -> int:
        png = r.render_frame(int(t_ms), canvas=(64, 64))
        a = np.array(Image.open(io.BytesIO(png)))[:, :, :3]
        return int((a.max(axis=2) > 30).sum())

    return sampler


def test_fixture_loads_and_has_dark_and_bright_halves():
    from xlights_core.preview import load_fseq
    header, frames = load_fseq(FIXTURE / "show.fseq")
    assert header.channels == 36 and header.frames == 20 and header.step_ms == 50
    assert int(frames[0].max()) <= 40                # first half DARK
    assert int(frames[-1].max()) == 255              # second half BRIGHT


def test_coverage_sampler_flags_dark_high_energy_section():
    """The coverage QA over the fixture flags the DARK high-energy section and passes the BRIGHT
    one — the exact objective the sampler seeds for CI (no live app needed)."""
    from xlights_orchestrator.qa import coverage
    sampler = _lit_sampler_over_fixture()
    # a high-energy DARK first section (0–500ms) + a high-energy BRIGHT second (500–1000ms)
    plan = SimpleNamespace(sections=[
        SimpleNamespace(start_ms=0, end_ms=500, intensity=0.9),      # loud but dark
        SimpleNamespace(start_ms=500, end_ms=1000, intensity=0.9),   # loud and lit
    ])
    score, findings = coverage.evaluate(plan, sampler)
    assert 0 <= score <= 100
    # the dark loud section is flagged; the lit one is not
    flagged = {f.section_index for f in findings}
    assert 0 in flagged and 1 not in flagged


def test_tier0_lit_fraction_over_fixture():
    """Tier-0-style deterministic metric: peak-normalized lit fraction per section, over the
    fixture. The bright section reaches full lit; the dark one is near-zero."""
    sampler = _lit_sampler_over_fixture()
    dark = max(sampler(t) for t in (50, 150, 250))          # first-half samples
    bright = max(sampler(t) for t in (600, 750, 900))       # second-half samples
    assert bright >= 12 and dark <= 2
    assert bright / max(1, bright) == 1.0 and dark / bright < 0.2   # clear separation


# -- pure-helper unit tests for the spike script ------------------------------

def test_project_group_mask_marks_pixels():
    import spike_fj_fidelity as S
    pts = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.0]])
    mask = S.project_group_mask(pts, canvas=(16, 16))
    assert mask.dtype == bool and mask.shape == (16, 16)
    assert mask.sum() >= 1                               # at least one projected pixel
    assert S.project_group_mask(np.empty((0, 2)), canvas=(16, 16)).sum() == 0


def test_frame_deltas_identical_and_divergent():
    import spike_fj_fidelity as S
    a = np.zeros((8, 8, 3), dtype=np.uint8); a[:, :, 0] = 200
    same = S.frame_deltas(a, a)
    assert same["brightness_delta"] == 0.0 and same["lit_fraction_agreement"] == 1.0
    b = np.zeros((8, 8, 3), dtype=np.uint8)              # all dark
    diff = S.frame_deltas(a, b)
    assert diff["brightness_delta"] > 0 and diff["lit_fraction_agreement"] < 1.0


def test_fseq_channel_diff_identical_and_over_1lsb():
    import spike_fj_fidelity as S
    a = np.zeros((4, 6), dtype=np.uint8); a[0, 0] = 100
    assert S.fseq_channel_diff(a, a)["identical"] is True
    b = a.copy(); b[0, 0] = 101                          # 1 LSB off
    d1 = S.fseq_channel_diff(a, b)
    assert d1["identical"] is False and d1["max_abs"] == 1 and d1["over_1lsb"] == 0
    c = a.copy(); c[0, 0] = 150                          # >1 LSB
    d2 = S.fseq_channel_diff(a, c)
    assert d2["over_1lsb"] == 1
    # shape mismatch is handled, not crashed
    dm = S.fseq_channel_diff(a, np.zeros((4, 5), dtype=np.uint8))
    assert dm["shape_mismatch"] is True and dm["identical"] is False


def test_fseq_diff_over_real_fixture_is_self_identical():
    """Loading the checked-in fixture .fseq and diffing it against itself is byte-identical — the
    S3 diff plumbing works over a real file, not just synthetic arrays."""
    import spike_fj_fidelity as S
    from xlights_core.preview import load_fseq
    _, frames = load_fseq(FIXTURE / "show.fseq")
    assert S.fseq_channel_diff(frames, frames.copy())["identical"] is True


def test_live_probes_are_gated(monkeypatch):
    """The live S1/S3 probes refuse to run without XLO_LIVE=1 (never in CI)."""
    import spike_fj_fidelity as S
    monkeypatch.delenv("XLO_LIVE", raising=False)
    with pytest.raises(SystemExit):
        S.run_s1_fidelity(FIXTURE)
    with pytest.raises(SystemExit):
        S.run_s3_cli_render(FIXTURE)


def test_fixture_fseq_is_small():
    """Guard against repo bloat — the CI fixture .fseq stays tiny (zstd, low channels/frames)."""
    assert (FIXTURE / "show.fseq").stat().st_size < 4096
