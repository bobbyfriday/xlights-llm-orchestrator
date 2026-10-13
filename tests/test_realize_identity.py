"""Phase 1 integration — the realization keys carrier/composite/palette on the repetition label
(the brief sections' recurring `label`s) and escalates recurring occurrences structurally
(coverage, accent density, a final extra layer)."""
from __future__ import annotations

from xlights_orchestrator.pipeline.generate import realize_section_from_brief
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.pipeline.weave import CARRIER_ROTATION
from xlights_orchestrator.show_plan import SectionPlan, ShowPlan
from xlights_core.audio import Beat, EnergyPoint, Segment, SongAnalysis, StemFeatures

GROUPS = [
    "SEM_ALL", "SEM_BAND_GROUND", "SEM_FOCAL", "SEM_ARCHES", "SEM_CANES",
    "SEM_MINITREES", "SEM_SNOWFLAKES", "SEM_SPINNERS",
    "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT",
]


def _analysis(n_sec: int, sec_ms: int) -> SongAnalysis:
    dur = n_sec * sec_ms / 1000.0
    beats = [Beat(time=round(i * 0.5, 3), bar_position=(i % 4) + 1)
             for i in range(int(dur / 0.5))]
    drum = [round(i * 0.5, 3) for i in range(0, int(dur / 0.5), 2)]
    return SongAnalysis(
        path="s.mp3", duration_s=dur, sample_rate=44100, tempo_overall=120.0,
        beats=beats, onsets=[round(i * 0.5, 3) for i in range(int(dur / 0.5))],
        segments=[Segment(start=i * sec_ms / 1000, end=(i + 1) * sec_ms / 1000, segment_id=str(i))
                  for i in range(n_sec)],
        energy_arc=[EnergyPoint(time=0, rms=0.8), EnergyPoint(time=dur, rms=0.85)],
        stems=[StemFeatures(stem="drums", onsets=drum,
                            energy_arc=[EnergyPoint(time=0, rms=0.8),
                                        EnergyPoint(time=dur, rms=0.9)])],
    )


def _section(i: int, sec_ms: int, intensity: float, label: str) -> SectionPlan:
    return SectionPlan(
        start_ms=i * sec_ms, end_ms=(i + 1) * sec_ms, label=label,
        target_groups=["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_ALL", "SEM_FOCAL",
                       "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT"],
        effect_family="On", intensity=intensity, palette=["Red", "Green", "Blue"],
        pulse_groups=["SEM_ARCHES"], pulse_on="beat")


def _state(intensities, labels) -> State:
    sec_ms = 8000
    n = len(intensities)
    st = State(song_path="s.mp3")
    st.song_analysis = _analysis(n, sec_ms)
    st.available_groups = list(GROUPS)
    st.show_plan = ShowPlan(
        concept="c", sections=[_section(i, sec_ms, v, labels[i]) for i, v in enumerate(intensities)])
    return st


def _carriers(instrs):
    return {i.effect_type for i in instrs} & set(CARRIER_ROTATION)


def test_choruses_share_carrier_one_offs_may_differ():
    # sections 0,1,2 are all "chorus"; the deterministic fallback weave rotates a carrier per section
    st = _state([0.9, 0.9, 0.9], ["chorus", "chorus", "chorus"])
    outs = [realize_section_from_brief(st, i) for i in range(3)]
    c0, c1, c2 = (_carriers(o) for o in outs)
    assert c0 and c0 == c1 == c2                       # every chorus shares the carrier (rhymes)


def test_one_off_sections_rotate_by_index():
    # no recurring labels → each section keys its carrier on the index (varies), as before
    st = _state([0.9, 0.9], ["intro", "outro"])
    o0 = realize_section_from_brief(st, 0)
    o1 = realize_section_from_brief(st, 1)
    assert _carriers(o0) != _carriers(o1)


def _lit_targets(instrs):
    return {i.target for i in instrs}


def test_final_chorus_is_fuller_and_gains_a_layer():
    st = _state([0.9, 0.9, 0.9], ["chorus", "chorus", "chorus"])
    first = realize_section_from_brief(st, 0)
    last = realize_section_from_brief(st, 2)
    # structural escalation: the final occurrence lights at least as many prop groups
    assert len(_lit_targets(last)) >= len(_lit_targets(first))
    # ...and gains the extra sparkle-contrast layer on an accent prop group
    accent_layer = [i for i in last if i.target == "SEM_SNOWFLAKES" and i.effect_type == "Twinkle"]
    first_accent = [i for i in first if i.target == "SEM_SNOWFLAKES" and i.effect_type == "Twinkle"]
    assert accent_layer and not first_accent


def test_escalation_never_exceeds_available_groups():
    st = _state([0.95, 0.95, 0.95, 0.95], ["chorus"] * 4)
    for i in range(4):
        out = realize_section_from_brief(st, i)
        assert _lit_targets(out) <= set(GROUPS)         # caps hold
