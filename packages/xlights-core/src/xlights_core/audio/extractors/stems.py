"""Optional stem separation (demucs) + per-stem features + per-section prevalence.

Backend is pluggable and resolved at call time: demucs-mlx (Apple-Silicon, no torch)
first, PyTorch demucs as fallback. All of it is optional and graceful — any failure
returns None and the analysis proceeds on the full mix.
"""

from __future__ import annotations

import logging
import os

from ..schema import EnergyPoint, SectionInstrumentation, Segment, StemFeatures

log = logging.getLogger(__name__)

STEM_NAMES = ("vocals", "drums", "bass", "other")
DEFAULT_MODEL = "htdemucs_6s"             # 6-stem: + guitar, piano (configurable via XLO_STEMS_MODEL)
SIX_STEM = {"guitar", "piano"}            # the extra stems a 6-stem model must yield


def stems_model() -> str:
    return os.environ.get("XLO_STEMS_MODEL", DEFAULT_MODEL)


# -- separation (backend-pluggable, graceful) ---------------------------------

def separate(path: str, sample_rate: int):
    """Separate `path` into {name: mono float32 ndarray @ sample_rate}, or None.

    Tries demucs-mlx, then PyTorch demucs; honors XLO_STEMS_BACKEND in {mlx,torch}.
    Any missing dependency / failure → None (logged), never raises.
    """
    backend = os.environ.get("XLO_STEMS_BACKEND")
    order = [backend] if backend else ["mlx", "torch"]
    for name in order:
        try:
            if name == "mlx":
                raw = _separate_mlx(path)
            elif name == "torch":
                raw = _separate_torch(path)
            else:
                continue
        except ImportError:
            continue  # backend not installed; try the next
        except Exception as exc:  # noqa: BLE001 — separation is best-effort
            log.warning("stem separation backend %s failed: %s", name, exc)
            continue
        if raw:
            return _normalize(raw, sample_rate)
    log.info("no stem-separation backend available; continuing without stems")
    return None


def _separate_mlx(path: str):
    from demucs_mlx import Separator  # type: ignore

    _, stems = Separator(model=stems_model()).separate_audio_file(path)
    return _to_named(stems)


def _separate_torch(path: str):
    from demucs.api import Separator  # type: ignore

    device = _torch_device()
    _, stems = Separator(model=stems_model(), device=device).separate_audio_file(path)
    return _to_named(stems)


def _torch_device() -> str:
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


def _to_named(stems) -> dict:
    """Coerce a backend's stem container to {name: array-like}. Keys by name, not order."""
    if isinstance(stems, dict):
        return {str(k).lower(): v for k, v in stems.items()}
    # positional sequence → demucs source order, by length (6-stem adds guitar, piano)
    src_order = (("drums", "bass", "other", "vocals", "guitar", "piano")
                 if len(stems) >= 6 else ("drums", "bass", "other", "vocals"))
    return {src_order[i]: s for i, s in enumerate(stems)}


def _normalize(raw: dict, sample_rate: int) -> dict:
    """Each stem → mono float32 numpy @ sample_rate. (Backends vary in dtype/rate.)"""
    import numpy as np

    out: dict = {}
    for name, arr in raw.items():
        a = np.asarray(arr, dtype=np.float32)
        if a.ndim > 1:  # (channels, samples) or (samples, channels) → mono
            ch_axis = 0 if a.shape[0] <= a.shape[-1] else -1
            a = a.mean(axis=ch_axis)
        a = np.ascontiguousarray(a.reshape(-1).astype(np.float32))
        out[name] = a
    return out


# -- per-stem features --------------------------------------------------------

def stem_features(stems: dict, sr: int, *, max_points: int = 400) -> list[StemFeatures]:
    """RMS energy arc + onsets per stem."""
    import librosa
    import numpy as np

    feats: list[StemFeatures] = []
    for name in stems:                           # iterate ACTUAL stems (4-, 6-, any-stem)
        y = stems.get(name)
        if y is None:
            continue
        rms = librosa.feature.rms(y=y)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        if len(rms) > max_points:
            idx = np.linspace(0, len(rms) - 1, max_points).astype(int)
            rms, times = rms[idx], times[idx]
        arc = [EnergyPoint(time=float(t), rms=float(r)) for t, r in zip(times, rms)]
        onsets = [float(t) for t in librosa.onset.onset_detect(y=y, sr=sr, units="time")]
        feats.append(StemFeatures(stem=name, energy_arc=arc, onsets=onsets))
    return feats


# -- per-section instrument prevalence (pure, testable) -----------------------

def section_instrumentation(
    stems: dict, sr: int, segments: list[Segment], *, eps: float = 1e-9
) -> list[SectionInstrumentation]:
    """Per-segment: each stem's energy share + dominant instrument(s).

    Pure over raw mono signals — silent windows yield empty shares (no div-by-zero);
    no segments yields []."""
    import numpy as np

    out: list[SectionInstrumentation] = []
    for seg in segments:
        s = max(0, int(seg.start * sr))
        e = int(seg.end * sr)
        energies: dict[str, float] = {}
        for name in stems:                       # iterate ACTUAL stems (4-, 6-, any-stem)
            y = stems.get(name)
            if y is None:
                continue
            window = y[s:e]
            energies[name] = float(np.sqrt(np.mean(np.square(window)))) if len(window) else 0.0
        total = sum(energies.values())
        if total <= eps:  # silent / no energy → don't normalize
            out.append(SectionInstrumentation(
                segment_id=seg.segment_id, start_ms=int(seg.start * 1000),
                end_ms=int(seg.end * 1000), shares={}, dominant=[]))
            continue
        shares = {k: v / total for k, v in energies.items()}
        top = max(shares.values())
        dominant = [k for k, v in shares.items() if top - v <= 0.05]  # near-ties
        out.append(SectionInstrumentation(
            segment_id=seg.segment_id, start_ms=int(seg.start * 1000),
            end_ms=int(seg.end * 1000), shares=shares, dominant=dominant))
    return out
