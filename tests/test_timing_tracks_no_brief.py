"""The no-MusicBrief path for reference timing tracks and meter resolution.

Interpretation now happens in conversation, so `finalize` builds the timing tracks from the
analysis plus the creative brief's `SectionPlan`s only (`brief=None`). These tests pin that path
against the legacy `brief` path: same grid, labels from the plan, onsets from the analysis.
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


def _legacy_brief(sections, time_signature=None):
    """A stand-in for the old `MusicBrief`: labelled sections + identity.time_signature."""
    return SimpleNamespace(sections=sections,
                           identity=SimpleNamespace(time_signature=time_signature))


def _tracks(sa, brief=None, **kw):
    return {t.name: t for t in T.build_timing_tracks(sa, brief, **kw)}


# -- section labels come from the plan -----------------------------------------

def test_section_track_uses_plan_labels_without_brief():
    secs = _plan_sections(("intro", "verse", "chorus"))
    tracks = _tracks(_sa(), None, fallback_sections=secs)
    assert [m.label for m in tracks["Sections"].marks] == ["intro", "verse", "chorus"]
    assert [(m.start_ms, m.end_ms) for m in tracks["Sections"].marks] == \
           [(0, 3000), (3000, 6000), (6000, 9000)]


def test_section_track_matches_brief_path_for_the_same_sections():
    secs = _plan_sections()
    via_plan = _tracks(_sa(), None, fallback_sections=secs)["Sections"]
    via_brief = _tracks(_sa(), _legacy_brief(secs))["Sections"]
    assert via_plan.marks == via_brief.marks


def test_real_section_plans_without_a_label_get_index_labels():
    # today's SectionPlan carries no `label`; a blank/missing label falls back to an index label
    # (so the field can be added later without this path changing shape)
    plan = ShowPlan(sections=[
        SectionPlan(start_ms=0, end_ms=4000, target_groups=["G"], effect_family="On", intensity=0.2),
        SectionPlan(start_ms=4000, end_ms=8000, target_groups=["G"], effect_family="On", intensity=0.8)])
    tracks = _tracks(_sa(), None, fallback_sections=plan.sections)
    assert [m.label for m in tracks["Sections"].marks] == ["Section 1", "Section 2"]
    # the ShowPlan itself can also sit in the `brief` slot (it has `.sections`) — same result
    assert _tracks(_sa(), plan)["Sections"].marks == tracks["Sections"].marks


def test_blank_plan_label_falls_back_to_index():
    secs = [SimpleNamespace(label="", start_ms=0, end_ms=2000),
            SimpleNamespace(label="  ", start_ms=2000, end_ms=4000),
            SimpleNamespace(label="drop", start_ms=4000, end_ms=6000)]
    tracks = _tracks(_sa(), None, fallback_sections=secs)
    assert [m.label for m in tracks["Sections"].marks] == ["Section 1", "Section 2", "drop"]


def test_no_sections_anywhere_means_no_section_track():
    names = {t.name for t in T.build_timing_tracks(_sa(), None)}
    assert "Sections" not in names and "Beats" in names


# -- the beat/bar grid is identical with and without a brief ---------------------

def test_beat_and_bar_grid_matches_brief_path():
    sa = _sa(n_beats=16, beats_per_bar=4)
    secs = _plan_sections()
    no_brief = _tracks(sa, None, fallback_sections=secs)
    with_brief = _tracks(sa, _legacy_brief(secs))
    assert no_brief["Beats"].marks == with_brief["Beats"].marks
    assert no_brief["Bars"].marks == with_brief["Bars"].marks
    assert [m.label for m in no_brief["Beats"].marks[:5]] == ["1", "2", "3", "4", "1"]
    assert len(no_brief["Bars"].marks) == 4                       # 16 beats / 4


def test_meter_detected_from_the_analysis_without_brief():
    sa = _sa(n_beats=15, beats_per_bar=3)                           # a waltz, per the tracker
    assert resolve_beats_per_bar(sa, None) == 3
    no_brief = _tracks(sa, None, fallback_sections=_plan_sections())
    with_brief = _tracks(sa, _legacy_brief(_plan_sections()))        # brief has no override
    assert [m.label for m in no_brief["Beats"].marks[:4]] == ["1", "2", "3", "1"]
    assert no_brief["Bars"].marks == with_brief["Bars"].marks
    assert [m.start_ms for m in no_brief["Bars"].marks] == [0, 1500, 3000, 4500, 6000]


def test_resolve_beats_per_bar_tolerates_a_show_plan_and_top_level_override():
    sa = _sa(n_beats=15, beats_per_bar=3)
    plan = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=1000, target_groups=["G"],
                                          effect_family="On", intensity=0.5)])
    assert resolve_beats_per_bar(sa, plan) == 3                     # no override field → detected
    assert resolve_beats_per_bar(sa, SimpleNamespace(time_signature="6/8")) == 6
    assert resolve_beats_per_bar(sa, _legacy_brief([], "5/4")) == 5   # legacy identity override


# -- onsets still come from the analysis ---------------------------------------

def test_onset_tracks_still_appear_without_brief():
    sa = _sa(stems={"drums": [0.1, 0.6, 1.1], "bass": [0.2, 0.7]})
    tracks = _tracks(sa, None, fallback_sections=_plan_sections())
    assert "Onsets (drums)" in tracks and "Onsets (bass)" in tracks
    assert [m.start_ms for m in tracks["Onsets (drums)"].marks] == [100, 600, 1100]


def test_whole_mix_onset_fallback_without_brief_or_stems():
    sa = _sa(stems={}, onsets=[0.1, 0.4, 0.9])
    tracks = _tracks(sa, None, fallback_sections=_plan_sections())
    assert "Onsets" in tracks and len(tracks["Onsets"].marks) == 3


def test_full_track_set_identical_with_and_without_brief():
    sa = _sa(n_beats=16, stems={"drums": [0.1, 0.6], "vocals": [0.2]}, onsets=[0.1])
    secs = _plan_sections()
    a = T.build_timing_tracks(sa, None, fallback_sections=secs)
    b = T.build_timing_tracks(sa, _legacy_brief(secs))
    assert [(t.name, t.layer_list()) for t in a] == [(t.name, t.layer_list()) for t in b]


# -- finalize patches the tracks with st.music_brief = None ----------------------

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


def test_finalize_builds_timing_tracks_from_the_plan_without_music_brief(tmp_path):
    from xlights_orchestrator.pipeline.finalize import finalize_sequence
    from xlights_orchestrator.pipeline.state import State

    save_as = f"nobrief_{tmp_path.name}"                # unique: never shadowed by the sandbox dir
    xsq = tmp_path / f"{save_as}.xsq"
    xsq.write_text(_XSQ)
    st = State(song_path="s.mp3")
    st.song_analysis = _sa(n_beats=12)
    st.music_brief = None
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
