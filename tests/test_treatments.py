"""Phase 2 — section treatments: realize_section withholds LAYERS per treatment (not just dims),
the deterministic fallback maps energy → treatment, and the bed floor guards long dark stretches."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xlights_orchestrator.pipeline.beats import resolve_treatment
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

    async def run(self, _r):
        return SimpleNamespace(output=self._e.model_copy(deep=True))


# -- fallback mapping (design table) ------------------------------------------

def _sec(intensity, treatment=""):
    return SectionPlan(start_ms=0, end_ms=8000, target_groups=["SEM_ARCHES"],
                       effect_family="On", intensity=intensity, treatment=treatment)


def test_resolve_treatment_fallback_table():
    assert resolve_treatment(_sec(0.9), is_peak=True, has_focal=True) == "full"
    assert resolve_treatment(_sec(0.7), is_peak=False, has_focal=True) == "full"   # ≥ peak floor
    assert resolve_treatment(_sec(0.55), is_peak=False, has_focal=True) == "pulse"
    assert resolve_treatment(_sec(0.35), is_peak=False, has_focal=True) == "feature"
    assert resolve_treatment(_sec(0.35), is_peak=False, has_focal=False) == "pulse"  # no hero → pulse
    assert resolve_treatment(_sec(0.15), is_peak=False, has_focal=True) == "gesture"
    assert resolve_treatment(_sec(0.05), is_peak=False, has_focal=True) == "rest"


def test_explicit_treatment_wins():
    assert resolve_treatment(_sec(0.9, "rest"), is_peak=True, has_focal=True) == "rest"
    assert resolve_treatment(_sec(0.1, "full"), is_peak=False, has_focal=True) == "full"
    # an invalid explicit value falls back to the energy mapping
    assert resolve_treatment(_sec(0.9, "sparkly"), is_peak=True, has_focal=True) == "full"


# -- layer inventory per treatment --------------------------------------------

def _analysis(dur=8.0):
    beats = [Beat(time=round(i * 0.5, 3), bar_position=(i % 4) + 1) for i in range(int(dur / 0.5))]
    drum = [round(i * 0.5, 3) for i in range(0, int(dur / 0.5), 2)]
    return SongAnalysis(path="s.mp3", duration_s=dur, sample_rate=44100, tempo_overall=120.0,
                        beats=beats, onsets=[round(i * 0.5, 3) for i in range(int(dur / 0.5))],
                        segments=[Segment(start=0, end=dur, segment_id="A")],
                        energy_arc=[EnergyPoint(time=0, rms=0.8), EnergyPoint(time=dur, rms=0.8)],
                        stems=[StemFeatures(stem="drums", onsets=drum,
                               energy_arc=[EnergyPoint(time=0, rms=0.8)])])


def _state_one(treatment, intensity=0.9):
    st = State(song_path="s.mp3")
    st.song_analysis = _analysis()
    st.available_groups = list(GROUPS)
    st.show_plan = ShowPlan(concept="c", sections=[SectionPlan(
        start_ms=0, end_ms=8000, treatment=treatment, intensity=intensity,
        target_groups=["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_ALL", "SEM_FOCAL"],
        effect_family="On", palette=["Red", "Green", "Blue"], pulse_groups=["SEM_ARCHES"])])
    st.music_brief = None
    return st


def _gen():
    return _FakeGen(SectionEffects(
        instructions=[EffectInstruction(target="SEM_ARCHES", effect_type="On", look_id="On#0",
                                        start_ms=0, end_ms=8000)],
        weave=None))


def _has_carrier(instrs):
    return bool({i.effect_type for i in instrs} & set(CARRIER_ROTATION))


def test_full_has_everything_gesture_has_almost_nothing():
    full = run(realize_section(_state_one("full"), 0, agent=_gen()))
    gesture = run(realize_section(_state_one("gesture"), 0, agent=_gen()))
    # full weaves a carrier + runs the VU feature; gesture runs a single carrier motion, no VU
    assert _has_carrier(full)
    assert not any(i.effect_type == "VU Meter" for i in gesture)
    assert len({i.target for i in gesture}) <= 2         # ≤2 groups
    assert len(gesture) < len(full)                      # visibly sparser


def test_gesture_is_one_carrier_recipe_no_bed_no_accents():
    gesture = run(realize_section(_state_one("gesture"), 0, agent=_gen()))
    # a lone section (no bed floor) → no injected bed; a carrier motion; no beat-accent flood
    assert _has_carrier(gesture)                         # the single held motion
    # no composite (multi-layer stack) and no VU
    assert not any(i.effect_type == "VU Meter" for i in gesture)


def test_pulse_withholds_weave_keeps_accents():
    pulse = run(realize_section(_state_one("pulse"), 0, agent=_gen()))
    assert not _has_carrier(pulse)                       # weave fabric withheld
    assert not any(i.effect_type == "VU Meter" for i in pulse)   # composites/VU withheld
    # a bed + beat accents are present (On effects across rhythm groups)
    assert any(i.effect_type == "On" for i in pulse)


def test_rest_is_dim_and_bounded():
    rest = run(realize_section(_state_one("rest", intensity=0.05), 0, agent=_gen()))
    assert not _has_carrier(rest)
    assert len({i.target for i in rest}) <= 2            # ≤2 groups, a dim bed only


# -- bed floor: >2 consecutive bedless (gesture) sections → a bed injected on the 3rd -----------

def _state_run(treatments):
    st = State(song_path="s.mp3")
    st.song_analysis = _analysis(dur=len(treatments) * 8.0)
    st.available_groups = list(GROUPS)
    st.show_plan = ShowPlan(concept="c", sections=[SectionPlan(
        start_ms=i * 8000, end_ms=(i + 1) * 8000, treatment=t, intensity=0.15,
        target_groups=["SEM_ARCHES"], effect_family="On", palette=["Red", "Blue"])
        for i, t in enumerate(treatments)])
    st.music_brief = None
    return st


def test_bed_floor_injects_after_two_bedless_sections():
    # three consecutive gesture (bedless) sections: the 3rd trips the floor and gets a bed
    st = _state_run(["gesture", "gesture", "gesture"])
    gen = _gen()
    from xlights_orchestrator.pipeline.semantic_groups import BED_PREFERENCE
    third = run(realize_section(st, 2, agent=gen))
    first = run(realize_section(st, 0, agent=gen))
    bed_targets = set(BED_PREFERENCE)
    assert any(i.target in bed_targets and i.effect_type == "On" for i in third)   # floor bed
    assert not any(i.target in bed_targets for i in first)                         # first stays bedless
