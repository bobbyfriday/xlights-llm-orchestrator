"""Boundary transitions: compose the joins between sections (Phase 3).

Hand shows live on the connective tissue — a riser into a chorus, a one-beat blackout before the
drop, a sweep handoff on a lateral move. Nothing downstream consumed the analyst's boundary cues,
so section joins were butt joints. This pass reads pure signal math (the energy arc, the downbeat
grid, the brief's `transition_cues_ms`) and PLACES those transitions.

Contract:
- Transition instructions carry the OUTGOING section's `section_index` (they occupy its final
  time range) so regenerating the INCOMING section never orphans them.
- The pass is IDEMPOTENT via an `extra_settings` marker: a re-run after a section splice strips its
  own prior output and re-derives, so it replaces rather than stacks. Blackout gating trims end
  times only (never reorders), so occlusion logic still sees final geometry.
- Runs in `generate_instructions` and after refine-loop / `xlo regen` splices, BEFORE
  `finalize_effects`.
"""

from __future__ import annotations

from ..agents.catalog import candidate_look_ids
from ..show_plan import EffectInstruction
from .semantic_groups import PEAK_BROAD_GROUPS
from .meter import DEFAULT_BEATS_PER_BAR

# marker keys — how the pass recognises (and strips) its OWN prior output for idempotence
_MARKER = "_XLO_TRANSITION"          # value: "riser" | "sweep"
_GATE_MARKER = "_XLO_GATED"          # a blackout-gated instruction (end trimmed to the beat)

# detection thresholds on the normalized energy arc (0..1 RMS delta across a boundary)
RISER_DELTA = 0.15                   # energy rises into the boundary by ≥ this → a build/riser
DROP_DELTA = 0.30                    # a large upward STEP at the boundary → the drop hits after it
_RISER_BARS = 2                      # the riser ramps over this many bars ending at the boundary


def _rms_at(energy_arc, t_s: float) -> float:
    """The (normalized) RMS at a time from an EnergyPoint arc; 0 when the arc is empty."""
    arc = list(energy_arc or [])
    if not arc:
        return 0.0
    peak = max((p.rms for p in arc), default=0.0) or 1.0
    nearest = min(arc, key=lambda p: abs(p.time - t_s))
    return max(0.0, min(1.0, nearest.rms / peak))


def _window_rms(energy_arc, t0_s: float, t1_s: float) -> float:
    """Mean normalized RMS over the HALF-OPEN [t0, t1) (falls back to the point value when no
    samples land). Half-open so a boundary sample counts toward the AFTER window only, never
    bleeding into the BEFORE window and inflating the approach slope."""
    arc = list(energy_arc or [])
    if not arc:
        return 0.0
    peak = max((p.rms for p in arc), default=0.0) or 1.0
    inside = [p.rms for p in arc if t0_s <= p.time < t1_s]
    if not inside:
        return _rms_at(energy_arc, (t0_s + t1_s) / 2)
    return max(0.0, min(1.0, (sum(inside) / len(inside)) / peak))


