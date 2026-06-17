"""Song-tail envelope: where the music's amplitude declines and where it goes silent.

Derived deterministically from the whole-track RMS `energy_arc` so the light show can stop and
fade *with* the music at the very end (a song that fades out gets a long fade; one that ends
abruptly gets a short one) instead of holding at full brightness through the trailing decay and
silence, then hard-cutting at the audio-file end.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

# Thresholds are RELATIVE to the track's robust peak, not absolute dB, so they travel across songs.
PEAK_PCTILE = 0.95        # "robust peak" = 95th-percentile RMS (ignores a lone transient spike)
SILENCE_FRAC = 0.08       # below this fraction of the robust peak the music is effectively silent
LOUD_FRAC = 0.5           # at/above this fraction it is "still loud" — the decline hasn't begun
MIN_TAIL_FADE_S = 0.5     # shortest song-end fade (an abrupt ending still eases off, never snaps)
MAX_TAIL_FADE_S = 6.0     # longest — a very gradual fade-out is bounded so earlier sections are untouched


def _percentile(vals: Sequence[float], q: float) -> float:
    s = sorted(vals)
    if not s:
        return 0.0
    idx = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[idx]


def song_tail_envelope(energy_arc: Any, duration_s: float) -> tuple[float, float]:
    """Return ``(fade_start_s, music_end_s)`` for the song's trailing decay.

    ``music_end_s`` is the music's last non-silent moment (≤ ``duration_s``); past it the lights
    should be dark. ``fade_start_s`` is the onset of the final amplitude decline, bounded to
    ``[music_end - MAX_TAIL_FADE_S, music_end - MIN_TAIL_FADE_S]`` — over this window the lights
    should fade out. With no usable envelope (or a track that never goes quiet) this degrades to a
    short fade at ``duration_s`` and no trim, never a regression to the old hard-cut.
    """
    dur = max(0.0, float(duration_s))
    pts = sorted((float(p.time), float(p.rms))
                 for p in (energy_arc or []) if float(p.time) <= dur + 1e-6)
    if len(pts) < 2:
        return max(0.0, dur - MIN_TAIL_FADE_S), dur

    peak = _percentile([r for _, r in pts], PEAK_PCTILE) or max((r for _, r in pts), default=0.0)
    if peak <= 0.0:
        return max(0.0, dur - MIN_TAIL_FADE_S), dur
    floor, loud = SILENCE_FRAC * peak, LOUD_FRAC * peak

    # music_end: the silence that BEGINS just after the last audible frame (else the file end).
    last_audible = max((i for i, (_, r) in enumerate(pts) if r > floor), default=None)
    if last_audible is None:
        return max(0.0, dur - MIN_TAIL_FADE_S), dur
    music_end = dur if last_audible >= len(pts) - 1 else pts[last_audible + 1][0]

    # fade length = how long since the music was last "still loud" before music_end (the decline's
    # span), bounded: a gradual fade-out yields a long fade, an abrupt ending the MIN floor.
    last_loud = max((t for t, r in pts if t < music_end and r >= loud), default=music_end - MAX_TAIL_FADE_S)
    fade_len = max(MIN_TAIL_FADE_S, min(MAX_TAIL_FADE_S, music_end - last_loud))
    return max(0.0, music_end - fade_len), music_end
