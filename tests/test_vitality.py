"""Tests for section vitality: rhythm pool (canes), downbeat sparkle, ensemble bed, wash builds."""
from xlights_orchestrator.pipeline.beats import ensemble_bed, place_beat_accents
from xlights_orchestrator.show_plan import SectionPlan


def _rhythm(beats):
    return {"beats_ms": beats, "prominent_stem": None, "onsets_by_stem": {}, "chords_ms": [], "tempo": 120}


def _sec(**kw):
    base = dict(start_ms=0, end_ms=8000, target_groups=["X"], effect_family="On", intensity=0.9,
                palette=["Gold", "Deep Blue"])
    base.update(kw)
    return SectionPlan(**base)


def test_single_pulse_group_extended_with_rhythm_cells():
    sec = _sec(pulse_groups=["SEM_ARCHES"])                       # the 2:00 failure: one group
    av = ["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_SNOWFLAKES"]
    acc = place_beat_accents(sec, _rhythm([i * 500 for i in range(8)]), av)
    chased = {a.target for a in acc}
    assert "SEM_CANES" in chased                                  # canes join the chase
    assert len({a.target for a in acc if a.start_ms == 500}) == 1   # off-beats still rotate one group


def test_snowflakes_fire_on_downbeats_only():
    sec = _sec(pulse_groups=["SEM_ARCHES", "SEM_CANES"])
    av = ["SEM_ARCHES", "SEM_CANES", "SEM_SNOWFLAKES"]
    acc = place_beat_accents(sec, _rhythm([i * 500 for i in range(8)]), av)
    flakes = [a for a in acc if a.target == "SEM_SNOWFLAKES"]
    assert flakes and all(a.start_ms in (0, 2000) for a in flakes)   # downbeats (every 4th beat) only


def test_ensemble_bed_high_energy_only():
    av = ["SEM_BAND_GROUND", "SEM_ALL"]
    bed = ensemble_bed(_sec(intensity=0.9), 0.9, av, set())
    assert bed is not None and bed.target == "SEM_BAND_GROUND"
    assert bed.start_ms == 0 and bed.end_ms == 8000               # spans the section
    assert ensemble_bed(_sec(intensity=0.4), 0.4, av, set()) is None          # quiet → no bed
    assert ensemble_bed(_sec(), 0.9, av, {"SEM_BAND_GROUND"}) is None         # already targeted → skip
    assert ensemble_bed(_sec(), 0.9, ["SEM_FOCAL"], set()) is None            # no ensemble group → skip


def test_onset_mode_also_sparkles_downbeats():
    sec = _sec(pulse_groups=["SEM_ARCHES", "SEM_CANES"], pulse_on="onset", follow_stem="drums")
    av = ["SEM_ARCHES", "SEM_CANES", "SEM_SNOWFLAKES"]
    rhythm = {"beats_ms": [i * 500 for i in range(8)], "prominent_stem": "drums",
              "onsets_by_stem": {"drums": [100, 700, 1300, 2100]}, "chords_ms": [], "tempo": 120}
    acc = place_beat_accents(sec, rhythm, av)
    flakes = [a for a in acc if a.target == "SEM_SNOWFLAKES"]
    assert flakes and all(a.start_ms in (0, 2000) for a in flakes)   # bar sparkles even in onset mode
