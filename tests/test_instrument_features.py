"""Tests for instrument-entrance detection + the feature layer."""
from types import SimpleNamespace

from xlights_orchestrator.pipeline.features import instrument_entrances, instrument_feature_layer
from xlights_orchestrator.show_plan import SectionPlan


def _stem(name, arc, onsets):
    return SimpleNamespace(stem=name, energy_arc=[SimpleNamespace(time=t, rms=v) for t, v in arc],
                           onsets=onsets)


def _sa(stems):
    return SimpleNamespace(stems=stems)


def _surge_arc():
    return [(t, 0.05) for t in range(0, 20)] + [(t, 0.5) for t in range(20, 40)]   # quiet → loud at 20s


def test_entrance_detected_at_the_surge():
    sa = _sa([_stem("guitar", _surge_arc(), [20.1, 20.5, 21.0])])
    ent = instrument_entrances(sa)
    assert len(ent) == 1 and ent[0][1] == "guitar"
    assert abs(ent[0][0] - 20000) < 4000                       # at/near the surge


def test_no_entrance_for_steady_or_blip():
    steady = _sa([_stem("drums", [(t, 0.5) for t in range(40)], [1.0])])
    assert instrument_entrances(steady) == []                  # already loud → continuation
    blip = _sa([_stem("piano", [(t, 0.05) for t in range(20)] + [(20, 0.6)] + [(t, 0.05) for t in range(21, 40)], [1.0])])
    assert instrument_entrances(blip) == []                    # one-sample blip doesn't sustain


def test_feature_rides_the_entering_stem():
    onsets = [20.2, 20.8, 21.5, 22.3, 23.0, 31.0]              # last one outside the 10s window
    sa = _sa([_stem("guitar", _surge_arc(), onsets)])
    secs = [SectionPlan(start_ms=0, end_ms=40000, target_groups=["X"], effect_family="On",
                        intensity=0.9, palette=["Gold", "Deep Blue"])]
    feats = instrument_feature_layer(sa, secs, ["SEM_FOCAL", "SEM_ARCHES"])
    assert feats and all(f.target == "SEM_FOCAL" for f in feats)
    assert all(f.effect_type == "Lightning" for f in feats)    # guitar → Lightning (energetic section)
    assert {f.start_ms for f in feats} == {20200, 20800, 21500, 22300, 23000}   # rides the onsets, windowed
    assert all(f.section_index is None for f in feats)         # survives refine regens


def test_quiet_section_uses_twinkle_and_no_focal_skips():
    sa = _sa([_stem("guitar", _surge_arc(), [20.5, 21.0])])
    quiet = [SectionPlan(start_ms=0, end_ms=40000, target_groups=["X"], effect_family="On",
                         intensity=0.2, palette=["Warm White"])]
    feats = instrument_feature_layer(sa, quiet, ["SEM_FOCAL"])
    assert feats and all(f.effect_type == "Twinkle" for f in feats)
    assert instrument_feature_layer(sa, quiet, ["SEM_ARCHES"]) == []   # no focal prop → no feature
