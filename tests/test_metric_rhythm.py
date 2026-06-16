"""Metric rhythm + instrument overlay: backbeat (2 & 4), and phrasing-aware accent softening."""

from __future__ import annotations

from xlights_orchestrator.pipeline.beats import place_beat_accents, select_rhythm_groups
from xlights_orchestrator.show_plan import SectionPlan


def _sec(**kw):
    base = dict(start_ms=0, end_ms=8000, target_groups=["X"], effect_family="On", intensity=0.9,
                palette=["Gold", "Deep Blue"], pulse_groups=["G1", "G2"])
    base.update(kw)
    return SectionPlan(**base)


def _rhythm(beats, drums=None, bpb=4):
    obs = {"drums": drums} if drums else {}
    omag = {"drums": [1.0] * len(drums)} if drums else {}
    return {"beats_ms": beats, "beats_per_bar": bpb, "prominent_stem": "drums" if drums else None,
            "melodic_stem": None, "onsets_by_stem": obs, "onset_mag_by_stem": omag,
            "chords_ms": [], "tempo": 120}


# -- backbeat -----------------------------------------------------------------

def test_backbeat_fires_on_2_and_4_with_drums():
    sec = _sec()
    av = ["G1", "G2", "SEM_SIDE_CENTER"]                      # SIDE_CENTER takes the backbeat
    beats = [i * 500 for i in range(8)]
    acc = place_beat_accents(sec, _rhythm(beats, drums=[i * 120 for i in range(8)]), av)
    assert select_rhythm_groups(sec, av).backbeat == "SEM_SIDE_CENTER"
    bb = sorted(a.start_ms for a in acc if a.target == "SEM_SIDE_CENTER")
    assert bb == [500, 1500, 2500, 3500]                     # beats 2 & 4 of each bar (i % 4 in {1,3})


def test_no_backbeat_without_drums():
    sec = _sec()
    av = ["G1", "G2", "SEM_SIDE_CENTER"]
    acc = place_beat_accents(sec, _rhythm([i * 500 for i in range(8)]), av)   # no drums
    assert not [a for a in acc if a.target == "SEM_SIDE_CENTER"]


# -- phrasing-aware accents ---------------------------------------------------

def test_legato_accents_fade_longer_and_sparser_than_staccato():
    beats = [i * 500 for i in range(16)]
    leg = place_beat_accents(_sec(intensity=0.2), _rhythm(beats), ["G1", "G2"])   # low → legato
    sta = place_beat_accents(_sec(intensity=0.9), _rhythm(beats), ["G1", "G2"])   # high → staccato
    assert leg and sta
    assert any("T_TEXTCTRL_Fadein" in a.extra_settings for a in leg)              # legato breathes
    assert not any("T_TEXTCTRL_Fadein" in a.extra_settings for a in sta)          # staccato crisp
    assert len(leg) < len(sta)                                                    # legato is sparser
    assert max(a.end_ms - a.start_ms for a in leg) > max(a.end_ms - a.start_ms for a in sta)


def test_directed_legato_softens_a_loud_section():
    beats = [i * 500 for i in range(16)]
    sec = _sec(intensity=0.9, phrasing="legato")             # loud, but the Director calls legato
    acc = place_beat_accents(sec, _rhythm(beats), ["G1", "G2"])
    assert any("T_TEXTCTRL_Fadein" in a.extra_settings for a in acc)
