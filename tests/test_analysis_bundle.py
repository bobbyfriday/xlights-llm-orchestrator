"""The standalone analysis export: analyze_song enrichment, the bundle writer, `xlo analyze`,
and the whisper backend switch. Hermetic — no VAMP, demucs, whisper, or network."""

from __future__ import annotations

import json
import sys
import types

import pytest

from xlights_core.audio import SongAnalysis
from xlights_core.audio.analyzer import _content_key
from xlights_core.audio.schema import (
    Beat, Chord, EnergyPoint, KeyPoint, SectionInstrumentation, Segment, StemFeatures,
)
from xlights_orchestrator.pipeline import analysis as analysis_mod
from xlights_orchestrator.pipeline import bundle


def _sa(path="song.mp3", **kw) -> SongAnalysis:
    beats = [Beat(time=i * 0.5, bar_position=(i % 4) + 1) for i in range(40)]   # 4/4, 120 bpm
    base = dict(
        path=path, duration_s=20.0, sample_rate=44100, tempo_overall=120.0,
        beats=beats, key=[KeyPoint(time=0, key="C major"), KeyPoint(time=10, key="A minor")],
        key_overall="C major",
        chords=[Chord(time=0, label="C"), Chord(time=2, label="C"), Chord(time=4, label="N"),
                Chord(time=5, label="G"), Chord(time=12, label="Am")],
        segments=[Segment(start=0, end=10, segment_id="A"), Segment(start=10, end=20, segment_id="B")],
        onsets=[1.0, 2.0, 11.0], energy_arc=[EnergyPoint(time=t, rms=0.1 if t < 10 else 0.9)
                                              for t in range(20)],
    )
    base.update(kw)
    return SongAnalysis(**base)


# -- summary digest (pure) --------------------------------------------------------

def test_summary_sections_carry_facts():
    s = bundle.summarize(_sa())
    assert s["tempo_bpm"] == 120.0 and s["beats_per_bar"] == 4 and s["key"] == "C major"
    a, b = s["sections"]
    assert (a["id"], a["start"], a["end"]) == ("A", 0.0, 10.0)
    assert a["beats"] == 20 and a["downbeats"] == 5
    assert a["chords"] == ["C", "G"]                   # repeats + no-chord collapsed
    assert b["key"] == "A minor" and b["chords"] == ["Am"]
    assert a["energy"] < b["energy"] and b["energy"] == 1.0
    assert a["onsets_per_s"] == 0.2
    assert s["lyrics"] is None and s["stems"] == []


def test_summary_attaches_stems_and_lyrics_per_section():
    sa = _sa(stems=[StemFeatures(stem="vocals"), StemFeatures(stem="drums")],
             section_instrumentation=[SectionInstrumentation(segment_id="A", start_ms=0, end_ms=10000,
                                                             shares={"drums": 0.7, "vocals": 0.3},
                                                             dominant=["drums"])],
             lyrics={"title": "T", "artist": "X", "lines": [{"text": "hello", "start": 12.0, "end": 13.0}]})
    s = bundle.summarize(sa)
    assert s["stems"] == ["drums", "vocals"]
    assert s["sections"][0]["dominant"] == ["drums"]
    assert "dominant" not in s["sections"][1]
    assert s["sections"][1]["lyrics"] == ["hello"] and s["lyrics"]["timed_lines"] == 1


def test_write_bundle_layout_and_stem_copy(tmp_path, monkeypatch):
    song = tmp_path / "My Song.mp3"
    song.write_bytes(b"not really audio")
    cache = tmp_path / "cache"
    monkeypatch.setenv("XLO_CACHE_DIR", str(cache))
    stems = cache / _content_key(str(song)) / "stems"
    stems.mkdir(parents=True)
    (stems / "vocals.mp3").write_bytes(b"v")
    out = bundle.write_bundle(_sa(str(song), stems=[StemFeatures(stem="vocals")]), str(song),
                              tmp_path / "out", degradations=[{"capability": "audio:lyrics"}])
    assert (out / "stems" / "vocals.mp3").read_bytes() == b"v"
    m = json.loads((out / "manifest.json").read_text())
    assert m["files"] == ["analysis.json", "summary.json", "stems/vocals.mp3"]
    assert m["capabilities"]["stems"] is True and m["capabilities"]["timed_lyrics"] is False
    assert m["degradations"] == [{"capability": "audio:lyrics"}]
    assert SongAnalysis.model_validate_json((out / "analysis.json").read_text()).tempo_overall == 120.0


