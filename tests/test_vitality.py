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


def test_sparkle_rides_drum_hits_not_bars():
    sec = _sec(pulse_groups=["SEM_ARCHES", "SEM_CANES"])             # ring; SNOWFLAKES → sparkle
    av = ["SEM_ARCHES", "SEM_CANES", "SEM_SNOWFLAKES"]
    rhythm = {"beats_ms": [i * 500 for i in range(8)], "beats_per_bar": 4, "prominent_stem": "drums",
              "melodic_stem": None, "onsets_by_stem": {"drums": [120, 600, 1300, 2100]},
              "onset_mag_by_stem": {"drums": [0.9, 0.4, 1.0, 0.3]}, "chords_ms": [], "tempo": 120}
    acc = place_beat_accents(sec, rhythm, av)
    flakes = sorted(a.start_ms for a in acc if a.target == "SEM_SNOWFLAKES")
    assert flakes and set(flakes) <= {120, 600, 1300, 2100}         # the real drum hits, not every bar
    # no drums → no sparkle
    rhythm2 = dict(rhythm, onsets_by_stem={}, onset_mag_by_stem={}, prominent_stem=None)
    assert not [a for a in place_beat_accents(sec, rhythm2, av) if a.target == "SEM_SNOWFLAKES"]


def test_ensemble_bed_high_energy_only():
    av = ["SEM_BAND_GROUND", "SEM_ALL"]
    bed = ensemble_bed(_sec(intensity=0.9), 0.9, av, set())
    assert bed is not None and bed.target == "SEM_BAND_GROUND"
    assert bed.start_ms == 0 and bed.end_ms == 8000               # spans the section
    assert ensemble_bed(_sec(intensity=0.4), 0.4, av, set()) is None          # quiet → no bed
    assert ensemble_bed(_sec(), 0.9, av, {"SEM_BAND_GROUND"}) is None         # already targeted → skip
    assert ensemble_bed(_sec(), 0.9, ["SEM_FOCAL"], set()) is None            # no ensemble group → skip


def test_bass_drives_the_ground_band():
    sec = _sec(pulse_groups=["SEM_ARCHES", "SEM_CANES"])
    av = ["SEM_ARCHES", "SEM_CANES", "SEM_BAND_GROUND"]
    rhythm = {"beats_ms": [i * 500 for i in range(8)], "beats_per_bar": 4, "prominent_stem": "drums",
              "melodic_stem": None, "onsets_by_stem": {"bass": [0, 1000, 2000]},
              "onset_mag_by_stem": {}, "chords_ms": [], "tempo": 120}
    acc = place_beat_accents(sec, rhythm, av)
    bass = sorted(a.start_ms for a in acc if a.target == "SEM_BAND_GROUND")
    assert bass == [0, 1000, 2000]                                   # low sound rides the low band
    # no ground band available → no bass layer
    assert not [a for a in place_beat_accents(sec, rhythm, ["SEM_ARCHES", "SEM_CANES"])
                if a.target == "SEM_BAND_GROUND"]
