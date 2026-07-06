"""Tests for instrument-entrance detection (featured via the `instrument_entrance` trigger)."""
from types import SimpleNamespace

from xlights_orchestrator.pipeline.features import instrument_entrances


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
