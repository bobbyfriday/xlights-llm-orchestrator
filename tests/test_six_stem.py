"""Tests for 6-stem separation + stem mp3 export + cache upgrade."""

from __future__ import annotations

import numpy as np

from xlights_core.audio import SongAnalysis
from xlights_core.audio.analyzer import AudioAnalyzer, _stems_need_refresh
from xlights_core.audio.extractors import stems as st
from xlights_core.audio.schema import StemFeatures


# -- model selection + positional order ---------------------------------------

def test_stems_model_default_and_override(monkeypatch):
    monkeypatch.delenv("XLO_STEMS_MODEL", raising=False)
    assert st.stems_model() == "htdemucs_6s"
    monkeypatch.setenv("XLO_STEMS_MODEL", "htdemucs")
    assert st.stems_model() == "htdemucs"


def test_to_named_six_stem_positional_order():
    seq = [f"arr{i}" for i in range(6)]                       # positional → 6-stem order
    named = st._to_named(seq)
    assert list(named) == ["drums", "bass", "other", "vocals", "guitar", "piano"]
    four = st._to_named([f"a{i}" for i in range(4)])          # 4-stem path unchanged
    assert list(four) == ["drums", "bass", "other", "vocals"]
    d = st._to_named({"Guitar": 1, "Piano": 2})               # dict path: lowercased, passthrough
    assert d == {"guitar": 1, "piano": 2}


# -- shares with guitar/piano (no schema change) ------------------------------

def test_section_instrumentation_includes_guitar_piano():
    sr = 8000
    stems = {n: (np.ones(sr) * v).astype("float32")
             for n, v in [("other", 0.2), ("drums", 0.3), ("guitar", 0.5), ("piano", 0.1)]}
    from xlights_core.audio.schema import Segment
    seg = Segment(start=0.0, end=1.0, segment_id="A")
    si = st.section_instrumentation(stems, sr, [seg])
    assert "guitar" in si[0].shares and "piano" in si[0].shares
    assert si[0].dominant == ["guitar"]                      # loudest stem


# -- mp3 export (with wav fallback) -------------------------------------------

def test_persist_stems_writes_audio(tmp_path):
    az = AudioAnalyzer(cache_dir=tmp_path)
    stems = {"guitar": (np.random.RandomState(0).randn(8000) * 0.1).astype("float32"),
             "piano": (np.random.RandomState(1).randn(8000) * 0.1).astype("float32")}
    az._persist_stems(stems, 8000, "k")
    files = {p.stem: p.suffix for p in (tmp_path / "k" / "stems").glob("*")}
    assert files.get("guitar") in (".mp3", ".wav") and files.get("piano") in (".mp3", ".wav")


def test_persist_stems_wav_fallback_without_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)       # no ffmpeg → wav fallback
    az = AudioAnalyzer(cache_dir=tmp_path)
    az._persist_stems({"bass": (np.zeros(4000)).astype("float32")}, 4000, "k")
    assert (tmp_path / "k" / "stems" / "bass.wav").exists()


# -- cache-upgrade guard ------------------------------------------------------

def _sa_with_stems(names):
    return SongAnalysis(path="s.mp3", duration_s=1.0, sample_rate=8000,
                        stems=[StemFeatures(stem=n) for n in names])


def test_cache_upgrade_guard(monkeypatch):
    monkeypatch.setenv("XLO_STEMS_MODEL", "htdemucs_6s")
    assert _stems_need_refresh(_sa_with_stems(["drums", "bass", "other", "vocals"])) is True   # 4-stem cache → upgrade
    assert _stems_need_refresh(_sa_with_stems(
        ["drums", "bass", "other", "vocals", "guitar", "piano"])) is False                     # already 6-stem
    sa = SongAnalysis(path="s.mp3", duration_s=1.0, sample_rate=8000, stems=None)
    assert _stems_need_refresh(sa) is True                                                     # missing → refresh
    monkeypatch.setenv("XLO_STEMS_MODEL", "htdemucs")
    assert _stems_need_refresh(_sa_with_stems(["drums", "bass", "other", "vocals"])) is False  # 4-stem model satisfied
