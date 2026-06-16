"""Tests for instrumental long-section subdivision (the lyric refiner's complement)."""

from __future__ import annotations

import pytest

from xlights_core.audio.schema import Beat, EnergyPoint, Segment, SongAnalysis
from xlights_core.audio.structure import cap_long_segments, refine_segments_for_instrumental


def _sa(duration=200.0, beats=None, segments=None, lyrics=None,
        harmonic=None, energy=None):
    return SongAnalysis(
        path="x.mp3", duration_s=duration, sample_rate=22050,
        tempo_overall=120.0,
        beats=[Beat(time=t) for t in (beats or [])],
        segments=segments or [Segment(start=0, end=duration, segment_id="A")],
        harmonic_changes=harmonic or [],
        energy_arc=[EnergyPoint(time=t, rms=r) for t, r in (energy or [])],
        lyrics=lyrics)


GRID = [i * 0.5 for i in range(400)]                       # 0–199.5s beat grid


def test_long_segment_splits_at_beat_snapped_harmonic_changes():
    sa = _sa(duration=50.0, beats=GRID, harmonic=[20.3],
             segments=[Segment(start=0, end=50, segment_id="A")])
    assert refine_segments_for_instrumental(sa) is True
    assert [s.segment_id for s in sa.segments] == ["A1", "A2"]
    assert sa.segments[0].end == 20.5                      # 20.3 snapped to the beat grid
    assert sa.segments[1].start == 20.5 and sa.segments[1].end == 50.0


def test_energy_delta_fallback_when_no_harmonic_changes():
    energy = [(float(t), 0.2 if t < 18 else 0.8) for t in range(50)]  # step at t=18
    sa = _sa(duration=50.0, beats=GRID, energy=energy,
             segments=[Segment(start=0, end=50, segment_id="A")])
    assert refine_segments_for_instrumental(sa) is True
    assert sa.segments[0].end == 18.0                      # strongest |delta rms| wins


def test_pure_time_based_last_resort_and_unsnapped_without_beats():
    sa = _sa(duration=50.0, beats=GRID,
             segments=[Segment(start=0, end=50, segment_id="A")])
    refine_segments_for_instrumental(sa)
    assert [s.end for s in sa.segments] == [25.0, 50.0]    # no seam: beat nearest the target
    sa2 = _sa(duration=50.0, segments=[Segment(start=0, end=50, segment_id="A")])
    refine_segments_for_instrumental(sa2)                  # no beats: graceful, unsnapped
    assert [s.end for s in sa2.segments] == [25.0, 50.0]


def test_min_piece_respected_no_slivers():
    sa = _sa(duration=40.0, segments=[Segment(start=0, end=40, segment_id="A")])
    refine_segments_for_instrumental(sa)
    assert all(s.end - s.start >= 12.0 for s in sa.segments)   # cap pulls the cut back
    assert all(s.end - s.start <= 32.0 for s in sa.segments)


def test_tiny_tail_folds_into_previous_piece():
    # a near-end cut would strand a sub-MIN_SECTION tail (only reachable when min_piece < MIN_SECTION);
    # it folds back into the previous piece rather than leaving a sliver.
    sa = _sa(duration=29.0, beats=GRID, segments=[Segment(start=0, end=29, segment_id="A")])
    cap_long_segments(sa, target_s=12.0, flex_s=2.0, min_piece_s=5.0)
    assert [s.segment_id for s in sa.segments] == ["A1", "A2"]
    assert sa.segments[-1].end == 29.0                     # sliver tail absorbed, no sliver
    assert all(s.end - s.start >= 6.0 for s in sa.segments)


def test_labels_ordered_and_parented_across_segments():
    sa = _sa(duration=140.0,
             segments=[Segment(start=0, end=70, segment_id="A"),
                       Segment(start=70, end=140, segment_id="B")])
    refine_segments_for_instrumental(sa)
    ids = [s.segment_id for s in sa.segments]
    assert ids == sorted(ids, key=lambda i: (i[0], int(i[1:])))
    assert all(i.startswith("A") for i in ids if sa.segments[ids.index(i)].end <= 70)
    assert ids[0] == "A1" and "B1" in ids


def test_short_segments_untouched_byte_for_byte():
    short = Segment(start=0, end=10.123, segment_id="N1")
    sa = _sa(duration=60.0, beats=GRID,
             segments=[short, Segment(start=10.123, end=60, segment_id="A")])
    before = short.model_dump()
    refine_segments_for_instrumental(sa)
    assert sa.segments[0] is short and sa.segments[0].model_dump() == before


def test_timed_lyric_lines_disable_refiner():
    sa = _sa(duration=100.0, segments=[Segment(start=0, end=100, segment_id="A")],
             lyrics={"lines": [{"text": "x", "start": 1.0, "end": 2.0}]})
    before = [s.model_dump() for s in sa.segments]
    assert refine_segments_for_instrumental(sa) is False
    assert [s.model_dump() for s in sa.segments] == before


def test_all_short_song_is_noop():
    sa = _sa(duration=60.0, segments=[Segment(start=0, end=30, segment_id="A"),
                                      Segment(start=30, end=60, segment_id="B")])
    before = [s.model_dump() for s in sa.segments]
    assert refine_segments_for_instrumental(sa) is False
    assert [s.model_dump() for s in sa.segments] == before


