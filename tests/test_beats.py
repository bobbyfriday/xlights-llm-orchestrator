"""Tests for the beat-aware accent layer."""

from __future__ import annotations

from types import SimpleNamespace

from xlights_orchestrator.pipeline.beats import (
    MAX_ACCENTS_PER_SECTION,
    place_beat_accents,
    section_rhythm,
)
from xlights_orchestrator.show_plan import SectionPlan


def _sa(beats_s, stem_onsets):
    return SimpleNamespace(
        beats=[SimpleNamespace(time=t) for t in beats_s],
        stems=[SimpleNamespace(stem=k, onsets=v) for k, v in stem_onsets.items()],
        tempo_overall=120.0)


# -- section_rhythm -----------------------------------------------------------

def test_section_rhythm_window_and_prominent_stem():
    sa = _sa([0.5, 1.5, 2.5, 3.5], {"drums": [1.0, 2.0], "other": [0.6, 1.2], "guitar": [1.1]})
    sec = SectionPlan(start_ms=1000, end_ms=3000, target_groups=["G"], effect_family="On",
                      intensity=0.5, stem_shares={"other": 0.5, "drums": 0.3, "guitar": 0.2})
    r = section_rhythm(sa, sec)
    assert r["beats_ms"] == [1500, 2500]                  # only in-window beats
    assert r["prominent_stem"] == "drums"                 # most non-"other" onsets in-window
    assert r["onsets_by_stem"]["drums"] == [1000, 2000]   # drums onsets in-window


def test_section_rhythm_no_stems_graceful():
    sa = SimpleNamespace(beats=[SimpleNamespace(time=1.0)], stems=None, tempo_overall=None)
    sec = SectionPlan(start_ms=0, end_ms=2000, target_groups=["G"], effect_family="On", intensity=0.5)
    r = section_rhythm(sa, sec)
    assert r["beats_ms"] == [1000] and r["prominent_stem"] is None and r["onsets_by_stem"] == {}


# -- place_beat_accents -------------------------------------------------------

def _rhythm(beats, onsets=None, chords=None):
    return {"beats_ms": beats, "prominent_stem": "drums" if onsets else None,
            "onsets_by_stem": {"drums": onsets or []}, "chords_ms": chords or [], "tempo": 120}


def test_beats_contrast_color_and_downbeat_emphasis():
    sec = SectionPlan(start_ms=0, end_ms=4000, target_groups=["X"], effect_family="On", intensity=0.8,
                      palette=["Gold", "Deep Blue"], pulse_groups=["04_BEAT_1", "04_BEAT_2"])
    acc = place_beat_accents(sec, _rhythm([0, 1000, 2000, 3000]), ["04_BEAT_1", "04_BEAT_2"])
    from xlights_core.knowledge.colors import hue_spread
    accent = acc[0].palette_colors[0]                    # accents = the CONTRAST anchor pair
    assert hue_spread([accent, "#FFD700"]) > 90          # hue-distant from the Gold wash (LED contrast)
    at0 = {a.target for a in acc if a.start_ms == 0}                # downbeat (i=0) → ALL groups
    assert at0 == {"04_BEAT_1", "04_BEAT_2"}
    assert sum(1 for a in acc if a.start_ms == 1000) == 1           # off-beat → single rotating group
    assert acc[0].end_ms == 250                                      # short accent


def test_default_groups_are_sem_sides():
    sec = SectionPlan(start_ms=0, end_ms=2000, target_groups=["Mega"], effect_family="On", intensity=0.5)
    acc = place_beat_accents(sec, _rhythm([0, 500]), ["SEM_FOCAL", "SEM_SIDE_LEFT", "SEM_SIDE_RIGHT"])
    assert {a.target for a in acc} <= {"SEM_SIDE_LEFT", "SEM_SIDE_RIGHT"}   # defaulted to SEM_SIDE_* chase


