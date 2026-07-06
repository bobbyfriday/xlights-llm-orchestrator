"""Instrument-entrance detection: a stem surging in (the 2:07 guitar) becomes a key moment
and the `instrument_entrance` trigger features it on the focal prop ("the solo prop is the
soloist"). Detection is pure audio (per-stem energy arcs), song-agnostic."""

from __future__ import annotations

SURGE_RATIO = 1.3            # next-window energy vs prior (catches sustained step-ups, not just from-silence)
SURGE_FLOOR = 0.40           # must reach 40% of the stem's own peak
PRIOR_CEIL = 0.45            # ...having been below 45% (an entrance/surge, not a continuation)
PRE_S, POST_S = 10.0, 5.0    # comparison windows
DEBOUNCE_S = 20.0            # one entrance per stem per window

# stem → the effect that features its entrance (the `instrument_entrance` trigger detector)
STEM_EFFECT = {"guitar": "Lightning", "piano": "Meteors", "drums": "Shockwave",
               "bass": "On", "vocals": "Twinkle"}


def instrument_entrances(sa) -> list[tuple[int, str]]:
    """(t_ms, stem) where a stem SURGES in: quiet before, loud and sustained after."""
    out: list[tuple[int, str]] = []
    for f in getattr(sa, "stems", None) or []:
        if f.stem == "other" or not (f.energy_arc and f.onsets):
            continue
        arc = sorted(f.energy_arc, key=lambda p: p.time)
        peak = max(p.rms for p in arc) or 1.0
        last = -1e9
        for p in arc:
            t = p.time
            if t - last < DEBOUNCE_S:
                continue
            prior = [q.rms for q in arc if t - PRE_S <= q.time < t]
            after = [q.rms for q in arc if t <= q.time < t + POST_S]
            if not prior or not after:
                continue
            m_prior = sum(prior) / len(prior)
            m_after = sum(after) / len(after)
            if (m_after >= SURGE_RATIO * max(m_prior, 1e-6)
                    and m_after >= SURGE_FLOOR * peak
                    and m_prior < PRIOR_CEIL * peak):
                out.append((int(t * 1000), f.stem))
                last = t
    return sorted(out)