def test_idempotent():
    sa = _sa(duration=100.0, beats=GRID, harmonic=[20.0, 40.0, 60.0, 80.0],
             segments=[Segment(start=0, end=100, segment_id="A")])
    assert refine_segments_for_instrumental(sa) is True
    first = [s.model_dump() for s in sa.segments]
    assert refine_segments_for_instrumental(sa) is False   # all pieces fit: no-op
    assert [s.model_dump() for s in sa.segments] == first


def test_worked_example_carol_of_the_bells():
    beats = [i * 0.453 for i in range(367)]                # ~132bpm to 165.8s
    harmonic = [18.0 * i for i in range(1, 10)]            # tonal seams every ~18s
    sa = _sa(duration=165.7, beats=beats, harmonic=harmonic,
             segments=[Segment(start=0, end=0.2, segment_id="N1"),
                       Segment(start=0.2, end=73, segment_id="A"),
                       Segment(start=73, end=141.6, segment_id="A"),
                       Segment(start=141.6, end=165.7, segment_id="N3")])
    assert refine_segments_for_instrumental(sa) is True
    ids = [s.segment_id for s in sa.segments]
    assert ids[0] == "N1" and ids[-1] == "N3"              # short edges untouched
    a_ids = [i for i in ids if i not in ("N1", "N3")]
    assert a_ids == [f"A{n}" for n in range(1, len(a_ids) + 1)]   # nested, ordered ordinals
    for s in sa.segments:
        assert s.end - s.start <= 35.0 + 1e-6              # ceiling = target 25 + flex 10
        if s.segment_id != "N1":                           # the 0.2s artifact is exempt
            assert s.end - s.start >= 12.0 - 1e-6
    # contiguous, boundary-preserving cover of the song
    assert sa.segments[0].start == 0.0 and sa.segments[-1].end == 165.7
    for a, b in zip(sa.segments, sa.segments[1:]):
        assert a.end == pytest.approx(b.start, abs=1e-9)
    # cuts landed on the beat grid (the music's own seams, snapped)
    grid = {round(b, 3) for b in beats}
    for s in sa.segments[1:-1]:
        if s.start not in (0.2, 73.0):                     # parent edges keep their times
            assert round(s.start, 3) in grid


def test_panel_render_marks_subsegments_evolving():
    from xlights_orchestrator.agents.panel import _structure_render
    sa = _sa(duration=60.0, segments=[Segment(start=0, end=30, segment_id="A1"),
                                      Segment(start=30, end=60, segment_id="A2")])
    out = _structure_render(sa, None)
    assert "EVOLVING" in out and "A1/A2" in out


# -- the fix: long sections are capped even in a LYRIC song (the 100s-intro bug) ----------------

def test_cap_runs_even_with_lyrics():
    # a lyric song with a long instrumental intro before the first sung line
    sa = _sa(duration=120.0, beats=GRID, harmonic=[30.0, 60.0, 90.0],
             segments=[Segment(start=0, end=100, segment_id="intro"),
                       Segment(start=100, end=120, segment_id="Verse")],
             lyrics={"lines": [{"text": "x", "start": 100.0, "end": 102.0}]})
    # the instrumental refiner bails because lyrics are present (its gate) ...
    assert refine_segments_for_instrumental(sa) is False
    # ... but cap_long_segments subdivides the 100s intro regardless
    assert cap_long_segments(sa) is True
    intro_pieces = [s for s in sa.segments if s.segment_id.startswith("intro")]
    assert len(intro_pieces) >= 3                           # 100s → several ≤32s pieces
    assert all(s.end - s.start <= 32 + 1e-6 for s in sa.segments)
    assert any(s.segment_id == "Verse" for s in sa.segments)   # short section untouched


def test_cap_is_noop_when_all_sections_fit():
    sa = _sa(duration=60.0, beats=GRID,
             segments=[Segment(start=0, end=30, segment_id="A"),
                       Segment(start=30, end=60, segment_id="B")])
    assert cap_long_segments(sa) is False


def test_cap_is_idempotent():
    sa = _sa(duration=100.0, beats=GRID, harmonic=[30.0, 60.0, 90.0],
             segments=[Segment(start=0, end=100, segment_id="A")])
    assert cap_long_segments(sa) is True
    n = len(sa.segments)
    assert cap_long_segments(sa) is False                   # second pass: nothing left to cut
    assert len(sa.segments) == n


# -- cuts land on the ENERGY break, not the latest harmonic before the cap (seam-strength) ------

def test_cut_lands_on_energy_break_not_latest_harmonic():
    # dense harmonic changes across the whole [12,32] window (like Canon's ~every-0.5s noise),
    # plus ONE real energy break at ~28s. Old code picked the latest harmonic (~31.5, cap-drift);
    # new code weights seams by energy change and picks the break.
    harmonic = [12.0 + 0.5 * i for i in range(40)]            # 12.0 .. 31.5, all in-window
    energy = [(float(t), 0.02 if t == 28 else 0.2) for t in range(50)]   # drop-out + re-entry at 28/29
    sa = _sa(duration=50.0, beats=GRID, harmonic=harmonic, energy=energy,
             segments=[Segment(start=0, end=50, segment_id="A")])
    assert cap_long_segments(sa) is True
    first_end = sa.segments[0].end
    assert 27.0 <= first_end <= 30.0                          # the energy break, NOT ~31.5
