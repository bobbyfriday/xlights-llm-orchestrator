"""Downbeat-aware long-section cuts: boundaries land on bar lines, preferring an earlier downbeat
phrase boundary over a louder off-beat seam near the length cap (Christmas Canon intro: 31.777 →
28.7). Falls back to beat snapping when the grid carries no bar positions."""

from __future__ import annotations

from xlights_core.audio.schema import Beat, EnergyPoint, Segment, SongAnalysis
from xlights_core.audio.structure import (
    DOWNBEAT_SNAP_TOL_S,
    _snap,
    _snap_downbeat,
    cap_long_segments,
)

# 0–120s beat grid at 0.5s; bar_position cycles 1..4 so downbeats land on EVEN seconds (0,2,4,…)
def _beats(with_bars: bool):
    return [Beat(time=round(i * 0.5, 3), bar_position=(i % 4) + 1 if with_bars else None)
            for i in range(240)]


def _sa(beats, harmonic=None, energy=None, duration=120.0, seg_end=120.0):
    return SongAnalysis(
        path="x.mp3", duration_s=duration, sample_rate=22050, tempo_overall=120.0,
        beats=beats, segments=[Segment(start=0.0, end=seg_end, segment_id="Intro")],
        harmonic_changes=harmonic or [],
        energy_arc=[EnergyPoint(time=t, rms=r) for t, r in (energy or [])])


# energy: baseline 0.2, a moderate step at 28.0 (|Δ|=0.3) and a LARGER step at 31.5 (|Δ|=0.4)
def _energy():
    out = []
    for i in range(240):
        t = round(i * 0.5, 3)
        r = 0.2 + (0.3 if t >= 28.0 else 0.0) + (0.4 if t >= 31.5 else 0.0)
        out.append((t, r))
    return out


# -- _snap_downbeat unit ------------------------------------------------------

def test_snap_downbeat_prefers_a_nearby_bar_line():
    beats = [round(i * 0.5, 3) for i in range(240)]
    downbeats = [float(s) for s in range(0, 120, 2)]
    assert _snap_downbeat(28.1, beats, downbeats) == 28.0            # within tol → downbeat
    assert _snap_downbeat(31.5, beats, downbeats) == 32.0            # 0.5 ≤ tol → up to the bar line
    # a seam far from any downbeat keeps its beat (29.0 is 1.0 from both 28 and 30 > tol)
    assert _snap_downbeat(29.0, beats, downbeats) == 29.0
    assert abs(29.0 - min(downbeats, key=lambda d: abs(d - 29.0))) > DOWNBEAT_SNAP_TOL_S


def test_snap_downbeat_without_downbeats_is_plain_snap():
    beats = [round(i * 0.5, 3) for i in range(240)]
    assert _snap_downbeat(28.1, beats, []) == _snap(28.1, beats) == 28.0


# -- the Christmas-Canon-shaped case ------------------------------------------

def test_cut_lands_on_downbeat_not_louder_offbeat_near_cap():
    sa = _sa(_beats(with_bars=True), harmonic=[28.1], energy=_energy())
    # cap just under the 32.0 bar line, so the loud 31.5 seam's downbeat (32.0) is past the cap
    assert cap_long_segments(sa, max_section_s=31.9, min_piece_s=12.0) is True
    first = sa.segments[0].end
    assert first == 28.0                                    # the earlier downbeat phrase boundary
    assert first in {float(s) for s in range(0, 120, 2)}    # ...and it IS a bar line


def test_same_data_without_bars_drifts_to_the_louder_offbeat():
    sa = _sa(_beats(with_bars=False), harmonic=[28.1], energy=_energy())
    assert cap_long_segments(sa, max_section_s=31.9, min_piece_s=12.0) is True
    assert sa.segments[0].end == 31.5                       # louder off-beat seam wins (pre-change)


# -- guarantees preserved -----------------------------------------------------

def test_no_op_when_all_sections_fit():
    sa = _sa(_beats(with_bars=True), seg_end=20.0, duration=20.0)
    assert cap_long_segments(sa) is False
    assert [s.segment_id for s in sa.segments] == ["Intro"]


def test_cuts_never_below_min_piece_or_over_cap():
    sa = _sa(_beats(with_bars=True), energy=_energy())
    cap_long_segments(sa, max_section_s=31.9, min_piece_s=12.0)
    for s in sa.segments:
        assert s.end - s.start <= 31.9 + 1e-6
    # every interior piece respects the min-piece floor (last may be a folded tail)
    for s in sa.segments[:-1]:
        assert s.end - s.start >= 12.0 - 1e-6


def test_idempotent_on_its_own_output():
    sa = _sa(_beats(with_bars=True), harmonic=[28.1], energy=_energy())
    cap_long_segments(sa, max_section_s=31.9, min_piece_s=12.0)
    snapshot = [(s.start, s.end, s.segment_id) for s in sa.segments]
    assert cap_long_segments(sa, max_section_s=31.9, min_piece_s=12.0) is False
    assert [(s.start, s.end, s.segment_id) for s in sa.segments] == snapshot
