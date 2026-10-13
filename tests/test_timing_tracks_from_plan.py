"""Reference timing tracks from the creative brief's sections + the analysis.

`finalize` builds the timing tracks from the analysis plus the creative brief's `SectionPlan`s:
section labels from the plan (index labels when blank), the beat/bar grid at the meter detected
from the analysis, onsets from the stems (or the whole mix).
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from types import SimpleNamespace

from xlights_orchestrator.pipeline import timing as T
from xlights_orchestrator.pipeline.meter import resolve_beats_per_bar
from xlights_orchestrator.show_plan import SectionPlan, ShowPlan


# -- fixtures -----------------------------------------------------------------

def _stem(name, onsets, energy=1.0):
    arc = [SimpleNamespace(time=0.0, rms=energy), SimpleNamespace(time=1.0, rms=energy)]
    return SimpleNamespace(stem=name, onsets=onsets, energy_arc=arc)


def _sa(*, n_beats=12, beats_per_bar=4, stems=None, duration_s=10.0, onsets=None):
    """A stub analysis: beats every 0.5 s stamped with a `bar_position` at the given meter, so the
    meter is DETECTED from the analysis (no brief needed)."""
    beats = [SimpleNamespace(time=i * 0.5, bar_position=(i % beats_per_bar) + 1)
             for i in range(n_beats)]
    feats = [_stem(k, ons) for k, ons in (stems or {}).items()]
    return SimpleNamespace(beats=beats, stems=feats, chords=[], lyrics=None,
                           duration_s=duration_s, onsets=onsets or [])


def _plan_sections(labels=("intro", "verse", "chorus")):
    """Plan sections as the brief contract describes them: `label` + `start_ms`/`end_ms`."""
    step = 3000
    return [SimpleNamespace(label=l, start_ms=i * step, end_ms=(i + 1) * step)
            for i, l in enumerate(labels)]


def _tracks(sa, sections=None):
    return {t.name: t for t in T.build_timing_tracks(sa, sections=sections)}


# -- section labels come from the plan -----------------------------------------

def test_section_track_uses_plan_labels():
    secs = _plan_sections(("intro", "verse", "chorus"))
    tracks = _tracks(_sa(), secs)
    assert [m.label for m in tracks["Sections"].marks] == ["intro", "verse", "chorus"]
    assert [(m.start_ms, m.end_ms) for m in tracks["Sections"].marks] == \
           [(0, 3000), (3000, 6000), (6000, 9000)]


def test_real_section_plans_without_a_label_get_index_labels():
    # a SectionPlan with a blank `label` falls back to an index label
    plan = ShowPlan(sections=[
        SectionPlan(start_ms=0, end_ms=4000, target_groups=["G"], effect_family="On", intensity=0.2),
        SectionPlan(start_ms=4000, end_ms=8000, target_groups=["G"], effect_family="On", intensity=0.8)])
    tracks = _tracks(_sa(), plan.sections)
    assert [m.label for m in tracks["Sections"].marks] == ["Section 1", "Section 2"]


def test_blank_plan_label_falls_back_to_index():
    secs = [SimpleNamespace(label="", start_ms=0, end_ms=2000),
            SimpleNamespace(label="  ", start_ms=2000, end_ms=4000),
            SimpleNamespace(label="drop", start_ms=4000, end_ms=6000)]
    tracks = _tracks(_sa(), secs)
    assert [m.label for m in tracks["Sections"].marks] == ["Section 1", "Section 2", "drop"]


def test_no_sections_anywhere_means_no_section_track():
    names = {t.name for t in T.build_timing_tracks(_sa())}
    assert "Sections" not in names and "Beats" in names


# -- the beat/bar grid at the detected meter ----------------------------------

def test_beat_and_bar_grid_in_four():
    tracks = _tracks(_sa(n_beats=16, beats_per_bar=4), _plan_sections())
    assert [m.label for m in tracks["Beats"].marks[:5]] == ["1", "2", "3", "4", "1"]
    assert len(tracks["Bars"].marks) == 4                       # 16 beats / 4


def test_meter_detected_from_the_analysis():
    sa = _sa(n_beats=15, beats_per_bar=3)                           # a waltz, per the tracker
    assert resolve_beats_per_bar(sa) == 3
    tracks = _tracks(sa, _plan_sections())
    assert [m.label for m in tracks["Beats"].marks[:4]] == ["1", "2", "3", "1"]
    assert [m.start_ms for m in tracks["Bars"].marks] == [0, 1500, 3000, 4500, 6000]


# -- onsets come from the analysis ---------------------------------------

def test_onset_tracks_come_from_the_stems():
    sa = _sa(stems={"drums": [0.1, 0.6, 1.1], "bass": [0.2, 0.7]})
    tracks = _tracks(sa, _plan_sections())
    assert "Onsets (drums)" in tracks and "Onsets (bass)" in tracks
    assert [m.start_ms for m in tracks["Onsets (drums)"].marks] == [100, 600, 1100]


def test_whole_mix_onset_fallback_without_stems():
    sa = _sa(stems={}, onsets=[0.1, 0.4, 0.9])
    tracks = _tracks(sa, _plan_sections())
    assert "Onsets" in tracks and len(tracks["Onsets"].marks) == 3


# -- finalize patches the tracks from the brief's sections ----------------------

_XSQ = ('<?xml version="1.0" encoding="UTF-8"?>\n<xsequence>'
        '<head><sequenceType>Animation</sequenceType></head>'
        '<DisplayElements><Element type="model" name="G1"/></DisplayElements>'
        '<ElementEffects><Element type="model" name="G1"><EffectLayer/></Element></ElementEffects>'
        '</xsequence>')


class _Client:
    def __init__(self):
        self.calls = []

    async def save_sequence(self, name):
        self.calls.append(("save", name))

    async def close_sequence(self, force=False, quiet=False):
        self.calls.append(("close", force))


def test_finalize_builds_timing_tracks_from_the_plan(tmp_path):
    from xlights_orchestrator.pipeline.finalize import finalize_sequence
    from xlights_orchestrator.pipeline.state import State

    save_as = f"nobrief_{tmp_path.name}"                # unique: never shadowed by the sandbox dir
    xsq = tmp_path / f"{save_as}.xsq"
    xsq.write_text(_XSQ)
    st = State(song_path="s.mp3")
    st.song_analysis = _sa(n_beats=12)
    st.show_plan = ShowPlan(sections=[
        SectionPlan(start_ms=0, end_ms=3000, target_groups=["G1"], effect_family="On", intensity=0.2),
        SectionPlan(start_ms=3000, end_ms=6000, target_groups=["G1"], effect_family="On", intensity=0.9)])
    client = _Client()
    asyncio.run(finalize_sequence(st, client=client, save_as=save_as, media=None,
                                  show_folder=tmp_path, duration_s=6.0, timing_tracks=True))
    assert client.calls == [("save", save_as), ("close", True)]
    root = ET.parse(xsq).getroot()
    timing = {e.get("name"): e for e in root.find("ElementEffects") if e.get("type") == "timing"}
    assert {"Sections", "Beats", "Bars"} <= set(timing)
    labels = [m.get("label") for m in timing["Sections"].find("EffectLayer").findall("Effect")]
    assert labels == ["Section 1", "Section 2"]
