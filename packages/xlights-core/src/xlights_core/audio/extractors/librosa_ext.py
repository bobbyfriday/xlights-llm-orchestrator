"""librosa complements (not a fallback): energy arc over time."""

from __future__ import annotations

from ..schema import EnergyPoint


def energy_arc(y, sr, *, max_points: int = 400) -> list[EnergyPoint]:
    """Overall RMS energy over time, downsampled to at most max_points."""
    import librosa
    import numpy as np

    rms = librosa.feature.rms(y=y)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
    if len(rms) > max_points:
        idx = np.linspace(0, len(rms) - 1, max_points).astype(int)
        rms, times = rms[idx], times[idx]
    return [EnergyPoint(time=float(t), rms=float(r)) for t, r in zip(times, rms)]
