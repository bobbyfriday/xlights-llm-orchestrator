"""Phase 1 meter handling: resolve beats-per-bar and grid the rhythm/timing layers to it."""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

from xlights_orchestrator.pipeline.beats import place_beat_accents, section_rhythm
from xlights_orchestrator.pipeline.meter import (
    DEFAULT_BEATS_PER_BAR,
    detect_beats_per_bar,
    parse_time_signature,
    resolve_beats_per_bar,
)
from xlights_orchestrator.pipeline.timing import _bar_track
from xlights_orchestrator.show_plan import SectionPlan


# -- parsing ------------------------------------------------------------------

def test_parse_time_signature():
    assert parse_time_signature("3/4") == 3
    assert parse_time_signature("6/8") == 6
    assert parse_time_signature("4/4") == 4
    assert parse_time_signature("5") == 5
    assert parse_time_signature("") is None
    assert parse_time_signature(None) is None
    assert parse_time_signature("common time") is None   # non-numeric → no guess
    assert parse_time_signature("13/8") is None           # out of 2..12 range


# -- resolution precedence ----------------------------------------------------

def _sa(bar_positions=None):
    beats = [SimpleNamespace(time=i * 0.5, bar_position=bp)
             for i, bp in enumerate(bar_positions or [])]
    return SimpleNamespace(beats=beats)


def _brief(ts):
    return SimpleNamespace(identity=SimpleNamespace(time_signature=ts))


def test_brief_time_signature_overrides():
    sa = _sa([1, 2, 3, 4] * 4)                 # tracker says 4/4...
    assert resolve_beats_per_bar(sa, _brief("3/4")) == 3   # ...but the brief says waltz → 3 wins


def test_detection_from_bar_positions():
    sa = _sa([1, 2, 3] * 5)                     # downbeats recur every 3rd beat
    assert detect_beats_per_bar(sa) == 3
    assert resolve_beats_per_bar(sa, None) == 3


def test_defaults_to_four_when_unknown():
    assert resolve_beats_per_bar(_sa([]), None) == DEFAULT_BEATS_PER_BAR
    assert resolve_beats_per_bar(_sa([]), _brief("")) == DEFAULT_BEATS_PER_BAR
    # robust to stub beats with no bar_position attribute at all
    assert resolve_beats_per_bar(SimpleNamespace(beats=[SimpleNamespace(time=0.0)]), None) == 4


# -- section_rhythm carries it ------------------------------------------------

def test_section_rhythm_carries_beats_per_bar():
    sa = SimpleNamespace(beats=[SimpleNamespace(time=0.5)], stems=None, tempo_overall=120.0)
    sec = SectionPlan(start_ms=0, end_ms=2000, target_groups=["G"], effect_family="On", intensity=0.5)
    assert section_rhythm(sa, sec, beats_per_bar=3)["beats_per_bar"] == 3
    assert section_rhythm(sa, sec)["beats_per_bar"] == 4          # default


# -- the meter actually moves the downbeats -----------------------------------

def _rhythm(beats_ms, bpb):
    return {"beats_ms": beats_ms, "prominent_stem": None, "onsets_by_stem": {},
            "chords_ms": [], "tempo": 120, "beats_per_bar": bpb}


def test_meter_drives_downbeat_placement():
    beats = [0, 500, 1000, 1500, 2000, 2500]
    sec = SectionPlan(start_ms=0, end_ms=3000, target_groups=["G1", "G2"], effect_family="On",
                      intensity=1.0, palette=["Gold", "Deep Blue"], pulse_groups=["G1", "G2"])

    def downbeats(bpb):
        acc = place_beat_accents(sec, _rhythm(beats, bpb), ["G1", "G2"])
        counts = Counter(a.start_ms for a in acc)          # a downbeat lights ALL pulse groups
        return {t for t, n in counts.items() if n >= 2}

    assert downbeats(3) == {0, 1500}                        # 3/4 → every 3rd beat
    assert downbeats(4) == {0, 2000}                        # 4/4 → every 4th beat


def test_bar_timing_track_strides_by_meter():
    sa = SimpleNamespace(beats=[SimpleNamespace(time=i * 0.5) for i in range(12)],
                         duration_s=6.0)
    bars3 = _bar_track(sa, 6000, beats_per_bar=3)
    bars4 = _bar_track(sa, 6000, beats_per_bar=4)
    assert [m.start_ms for m in bars3.marks] == [0, 1500, 3000, 4500]   # every 3rd beat
    assert [m.start_ms for m in bars4.marks] == [0, 2000, 4000]         # every 4th beat
