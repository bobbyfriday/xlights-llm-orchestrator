"""Phase 3 — boundary transitions: risers into rising boundaries, a one-beat blackout before a
downbeat drop, sweep handoffs on marked lateral joins; tagged to the outgoing section; idempotent."""
from __future__ import annotations

from xlights_orchestrator.music_brief import MusicBrief
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.pipeline.transitions import (
    _GATE_MARKER,
    _MARKER,
    place_transitions,
)
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan, ShowPlan
from xlights_core.audio import Beat, EnergyPoint, SongAnalysis


def _sa(energy_pairs, dur=24.0):
    # 120 BPM → beat every 0.5s, downbeat every 4th (bar_position 1)
    beats = [Beat(time=round(i * 0.5, 3), bar_position=(i % 4) + 1) for i in range(int(dur / 0.5))]
    return SongAnalysis(path="s.mp3", duration_s=dur, sample_rate=44100, tempo_overall=120.0,
                        beats=beats,
                        energy_arc=[EnergyPoint(time=t, rms=r) for t, r in energy_pairs])


def _state(energy_pairs, boundaries, *, cues=None):
    st = State(song_path="s.mp3")
    st.song_analysis = _sa(energy_pairs)
    secs = []
    for i, (s, e) in enumerate(boundaries):
        secs.append(SectionPlan(start_ms=s, end_ms=e, target_groups=["SEM_ALL"],
                                effect_family="On", intensity=0.6, palette=["Red", "Blue"]))
    st.show_plan = ShowPlan(concept="c", sections=secs)
    st.music_brief = MusicBrief(sections=[], transition_cues_ms=cues or [])
    return st


def _ins(target, start, end, sec):
    return EffectInstruction(target=target, effect_type="On", look_id="On#0",
                             start_ms=start, end_ms=end, section_index=sec)


# -- riser --------------------------------------------------------------------

def test_riser_placed_into_a_rising_boundary():
    # energy CLIMBS through the two bars before the 12s boundary (a build/riser into it), not a
    # flat-then-step drop: 8s→0.3, 10s→0.6, 12s→0.9 — a rising approach.
    st = _state([(0, 0.2), (8, 0.3), (10, 0.6), (11, 0.75), (12, 0.9), (24, 0.9)],
                [(0, 12000), (12000, 24000)])
    out = place_transitions(st, [_ins("SEM_ALL", 0, 12000, 0)])
    risers = [i for i in out if i.extra_settings.get(_MARKER) == "riser"]
    assert len(risers) == 1
    r = risers[0]
    assert r.end_ms == 12000                       # ends AT the boundary
    assert r.start_ms < 12000                       # ramps INTO it
    assert r.section_index == 0                      # tagged to the OUTGOING section


# -- blackout before a drop ---------------------------------------------------

def test_drop_gates_the_final_beat():
    # a big upward step at a downbeat boundary (12000ms is a downbeat) out of a FLAT-low approach
    st = _state([(0, 0.15), (8, 0.15), (10, 0.15), (11, 0.15), (12, 0.95), (24, 0.95)],
                [(0, 12000), (12000, 24000)])
    body = _ins("SEM_ALL", 0, 12000, 0)             # a section-spanning effect on the outgoing side
    out = place_transitions(st, [body])
    gated = [i for i in out if _GATE_MARKER in i.extra_settings]
    assert gated, "expected the pre-drop beat to be gated dark"
    # the gated effect now ends BEFORE the boundary (a beat of darkness before the drop relights)
    assert gated[0].end_ms < 12000
    # no riser AND no double-count: it's a drop, not a build
    assert not [i for i in out if i.extra_settings.get(_MARKER) == "riser"]


# -- sweep handoff on a marked lateral join -----------------------------------

def test_sweep_on_a_cued_lateral_boundary():
    # flat energy across a boundary that a transition cue marks → a sweep handoff
    st = _state([(0, 0.5), (12, 0.5), (24, 0.5)], [(0, 12000), (12000, 24000)], cues=[12000])
    out = place_transitions(st, [_ins("SEM_ALL", 0, 12000, 0)])
    sweeps = [i for i in out if i.extra_settings.get(_MARKER) == "sweep"]
    assert len(sweeps) == 1 and sweeps[0].section_index == 0


def test_no_transition_on_a_plain_flat_join():
    st = _state([(0, 0.5), (12, 0.5), (24, 0.5)], [(0, 12000), (12000, 24000)])
    out = place_transitions(st, [_ins("SEM_ALL", 0, 12000, 0)])
    assert not [i for i in out if i.extra_settings.get(_MARKER)]


# -- idempotence --------------------------------------------------------------

def test_idempotent_riser_replaced_not_stacked():
    st = _state([(0, 0.2), (8, 0.3), (10, 0.6), (12, 0.9), (24, 0.9)], [(0, 12000), (12000, 24000)])
    base = [_ins("SEM_ALL", 0, 12000, 0)]
    once = place_transitions(st, base)
    twice = place_transitions(st, once)             # re-run over its own output
    assert len([i for i in once if i.extra_settings.get(_MARKER) == "riser"]) == 1
    assert len([i for i in twice if i.extra_settings.get(_MARKER) == "riser"]) == 1


def test_idempotent_gate_restores_then_re_gates():
    st = _state([(0, 0.15), (8, 0.15), (10, 0.15), (12, 0.95), (24, 0.95)],
                [(0, 12000), (12000, 24000)])
    body = _ins("SEM_ALL", 0, 12000, 0)
    once = place_transitions(st, [body])
    gated_once = [i for i in once if _GATE_MARKER in i.extra_settings][0].end_ms
    twice = place_transitions(st, once)
    gated_twice = [i for i in twice if _GATE_MARKER in i.extra_settings][0].end_ms
    assert gated_once == gated_twice                # re-gates to the SAME beat, doesn't compound


def test_finalize_wires_transitions_and_regen_preserves_the_riser():
    # finalize_effects runs place_transitions; regenerating the INCOMING section (splice) and
    # re-running finalize keeps exactly one riser (tagged to the OUTGOING section, idempotent).
    from xlights_orchestrator.pipeline.generate import finalize_effects
    from xlights_orchestrator.refine import replace_section
    st = _state([(0, 0.2), (8, 0.3), (10, 0.6), (12, 0.9), (24, 0.9)],
                [(0, 12000), (12000, 24000)])
    instrs = [_ins("SEM_ALL", 0, 12000, 0), _ins("SEM_ALL", 12000, 24000, 1)]
    once = finalize_effects(st, instrs)
    risers1 = [i for i in once if i.extra_settings.get(_MARKER) == "riser"]
    assert len(risers1) == 1 and risers1[0].section_index == 0
    # regenerate section 1 (incoming) and re-run finalize
    spliced = replace_section(once, 1, [_ins("SEM_FOCAL", 12000, 24000, 1)])
    twice = finalize_effects(st, spliced)
    risers2 = [i for i in twice if i.extra_settings.get(_MARKER) == "riser"]
    assert len(risers2) == 1                        # exactly one riser survives the regen