# -- analyze_song enrichment ------------------------------------------------------

class _FakeAnalyzer:
    calls: list = []

    def analyze(self, path, *, stems=False):
        return _sa(path)

    def attach_lyrics(self, sa, path, *, text, title="", artist=""):
        self.calls.append(("lyrics", text))
        sa.lyrics = {"lines": [{"text": text, "start": 1.0, "end": 2.0}], "headers_fetch": True}
        return True

    def refine_instrumental(self, sa, path):
        self.calls.append(("instrumental",))
        return False


@pytest.fixture
def fake_analyzer(monkeypatch):
    _FakeAnalyzer.calls = []
    monkeypatch.setattr(analysis_mod, "AudioAnalyzer", _FakeAnalyzer)
    return _FakeAnalyzer


def test_analyze_song_uses_supplied_lyrics_without_genius(fake_analyzer, monkeypatch):
    monkeypatch.setattr(analysis_mod, "fetch_lyrics", lambda p: pytest.fail("Genius consulted"))
    sa = analysis_mod.analyze_song("s.mp3", stems=False, lyrics_text="la la")
    assert fake_analyzer.calls == [("lyrics", "la la")]
    assert sa.lyrics["lines"]


def test_analyze_song_no_lyrics_refines_instrumental(fake_analyzer, monkeypatch):
    monkeypatch.setattr(analysis_mod, "fetch_lyrics", lambda p: pytest.fail("Genius consulted"))
    analysis_mod.analyze_song("s.mp3", stems=False, lyrics=False)
    assert fake_analyzer.calls == [("instrumental",)]


def test_analyze_song_records_stem_loss(fake_analyzer, monkeypatch):
    from xlights_orchestrator import degradations
    monkeypatch.setattr(analysis_mod, "fetch_lyrics", lambda p: None)
    dl = degradations.start_run()
    analysis_mod.analyze_song("s.mp3", stems=True)
    assert "audio:stems" in dl.items


# -- `xlo analyze` ----------------------------------------------------------------

def test_cli_analyze_writes_bundle_without_llm_key(tmp_path, monkeypatch, capsys):
    from xlights_orchestrator import cli
    for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    song = tmp_path / "a song.mp3"
    song.write_bytes(b"x")
    seen = {}

    def fake_analyze_song(path, *, stems, lyrics, lyrics_text):
        seen.update(stems=stems, lyrics=lyrics, text=lyrics_text)
        return _sa(path)

    monkeypatch.setattr(analysis_mod, "analyze_song", fake_analyze_song)
    (tmp_path / "words.txt").write_text("[Chorus]\nhey")
    cli.main(["analyze", str(song), "--out", str(tmp_path / "b"), "--no-stems",
              "--lyrics", str(tmp_path / "words.txt")])
    assert seen == {"stems": False, "lyrics": True, "text": "[Chorus]\nhey"}
    assert (tmp_path / "b" / "a_song" / "summary.json").exists()
    assert "2 sections" in capsys.readouterr().out


# -- whisper backend switch ---------------------------------------------------------

def test_transcribe_falls_back_to_faster_whisper(monkeypatch):
    from xlights_core.audio import lyrics_align as la

    class W:
        def __init__(self, word, start, end):
            self.word, self.start, self.end = word, start, end

    class Model:
        def __init__(self, name, **kw):
            assert name == "small"

        def transcribe(self, path, **kw):
            assert kw["word_timestamps"] is True
            return iter([types.SimpleNamespace(words=[W(" Hello,", 0.5, 0.9), W(" world", 1.0, 1.4)])]), None

    monkeypatch.delenv("XLO_WHISPER_BACKEND", raising=False)
    monkeypatch.setitem(sys.modules, "mlx_whisper", None)            # mlx absent → ImportError
    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=Model))
    assert la._transcribe("v.wav") == [("hello", 0.5, 0.9), ("world", 1.0, 1.4)]


def test_transcribe_no_backend_raises_import_error(monkeypatch):
    from xlights_core.audio import lyrics_align as la
    monkeypatch.setitem(sys.modules, "mlx_whisper", None)
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(ImportError):
        la._transcribe("v.wav")
