"""Tests for lyric-marker-driven structure refinement."""

from __future__ import annotations

from xlights_core.audio.schema import Beat, Segment, SongAnalysis
from xlights_core.audio.structure import refine_segments_with_lyrics


def _sa(duration=200.0, beats=None, segments=None, lyrics=None):
    return SongAnalysis(
        path="x.mp3", duration_s=duration, sample_rate=22050,
        tempo_overall=120.0,
        beats=[Beat(time=t) for t in (beats or [])],
        segments=segments or [Segment(start=0, end=duration, segment_id="A")],
        lyrics=lyrics)


def _lyrics(markers, lines):
    return {"sections": [{"label": l, "start": s} for l, s in markers],
            "lines": [{"text": "x", "start": a, "end": b} for a, b in lines]}


def test_markers_become_beat_snapped_sections():
    beats = [i * 0.5 for i in range(400)]                  # 0–199.5s grid
    ly = _lyrics([("Verse 1", 10.3), ("Chorus", 40.1), ("Verse 2", 80.4)],
                 [(10.3, 12.0), (40.1, 42.0), (80.4, 82.0), (180.0, 182.0)])
    sa = _sa(beats=beats, lyrics=ly)
    assert refine_segments_with_lyrics(sa) is True
    ids = [s.segment_id for s in sa.segments]
    assert ids[:4] == ["intro", "Verse 1", "Chorus", "Verse 2"]
    assert sa.segments[1].start == 10.5                    # snapped to the beat grid
    assert sa.segments[0].start == 0.0
    assert sa.segments[-1].end == 200.0


def test_outro_split_after_last_sung_line():
    ly = _lyrics([("Verse", 10.0), ("Chorus", 40.0)], [(10.0, 12.0), (40.0, 60.0)])
    sa = _sa(duration=100.0, lyrics=ly)
    refine_segments_with_lyrics(sa)
    assert sa.segments[-1].segment_id == "outro" and sa.segments[-1].start == 60.0


def test_tiny_sections_merge_and_short_intro_folds_forward():
    ly = _lyrics([("Verse", 3.0), ("Chorus", 50.0), ("Tag", 55.0)],
                 [(3.0, 5.0), (50.0, 52.0), (55.0, 90.0)])
    sa = _sa(duration=95.0, lyrics=ly)
    refine_segments_with_lyrics(sa)
    ids = [s.segment_id for s in sa.segments]
    assert ids[0] == "Verse" and sa.segments[0].start == 0.0   # 3s intro folded forward
    assert all(s.end - s.start >= 6 for s in sa.segments[:-1])


def test_instrumental_span_keeps_audio_boundaries():
    old = [Segment(start=0, end=60, segment_id="A"),
           Segment(start=100, end=160, segment_id="B"),     # boundary at 100s, instrumental
           Segment(start=160, end=200, segment_id="C")]
    ly = _lyrics([("Verse", 10.0), ("Chorus", 60.0)],
                 [(10.0, 12.0), (60.0, 70.0)])               # nothing sung after 70s
    sa = _sa(duration=200.0, segments=old, lyrics=ly)
    refine_segments_with_lyrics(sa)
    starts = {s.start for s in sa.segments}
    assert 100.0 in starts                                   # audio boundary retained in-fill
    assert any(s.segment_id == "B" for s in sa.segments)


def test_no_markers_or_one_marker_is_noop():
    sa = _sa(lyrics=_lyrics([("Verse", 10.0)], [(10.0, 12.0)]))
    before = [s.model_dump() for s in sa.segments]
    assert refine_segments_with_lyrics(sa) is False
    assert [s.model_dump() for s in sa.segments] == before
    sa2 = _sa(lyrics=None)
    assert refine_segments_with_lyrics(sa2) is False


def test_idempotent():
    beats = [i * 0.5 for i in range(400)]
    ly = _lyrics([("Verse", 10.3), ("Chorus", 40.1)], [(10.3, 12.0), (40.1, 190.0)])
    sa = _sa(beats=beats, lyrics=ly)
    refine_segments_with_lyrics(sa)
    first = [s.model_dump() for s in sa.segments]
    refine_segments_with_lyrics(sa)
    assert [s.model_dump() for s in sa.segments] == first


def test_panel_render_marks_lyric_labels_ground_truth():
    from xlights_orchestrator.agents.panel import _structure_render
    sa = _sa(segments=[Segment(start=0, end=30, segment_id="Chorus")],
             lyrics={"sections": [{"label": "Chorus", "start": 0.0}], "lines": [], "repeated": []})
    out = _structure_render(sa, None)
    assert "GROUND TRUTH" in out and "Chorus" in out
