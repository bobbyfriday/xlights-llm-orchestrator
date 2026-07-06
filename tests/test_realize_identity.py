"""Phase 1 integration — realize_section keys carrier/composite/palette on the repetition label
and escalates recurring occurrences structurally (coverage, accent density, a final extra layer)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xlights_orchestrator.music_brief import MusicBrief, LabeledSection
from xlights_orchestrator.pipeline.generate import realize_section
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.pipeline.weave import CARRIER_ROTATION
from xlights_orchestrator.show_plan import (
    EffectInstruction,
    SectionEffects,
    SectionPlan,
    ShowPlan,
)
from xlights_core.audio import Beat, EnergyPoint, Segment, SongAnalysis, StemFeatures

GROUPS = [
    "SEM_ALL", "SEM_BAND_GROUND", "SEM_FOCAL", "SEM_ARCHES", "SEM_CANES",
    "SEM_MINITREES", "SEM_SNOWFLAKES", "SEM_SPINNERS",
    "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT",
]


def run(c):
    return asyncio.run(c)


class _FakeGen:
    def __init__(self, effects):
        self._e = effects

    async def run(self, _rendered):
        # fresh copy per call — realize_section mutates its instructions
        return SimpleNamespace(output=self._e.model_copy(deep=True))


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


def _section(i: int, sec_ms: int, intensity: float) -> SectionPlan:
    return SectionPlan(
        start_ms=i * sec_ms, end_ms=(i + 1) * sec_ms,
        target_groups=["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_ALL", "SEM_FOCAL",
                       "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT"],
        effect_family="On", intensity=intensity, palette=["Red", "Green", "Blue"],
        pulse_groups=["SEM_ARCHES"], pulse_on="beat")


def _state(intensities, repetition_map) -> State:
    sec_ms = 8000
    n = len(intensities)
    st = State(song_path="s.mp3")
    st.song_analysis = _analysis(n, sec_ms)
    st.available_groups = list(GROUPS)
    st.show_plan = ShowPlan(
        concept="c", sections=[_section(i, sec_ms, v) for i, v in enumerate(intensities)])
    st.music_brief = MusicBrief(
        sections=[LabeledSection(start_ms=i * sec_ms, end_ms=(i + 1) * sec_ms, label="l",
                                 intensity=v) for i, v in enumerate(intensities)],
        repetition_map=repetition_map)
    return st


def _gen():
    return _FakeGen(SectionEffects(instructions=[EffectInstruction(
        target="SEM_ARCHES", effect_type="On", look_id="On#0", start_ms=0, end_ms=8000)]))


def _carriers(instrs):
    return {i.effect_type for i in instrs} & set(CARRIER_ROTATION)


def test_choruses_share_carrier_one_offs_may_differ():
    # sections 0,1,2 are all "chorus"; the deterministic fallback weave rotates a carrier per section
    st = _state([0.9, 0.9, 0.9], {"chorus": [0, 1, 2]})
    gen = _gen()
    outs = [run(realize_section(st, i, agent=gen)) for i in range(3)]
    c0, c1, c2 = (_carriers(o) for o in outs)
    assert c0 and c0 == c1 == c2                       # every chorus shares the carrier (rhymes)


def test_one_off_sections_rotate_by_index():
    # no recurring labels → each section keys its carrier on the index (varies), as before
    st = _state([0.9, 0.9], {})
    gen = _gen()
    o0 = run(realize_section(st, 0, agent=gen))
    o1 = run(realize_section(st, 1, agent=gen))
    assert _carriers(o0) != _carriers(o1)


def _lit_targets(instrs):
    return {i.target for i in instrs}


def test_final_chorus_is_fuller_and_gains_a_layer():
    st = _state([0.9, 0.9, 0.9], {"chorus": [0, 1, 2]})
    gen = _gen()
    first = run(realize_section(st, 0, agent=gen))
    last = run(realize_section(st, 2, agent=gen))
    # structural escalation: the final occurrence lights at least as many prop groups
    assert len(_lit_targets(last)) >= len(_lit_targets(first))
    # ...and gains the extra sparkle-contrast layer on an accent prop group
    accent_layer = [i for i in last if i.target == "SEM_SNOWFLAKES" and i.effect_type == "Twinkle"]
    first_accent = [i for i in first if i.target == "SEM_SNOWFLAKES" and i.effect_type == "Twinkle"]
    assert accent_layer and not first_accent


def test_escalation_never_exceeds_available_groups():
    st = _state([0.95, 0.95, 0.95, 0.95], {"chorus": [0, 1, 2, 3]})
    gen = _gen()
    for i in range(4):
        out = run(realize_section(st, i, agent=gen))
        assert _lit_targets(out) <= set(GROUPS)         # caps hold