def test_every_beat_not_downsampled():
    sec = SectionPlan(start_ms=0, end_ms=20000, target_groups=["G"], effect_family="On", intensity=0.8,
                      palette=["Gold", "Deep Blue"], pulse_groups=["04_BEAT_1", "04_BEAT_2"])
    acc = place_beat_accents(sec, _rhythm([i * 500 for i in range(32)]), ["04_BEAT_1", "04_BEAT_2"])
    assert len(acc) >= 32                                            # ~every beat (downbeats add extra), not 24


def test_density_bounded_for_huge_section():
    sec = SectionPlan(start_ms=0, end_ms=100000, target_groups=["G"], effect_family="On", intensity=1.0,
                      pulse_groups=["G"])
    acc = place_beat_accents(sec, _rhythm(list(range(0, 100000, 200))), ["G"])  # 500 beats
    assert len(acc) <= MAX_ACCENTS_PER_SECTION                       # hard upper bound (80)


def test_unplaceable_accent_falls_back_to_on():
    sec = SectionPlan(start_ms=0, end_ms=2000, target_groups=["G"], effect_family="On", intensity=0.5,
                      pulse_groups=["G"], accent_effect="Pulse")        # Pulse is NOT placeable
    acc = place_beat_accents(sec, _rhythm([0, 1000]), ["G"])
    assert acc and all(a.effect_type == "On" and a.look_id for a in acc)   # fell back, valid look


def test_energy_scaled_density():
    beats = [i * 500 for i in range(16)]
    quiet = SectionPlan(start_ms=0, end_ms=8000, target_groups=["M"], effect_family="On", intensity=0.2,
                        palette=["Gold", "Deep Blue"], pulse_groups=["04_BEAT_1", "04_BEAT_2"])
    loud = quiet.model_copy(update={"intensity": 0.9})
    nq = len(place_beat_accents(quiet, _rhythm(beats), ["04_BEAT_1", "04_BEAT_2"]))
    nl = len(place_beat_accents(loud, _rhythm(beats), ["04_BEAT_1", "04_BEAT_2"]))
    assert nq < nl                                                   # quiet sparser than loud
    assert nq > 0                                                    # downbeats still present


def test_hero_onset_layer_follows_prominent_stem():
    sec = SectionPlan(start_ms=0, end_ms=8000, target_groups=["Mega"], effect_family="On", intensity=0.9,
                      palette=["Gold", "Deep Blue"], pulse_groups=["04_BEAT_1"])
    av = ["SEM_SIDE_LEFT", "SEM_FOCAL"]
    acc = place_beat_accents(sec, _rhythm([0, 500], onsets=[100, 600, 1100]), av)
    hero = [a for a in acc if a.target == "SEM_FOCAL"]
    assert [a.start_ms for a in hero] == [100, 600, 1100]           # feature prop on the onsets
    # no stem → no hero layer
    assert not [a for a in place_beat_accents(sec, _rhythm([0, 500]), av)
                if a.target == "SEM_FOCAL"]


def test_chord_driven_accent_color():
    sec = SectionPlan(start_ms=0, end_ms=8000, target_groups=["M"], effect_family="On", intensity=0.9,
                      palette=["Gold", "Deep Blue"], pulse_groups=["04_BEAT_1", "04_BEAT_2"])
    beats = [i * 500 for i in range(16)]
    chords = [(0, "Em"), (2000, "E"), (4000, "C")]
    acc = place_beat_accents(sec, _rhythm(beats, chords=chords), ["04_BEAT_1", "04_BEAT_2"])
    assert len({tuple(a.palette_colors) for a in acc}) > 1           # color steps with chords
    # no chords → single accent color (the hue-distant contrast anchor, brightened)
    one = place_beat_accents(sec, _rhythm(beats), ["04_BEAT_1", "04_BEAT_2"])
    assert len({tuple(a.palette_colors) for a in one}) == 1


def test_onset_mode_uses_stem_onsets():
    sec = SectionPlan(start_ms=0, end_ms=4000, target_groups=["G"], effect_family="On", intensity=0.5,
                      pulse_groups=["G"], pulse_on="onset")
    acc = place_beat_accents(sec, _rhythm([0, 2000], onsets=[100, 900, 1700]), ["G"])
    assert [a.start_ms for a in acc] == [100, 900, 1700]                # rode the onsets, not the beats
