"""Tests for the bar-line re-check (xlights_core.audio.bar_phase)."""

from __future__ import annotations

from xlights_core.audio.bar_phase import chord_evidence, rephase_bars
from xlights_core.audio.schema import Beat

IBI = 0.5


def _beats(n: int, first_label: int = 1) -> list[Beat]:
    """A tracker grid: one fixed phase all song, counting 1-2-3-4."""
    return [Beat(time=round(k * IBI, 3), bar_position=(first_label - 1 + k) % 4 + 1)
            for k in range(n)]


def _downbeats(beats: list[Beat]) -> list[float]:
    return [b.time for b in beats if b.bar_position == 1]


def test_chord_evidence_marks_beats_with_a_change():
    assert chord_evidence([0.0, 0.5, 1.0], [0.05, 0.9]) == [1.0, 0.0, 1.0]


def test_an_odd_bar_moves_the_phase_from_there_on():
    beats = _beats(128)
    # the music: bars of 4 from 0 s, one 2/4 bar at beat 64, bars of 4 again after it
    true_ones = [k for k in range(0, 64, 4)] + [k for k in range(66, 128, 4)]
    changes = [k * IBI for k in true_ones]
    assert rephase_bars(beats, chord_times=changes)
    assert _downbeats(beats) == [k * IBI for k in true_ones]


def test_a_whole_song_phase_error_is_corrected():
    beats = _beats(64, first_label=2)               # the tracker calls beat 3 the "1"
    changes = [k * IBI for k in range(0, 64, 4)]
    assert rephase_bars(beats, chord_times=changes)
    assert beats[0].bar_position == 1 and beats[4].bar_position == 1


def test_drum_accents_alone_can_move_it():
    beats = _beats(64, first_label=2)
    kick = [1.5 if k % 4 == 0 else (-1.0 if k % 2 else 0.5) for k in range(64)]
    assert rephase_bars(beats, drum_accent=kick)
    assert beats[0].bar_position == 1


def test_agreeing_evidence_changes_nothing():
    beats = _beats(64)
    assert not rephase_bars(beats, chord_times=[k * IBI for k in range(0, 64, 4)])
    assert [b.bar_position for b in beats] == [b.bar_position for b in _beats(64)]


def test_no_evidence_or_a_stray_change_keeps_the_tracker():
    beats = _beats(64)
    assert not rephase_bars(beats)
    assert not rephase_bars(beats, chord_times=[2 * IBI])   # one off-beat change ≠ an odd bar
    assert [b.bar_position for b in beats] == [b.bar_position for b in _beats(64)]


def test_unlabelled_beats_are_left_alone():
    beats = [Beat(time=k * IBI) for k in range(32)]
    assert not rephase_bars(beats, chord_times=[0.0, 2.0])
    assert all(b.bar_position is None for b in beats)


def test_rechecking_its_own_output_is_stable():
    beats = _beats(128)
    true_ones = [k for k in range(0, 64, 4)] + [k for k in range(66, 128, 4)]
    changes = [k * IBI for k in true_ones]
    rephase_bars(beats, chord_times=changes)
    assert not rephase_bars(beats, chord_times=changes)


def test_a_cached_analysis_rechecks_its_bar_lines_once(tmp_path, monkeypatch):
    from xlights_core.audio import AudioAnalyzer, SongAnalysis
    from xlights_core.audio.analyzer import _content_key
    from xlights_core.audio.extractors import vamp_host
    from xlights_core.audio.schema import STRUCTURE_VERSION, Chord

    monkeypatch.setattr(vamp_host, "check_required_plugins", lambda: None)
    song = tmp_path / "song.bin"
    song.write_bytes(b"not really audio")
    cache = tmp_path / "cache"
    cache.mkdir()
    seeded = SongAnalysis(path=str(song), duration_s=32.0, sample_rate=44100, tempo_overall=120.0,
                          beats=_beats(64, first_label=2), structure_version=1,
                          chords=[Chord(time=k * IBI, label="C") for k in range(0, 64, 4)])
    (cache / f"{_content_key(str(song))}.json").write_text(seeded.model_dump_json())

    got = AudioAnalyzer(cache_dir=cache).analyze(str(song), use_cache=True)
    assert got.beats[0].bar_position == 1 and got.structure_version == STRUCTURE_VERSION
    again = AudioAnalyzer(cache_dir=cache).analyze(str(song), use_cache=True)
    assert [b.bar_position for b in again.beats] == [b.bar_position for b in got.beats]
