"""Re-check the bar tracker's downbeats against the music's own accents.

The VAMP bar tracker (qm-barbeattracker) fixes ONE bar phase for the whole song and counts
1-2-3-4 to the end. A song with an odd bar (a 2/4 turnaround, a dropped beat) leaves every bar
after it labelled a beat early or late — Hallowed Be Thy Name's first verse and riff sat one
beat off while chord changes piled up on the tracker's beat 3. Section boundaries, the
validator's snap advice, and every bar-gridded light cue read those labels.

`rephase_bars` relabels `bar_position` with a Viterbi walk over the four bar positions:

- **Evidence** (per beat, "how much this sounds like a 1"): a chord change on the beat, plus the
  drum stem's kick-minus-snare accent (kick on 1 and 3, snare on 2 and 4) when the stem exists.
  Chord changes decide between 1 and 3, which the kick alone can't.
- **Continuity**: the count advances one position per beat for free; jumping anywhere else (an
  odd bar) costs `SWITCH_COST`, so the phase only moves where the music clearly says so.
- **Prior**: every beat that keeps the tracker's label earns `PRIOR`, so where evidence is flat
  (a cymbal-washed solo) the tracker's phase stands.

Deterministic, numpy-free, idempotent in practice (re-running on its own output finds the same
path). Returns False and leaves the beats untouched when there is no evidence to weigh.
"""

from __future__ import annotations

import logging
from bisect import bisect_left

from .schema import Beat

log = logging.getLogger(__name__)

CHORD_TOL_S = 0.12      # a chord change this close to a beat lands ON that beat
CHORD_WEIGHT = 1.0      # one chord change on a beat ≈ one strong kick-over-snare accent
DRUM_WEIGHT = 0.5
SWITCH_COST = 4.0       # what an odd bar must earn back before the phase moves
PRIOR = 0.02            # per beat that keeps the tracker's label: light, so an odd bar lands where
                        # the evidence changes, not wherever the prior first outweighs it


def chord_evidence(beat_times: list[float], change_times: list[float],
                   tol: float = CHORD_TOL_S) -> list[float]:
    """1.0 for a beat with a chord change within `tol`, else 0.0."""
    ch = sorted(change_times)
    out = []
    for t in beat_times:
        i = bisect_left(ch, t - tol)
        out.append(1.0 if i < len(ch) and ch[i] <= t + tol else 0.0)
    return out


def drum_evidence(drums, sr: int, beat_times: list[float]) -> list[float]:
    """Per beat: low-band (kick) onset strength minus high-band (snare) onset strength, each
    normalized by its song mean, clipped to ±2. Empty on any failure."""
    try:
        import numpy as np
        import librosa
        hop = 256
        spec = np.abs(librosa.stft(np.asarray(drums, dtype=float), n_fft=2048, hop_length=hop))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

        def flux(band):
            e = spec[band].sum(0)
            return np.maximum(0.0, np.diff(e, prepend=e[:1]))

        kick, snare = flux(freqs < 150), flux((freqs > 1500) & (freqs < 5000))
        frames = librosa.time_to_frames(np.asarray(beat_times), sr=sr, hop_length=hop)

        def at(arr):
            v = np.array([arr[max(0, f - 3):f + 4].max() if f < len(arr) else 0.0
                          for f in frames])
            return v / (v.mean() or 1.0)

        return [float(x) for x in np.clip(at(kick) - at(snare), -2.0, 2.0)]
    except Exception as exc:  # noqa: BLE001 — evidence is optional; chords alone still work
        log.debug("drum evidence unavailable: %s", exc)
        return []


def rephase_bars(beats: list[Beat], *, chord_times: list[float] | None = None,
                 drum_accent: list[float] | None = None, bpb: int | None = None) -> bool:
    """Relabel `beats[*].bar_position` in place (see module doc). True when any label changed."""
    labels = [b.bar_position for b in beats]
    if len(beats) < 2 * 4 or any(lab is None for lab in labels):
        return False
    n_pos = bpb or max(lab for lab in labels if lab is not None)
    if n_pos < 2:
        return False
    times = [float(b.time) for b in beats]
    chords = chord_evidence(times, chord_times or [])
    drums = drum_accent if drum_accent and len(drum_accent) == len(beats) else [0.0] * len(beats)
    raw = [CHORD_WEIGHT * c + DRUM_WEIGHT * d for c, d in zip(chords, drums)]
    if not any(raw):
        return False
    mean = sum(raw) / len(raw)
    ev = [r - mean for r in raw]            # a downbeat on an ordinary beat scores ~0

    # Viterbi over positions 0..n_pos-1 (0 == the downbeat)
    def gain(j: int, p: int) -> float:
        return (ev[j] if p == 0 else 0.0) + (PRIOR if labels[j] == p + 1 else 0.0)

    score = [gain(0, p) for p in range(n_pos)]
    back: list[list[int]] = []
    for j in range(1, len(beats)):
        best_any = max(range(n_pos), key=lambda q: score[q])
        new, ptr = [], []
        for p in range(n_pos):
            q_next = (p - 1) % n_pos            # the free predecessor: the count just advanced
            stay = score[q_next]
            jump = score[best_any] - SWITCH_COST
            if stay >= jump or best_any == q_next:
                new.append(stay + gain(j, p))
                ptr.append(q_next)
            else:
                new.append(jump + gain(j, p))
                ptr.append(best_any)
        score = new
        back.append(ptr)
    p = max(range(n_pos), key=lambda q: score[q])
    path = [p]
    for ptr in reversed(back):
        p = ptr[p]
        path.append(p)
    path.reverse()

    changed = False
    for b, pos in zip(beats, path):
        if b.bar_position != pos + 1:
            b.bar_position = pos + 1
            changed = True
    if changed:
        shifts = [round(times[j], 1) for j in range(1, len(path))
                  if path[j] != (path[j - 1] + 1) % n_pos]
        log.info("bar phase re-checked: odd bars at %s", shifts or "the start")
    return changed