def _bar_ms(sa) -> float:
    """One bar in ms from tempo (else the median beat gap × meter, else a 2s/beat default)."""
    bpb = DEFAULT_BEATS_PER_BAR
    tempo = getattr(sa, "tempo_overall", None)
    if tempo:
        return bpb * 60000.0 / tempo
    beats = [b.time * 1000 for b in (getattr(sa, "beats", None) or [])]
    if len(beats) > 4:
        gaps = sorted(b - a for a, b in zip(beats, beats[1:]))
        return bpb * gaps[len(gaps) // 2]
    return bpb * 2000.0


def _downbeat_times_ms(sa) -> list[int]:
    return sorted(int(b.time * 1000) for b in (getattr(sa, "beats", None) or []) if b.is_downbeat)


def _beats_ms(sa) -> list[int]:
    return sorted(int(b.time * 1000) for b in (getattr(sa, "beats", None) or []))


def _near(value: int, candidates: list[int], tol_ms: float) -> int | None:
    """The candidate closest to `value` within `tol_ms`, else None."""
    if not candidates:
        return None
    best = min(candidates, key=lambda c: abs(c - value))
    return best if abs(best - value) <= tol_ms else None


def _strip_prior(instrs: list[EffectInstruction]) -> list[EffectInstruction]:
    """Remove the pass's own prior riser/sweep placements and UN-gate prior blackouts, so a re-run
    replaces rather than stacks (idempotence). Gated instructions restore their trimmed end from the
    saved original before re-detection."""
    out: list[EffectInstruction] = []
    for ins in instrs:
        if ins.extra_settings.get(_MARKER):
            continue                                  # a prior riser/sweep → drop it
        saved = ins.extra_settings.pop(_GATE_MARKER, None)
        if saved is not None:
            try:
                ins.end_ms = int(saved)               # restore the pre-gate end
            except (TypeError, ValueError):
                pass
        out.append(ins)
    return out


def _riser(section_index: int, boundary_ms: int, bar_ms: float, palette: list[str]
           ) -> EffectInstruction | None:
    """A 2-bar brightness-ramp chase on a broad group, ending AT the boundary (the build)."""
    from xlights_core.knowledge.value_curves import brightness_ramp
    looks = candidate_look_ids("SingleStrand")
    if not looks:
        return None
    start = int(boundary_ms - _RISER_BARS * bar_ms)
    ins = EffectInstruction(
        target=PEAK_BROAD_GROUPS[0], effect_type="SingleStrand", look_id=looks[0],
        render_style="Default", palette_colors=list(palette or [])[:2],
        start_ms=max(0, start), end_ms=int(boundary_ms))
    ins.extra_settings.update(brightness_ramp(40.0, 180.0))    # dark → bright INTO the hit
    ins.extra_settings[_MARKER] = "riser"
    ins.section_index = section_index
    return ins


def _sweep(section_index: int, boundary_ms: int, bar_ms: float, palette: list[str]
           ) -> EffectInstruction | None:
    """A one-bar lateral sweep spanning the boundary — a handoff between adjacent sections."""
    looks = candidate_look_ids("SingleStrand")
    if not looks:
        return None
    ins = EffectInstruction(
        target=PEAK_BROAD_GROUPS[0], effect_type="SingleStrand", look_id=looks[0],
        render_style="Default", palette_colors=list(palette or [])[:2],
        start_ms=int(max(0, boundary_ms - bar_ms // 2)), end_ms=int(boundary_ms + bar_ms // 2))
    ins.extra_settings["E_CHOICE_Chase_Type1"] = "Left-Right"
    ins.extra_settings[_MARKER] = "sweep"
    ins.section_index = section_index
    return ins


def place_transitions(st, instrs: list[EffectInstruction]) -> list[EffectInstruction]:
    """Compose section-boundary transitions from the energy arc + downbeat grid + transition cues.

    Idempotent: strips its own prior output first. Returns a new list (adds risers/sweeps, gates the
    pre-drop beat in place)."""
    sa = getattr(st, "song_analysis", None)
    plan = getattr(st, "show_plan", None)
    sections = list(getattr(plan, "sections", None) or [])
    out = _strip_prior(list(instrs))
    if sa is None or len(sections) < 2:
        return out

    energy = getattr(sa, "energy_arc", None) or []
    bar_ms = _bar_ms(sa)
    downbeats = _downbeat_times_ms(sa)
    beats = _beats_ms(sa)
    cues = set(getattr(getattr(st, "music_brief", None), "transition_cues_ms", None) or [])

    for i in range(len(sections) - 1):
        outgoing, incoming = sections[i], sections[i + 1]
        boundary = int(incoming.start_ms)
        palette = getattr(incoming, "palette", None) or getattr(outgoing, "palette", None) or []
        # energy just BEFORE vs just AFTER the boundary (one bar each side), plus the APPROACH slope
        # (2 bars before → 1 bar before): a riser CLIMBS in; a drop stays flat/low then STEPS at the
        # boundary. before-of-before distinguishes the two so a rising boundary isn't read as a drop.
        far = _window_rms(energy, (boundary - 2 * bar_ms) / 1000.0, (boundary - bar_ms) / 1000.0)
        before = _window_rms(energy, (boundary - bar_ms) / 1000.0, boundary / 1000.0)
        after = _window_rms(energy, boundary / 1000.0, (boundary + bar_ms) / 1000.0)
        delta = after - before
        approach = before - far                       # >0 → energy already climbing into the boundary
        near_cue = any(abs(boundary - c) <= bar_ms for c in cues)
        on_downbeat = _near(boundary, downbeats, bar_ms * 0.5) is not None

        # DROP: a big upward STEP out of a flat/low approach, landing on a downbeat → gate the final
        # beat before the boundary (the display goes dark for that beat and RELIGHTS at the drop).
        # `approach < RISER_DELTA` keeps a smooth BUILD (rising approach) out of the drop branch.
        is_drop = (delta >= DROP_DELTA and approach < RISER_DELTA and on_downbeat) \
            or (near_cue and delta >= DROP_DELTA and on_downbeat)
        if is_drop:
            gate_from = _near(boundary, beats, bar_ms) or int(boundary - bar_ms / DEFAULT_BEATS_PER_BAR)
            beat_start = gate_from - int(bar_ms / DEFAULT_BEATS_PER_BAR)
            for ins in out:
                if (ins.section_index == i and ins.start_ms < beat_start < ins.end_ms
                        and _MARKER not in ins.extra_settings):
                    ins.extra_settings[_GATE_MARKER] = str(ins.end_ms)   # save for idempotent un-gate
                    ins.end_ms = beat_start                              # trim end → dark for the beat
            continue

        # RISER: energy rises INTO the boundary (a build) → a 2-bar ramp chase ending at it.
        if delta >= RISER_DELTA or approach >= RISER_DELTA:
            r = _riser(i, boundary, bar_ms, palette)
            if r is not None:
                out.append(r)
            continue

        # LATERAL: a cued boundary with FLAT energy (neither a build nor a drop) → a sweep handoff.
        # Only on a marked cue, so we don't sweep every quiet join.
        if near_cue:
            s = _sweep(i, boundary, bar_ms, palette)
            if s is not None:
                out.append(s)

    return out
