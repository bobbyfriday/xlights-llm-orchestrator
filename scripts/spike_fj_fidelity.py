"""F-J spike (S1 fidelity + S3 CLI-render diff) — a decision tool, NOT a shipped feature.

This script measures "what truly requires live xLights?" It has two halves:

* **Pure helpers** (mask projection, per-frame delta metrics, ``.fseq`` byte/channel diff) — imported
  and unit-tested hermetically by ``tests/test_headless_fixture.py``. These carry no live dependency.
* **Live harness** (``run_s1_fidelity``, ``run_s3_cli_render``) — gated behind ``XLO_LIVE=1`` and a
  running xLights with the fixture open. NEVER runs in CI. These emit ``fidelity_report.json`` and the
  ``.fseq`` diff the decision table keys off.

Run: ``XLO_LIVE=1 uv run python scripts/spike_fj_fidelity.py --fixture <dir>``. The go/no-go analysis
lives in ``openspec/changes/add-pipeline-operability/design.md`` (`## Notes` → F-J) and the write-up
in ``docs/roadmap-2026-07/F-J-spike.md``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np


# -- pure helpers (hermetically unit-tested) ----------------------------------

def project_group_mask(pixel_xy: np.ndarray, canvas: tuple[int, int],
                       extent: tuple[float, float, float, float] | None = None) -> np.ndarray:
    """Project a group's member-model world pixels (``[N, 2]`` x/y) onto a boolean canvas mask.

    Mirrors the offline renderer's ``_project`` normalization: fit the world extent to the canvas,
    flip Y (world up → image down), and mark each projected pixel. Used to compute per-group
    brightness/lit-fraction agreement between the offline and real renders.
    """
    w, h = canvas
    mask = np.zeros((h, w), dtype=bool)
    if pixel_xy.size == 0:
        return mask
    xs, ys = pixel_xy[:, 0].astype(float), pixel_xy[:, 1].astype(float)
    if extent is None:
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    else:
        x0, x1, y0, y1 = extent
    sx = (w - 1) / (x1 - x0) if x1 > x0 else 0.0
    sy = (h - 1) / (y1 - y0) if y1 > y0 else 0.0
    px = np.clip(((xs - x0) * sx).round().astype(int), 0, w - 1)
    py = np.clip((h - 1 - (ys - y0) * sy).round().astype(int), 0, h - 1)   # flip Y
    mask[py, px] = True
    return mask


def frame_deltas(offline: np.ndarray, real: np.ndarray, *, lit_threshold: int = 30) -> dict:
    """Per-frame agreement metrics between two RGB frames (``[H, W, 3]`` uint8).

    Returns ``{brightness_delta, lit_fraction_offline, lit_fraction_real,
    lit_fraction_agreement, hue_distance}``. ``lit_fraction_agreement`` is the fraction of pixels
    where the two renders agree on lit-vs-dark at the sampler's ``>lit_threshold`` cutoff — the
    metric the decision table cares about (keep/revert outcomes track lit-fraction, not pixel
    equality).
    """
    off = offline[:, :, :3].astype(np.int16)
    rl = real[:, :, :3].astype(np.int16)
    off_v = off.max(axis=2)
    rl_v = rl.max(axis=2)
    lit_off = off_v > lit_threshold
    lit_rl = rl_v > lit_threshold
    return {
        "brightness_delta": float(np.abs(off_v - rl_v).mean()),
        "lit_fraction_offline": float(lit_off.mean()),
        "lit_fraction_real": float(lit_rl.mean()),
        "lit_fraction_agreement": float((lit_off == lit_rl).mean()),
        "hue_distance": _hue_hist_distance(off, rl),
    }


def _hue_hist_distance(a: np.ndarray, b: np.ndarray, bins: int = 12) -> float:
    """L1 distance between the two frames' coarse hue histograms (lit pixels only)."""
    def hue_hist(x):
        r, g, bl = x[:, :, 0].ravel(), x[:, :, 1].ravel(), x[:, :, 2].ravel()
        mx = np.maximum(np.maximum(r, g), bl)
        lit = mx > 30
        if not lit.any():
            return np.zeros(bins)
        # cheap hue proxy: argmax channel + secondary — 3-way bucket scaled to `bins`
        chan = np.stack([r, g, bl], axis=1)[lit]
        dom = chan.argmax(axis=1)
        hist = np.bincount(dom, minlength=3).astype(float)
        hist = hist / hist.sum()
        return np.repeat(hist, bins // 3)[:bins]
    ha, hb = hue_hist(a), hue_hist(b)
    return float(np.abs(ha - hb).sum())


def fseq_channel_diff(a: np.ndarray, b: np.ndarray) -> dict:
    """Byte/channel-for-channel diff between two decoded ``.fseq`` arrays (``[frames, channels]``).

    S3's hard gate: option (a) (file-based emitter + CLI render) requires the CLI-produced ``.fseq``
    to match the REST render to ≤1 LSB per channel. Returns ``{max_abs, mean_abs, over_1lsb,
    identical, shape_a, shape_b}``.
    """
    if a.shape != b.shape:
        return {"identical": False, "shape_mismatch": True,
                "shape_a": list(a.shape), "shape_b": list(b.shape),
                "max_abs": None, "mean_abs": None, "over_1lsb": None}
    d = np.abs(a.astype(np.int16) - b.astype(np.int16))
    return {
        "identical": bool((d == 0).all()),
        "shape_mismatch": False,
        "shape_a": list(a.shape), "shape_b": list(b.shape),
        "max_abs": int(d.max()),
        "mean_abs": float(d.mean()),
        "over_1lsb": int((d > 1).sum()),
    }


# -- live harness (XLO_LIVE-gated; never in CI) -------------------------------

def _require_live() -> None:
    if os.environ.get("XLO_LIVE") != "1":
        raise SystemExit("live S1/S3 steps require XLO_LIVE=1 and a running xLights (never in CI).")


def run_s1_fidelity(fixture: Path, *, samples: int = 8) -> dict:  # pragma: no cover — live only
    """S1: measure the offline-vs-real fidelity gap on the fixture, emit fidelity_report.json.

    Requires a live xLights with the fixture open (RealRender export path). Per section, sample N
    beat-aligned timestamps, render each both ways, compute per-frame ``frame_deltas``. This is a
    STUB skeleton — the live probes are documented but gated; wire them when running the spike.
    """
    _require_live()
    raise NotImplementedError(
        "S1 live probe: open the fixture in xLights, export the house preview via RealRender, "
        "render each sampled timestamp offline (PreviewRenderer) + real (RealRender.frame_png), "
        "call frame_deltas() per group mask (project_group_mask), and write fidelity_report.json.")


def run_s3_cli_render(fixture: Path) -> dict:  # pragma: no cover — live only
    """S3: prototype xLights batch/CLI render (macOS, then Linux/Xvfb); diff the produced .fseq
    channel-for-channel against the REST render via fseq_channel_diff. Gated behind XLO_LIVE."""
    _require_live()
    raise NotImplementedError(
        "S3 live probe: discover the xLights CLI flags, render the fixture's .xsq headless, "
        "load_fseq() both outputs, and gate option (a) on fseq_channel_diff(...)['over_1lsb'] == 0.")


def main(argv=None) -> None:  # pragma: no cover — CLI entry
    ap = argparse.ArgumentParser(description="F-J fidelity/CLI-render spike (XLO_LIVE-gated)")
    ap.add_argument("--fixture", type=Path, default=Path("tests/fixtures/fj_headless"))
    ap.add_argument("--step", choices=["s1", "s3"], required=True)
    args = ap.parse_args(argv)
    report = run_s1_fidelity(args.fixture) if args.step == "s1" else run_s3_cli_render(args.fixture)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":  # pragma: no cover
    main()
