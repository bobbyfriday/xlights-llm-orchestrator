"""Instrument-entrance features: detect a stem surging in (the 2:07 guitar) and FEATURE it —
the focal prop rides the entering instrument's onsets for a bounded window ("the solo prop is
the soloist"). Detection is pure audio (per-stem energy arcs), song-agnostic."""

from __future__ import annotations

from ..agents.catalog import candidate_look_ids, placeable_effect_types
from ..show_plan import EffectInstruction
from .beats import HERO_GROUP, _accent_look, _downsample, effect_palette

SURGE_RATIO = 1.3            # next-window energy vs prior (catches sustained step-ups, not just from-silence)
SURGE_FLOOR = 0.40           # must reach 40% of the stem's own peak
PRIOR_CEIL = 0.45            # ...having been below 45% (an entrance/surge, not a continuation)
PRE_S, POST_S = 10.0, 5.0    # comparison windows
DEBOUNCE_S = 20.0            # one entrance per stem per window
FEATURE_MS = 10_000          # how long the feature rides
FEATURE_HITS = 24            # bounded onset hits per feature

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


def _section_at(sections, t_ms: int):
    for i, s in enumerate(sections or []):
        if s.start_ms <= t_ms < s.end_ms:
            return i, s
    return None, None


def instrument_feature_layer(sa, sections, available_groups: list[str]) -> list[EffectInstruction]:
    """Feature each entrance on the focal prop, riding the entering stem's onsets."""
    if HERO_GROUP not in (available_groups or []):
        return []
    onsets_by_stem = {f.stem: [int(t * 1000) for t in (f.onsets or [])]
                      for f in (getattr(sa, "stems", None) or [])}
    out: list[EffectInstruction] = []
    for t_ms, stem in instrument_entrances(sa):
        si, sec = _section_at(sections, t_ms)
        intensity = getattr(sec, "intensity", 0.5) if sec else 0.5
        wanted = STEM_EFFECT.get(stem, "Twinkle") if intensity >= 0.5 else "Twinkle"
        eff, look = (wanted, candidate_look_ids(wanted)[0]) \
            if wanted in placeable_effect_types() and candidate_look_ids(wanted) \
            else _accent_look("")
        colors = effect_palette(list(getattr(sec, "palette", []) or []), eff, 2) if sec else []
        hits = _downsample([t for t in onsets_by_stem.get(stem, [])
                            if t_ms <= t < t_ms + FEATURE_MS], FEATURE_HITS)
        for i, t in enumerate(hits):
            nxt = hits[i + 1] if i + 1 < len(hits) else t + 400
            out.append(EffectInstruction(
                target=HERO_GROUP, effect_type=eff, look_id=look,
                palette_colors=colors, start_ms=int(t),
                end_ms=int(min(nxt, t + 400))))          # section_index=None → survives regens
    return out
