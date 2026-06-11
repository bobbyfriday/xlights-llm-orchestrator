"""Tests for optional stem separation (hermetic — no demucs/torch runs).

Separation itself is monkeypatched; the per-stem features and per-section prevalence
math run for real on tiny synthetic signals.
"""

from __future__ import annotations

import numpy as np

from xlights_core.audio import SongAnalysis
from xlights_core.audio.analyzer import AudioAnalyzer, _content_key
from xlights_core.audio.extractors import stems as st
from xlights_core.audio.extractors import vamp_host
from xlights_core.audio.schema import Segment


def _seg(sid, a, b):
    return Segment(start=a, end=b, segment_id=sid)


# -- per-section prevalence (pure) --------------------------------------------

def test_prevalence_dominant_per_section():
    sr = 100
    drums = np.concatenate([np.ones(100), np.full(100, 0.01)]).astype("float32")
    vocals = np.concatenate([np.full(100, 0.01), np.ones(100)]).astype("float32")
    stems = {"drums": drums, "vocals": vocals, "bass": np.zeros(200, "float32"),
             "other": np.zeros(200, "float32")}
    si = st.section_instrumentation(stems, sr, [_seg("A", 0, 1), _seg("B", 1, 2)])
    assert si[0].dominant == ["drums"] and si[1].dominant == ["vocals"]
    assert abs(sum(si[0].shares.values()) - 1.0) < 1e-6
    assert si[0].start_ms == 0 and si[0].end_ms == 1000


def test_prevalence_silent_window_no_divzero():
    sr = 100
    stems = {n: np.zeros(200, "float32") for n in st.STEM_NAMES}
    si = st.section_instrumentation(stems, sr, [_seg("A", 0, 1)])
    assert si[0].shares == {} and si[0].dominant == []


def test_prevalence_no_segments():
    sr = 100
    stems = {n: np.ones(100, "float32") for n in st.STEM_NAMES}
    assert st.section_instrumentation(stems, sr, []) == []


def test_stem_features_shape():
    sr = 22050
    y = (np.random.RandomState(0).randn(sr) * 0.1).astype("float32")
    feats = st.stem_features({"drums": y}, sr)
    assert feats[0].stem == "drums" and len(feats[0].energy_arc) > 0


# -- backend resolution (graceful) --------------------------------------------

def test_separate_returns_none_when_no_backend(monkeypatch):
    monkeypatch.setattr(st, "_separate_mlx", lambda p: (_ for _ in ()).throw(ImportError()))
    monkeypatch.setattr(st, "_separate_torch", lambda p: (_ for _ in ()).throw(ImportError()))
    assert st.separate("nope.wav", 44100) is None


def test_normalize_stereo_to_mono():
    raw = {"vocals": np.ones((2, 50), "float32")}  # (channels, samples)
    out = st._normalize(raw, 44100)
    assert out["vocals"].ndim == 1 and out["vocals"].shape[0] == 50


# -- analyzer integration -----------------------------------------------------

def _synth_stems(sr):
    return {n: (np.random.RandomState(i).randn(sr) * 0.1).astype("float32")
            for i, n in enumerate(st.STEM_NAMES)}


def test_attach_stems_wiring(tmp_path, monkeypatch):
    sr = 22050
    monkeypatch.setattr(st, "separate", lambda path, sample_rate: _synth_stems(sr))
    az = AudioAnalyzer(cache_dir=tmp_path)
    sa = SongAnalysis(path="s.mp3", duration_s=1.0, sample_rate=sr,
                      segments=[_seg("A", 0, 0.5), _seg("B", 0.5, 1.0)])
    az._attach_stems(sa, "s.mp3", "key123")
    assert sa.stems is not None and len(sa.stems) == 4
    assert sa.section_instrumentation is not None and len(sa.section_instrumentation) == 2
    assert list((tmp_path / "key123" / "stems").glob("drums.*"))   # mp3 (ffmpeg) or wav fallback


def test_attach_stems_graceful_no_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "separate", lambda path, sample_rate: None)
    az = AudioAnalyzer(cache_dir=tmp_path)
    sa = SongAnalysis(path="s.mp3", duration_s=1.0, sample_rate=22050, segments=[_seg("A", 0, 1)])
    az._attach_stems(sa, "s.mp3", "k")
    assert sa.stems is None and sa.section_instrumentation is None


def test_cache_stems_augment_and_resave(tmp_path, monkeypatch):
    """A cached stem-less analysis must be augmented (not returned stale) on stems=True."""
    monkeypatch.setattr(vamp_host, "check_required_plugins", lambda: None)
    monkeypatch.setattr(st, "separate", lambda path, sample_rate: _synth_stems(22050))
    f = tmp_path / "song.mp3"
    f.write_bytes(b"some-bytes")
    az = AudioAnalyzer(cache_dir=tmp_path)
    key = _content_key(str(f))
    seed = SongAnalysis(path=str(f), duration_s=1.0, sample_rate=22050, segments=[_seg("A", 0, 1)])
    (tmp_path / f"{key}.json").write_text(seed.model_dump_json())  # stem-less cache

    got = az.analyze(str(f), stems=True)
    assert got.stems is not None  # augmented, not the stale stem-less cache hit
    reloaded = SongAnalysis.model_validate_json((tmp_path / f"{key}.json").read_text())
    assert reloaded.stems is not None  # re-saved


def test_cache_no_stems_unchanged(tmp_path, monkeypatch):
    """stems=False returns the cached analysis as-is (no separation)."""
    monkeypatch.setattr(vamp_host, "check_required_plugins", lambda: None)
    called = {"sep": False}
    def _boom(path, sample_rate):
        called["sep"] = True
        return None
    monkeypatch.setattr(st, "separate", _boom)
    f = tmp_path / "song.mp3"
    f.write_bytes(b"abc")
    az = AudioAnalyzer(cache_dir=tmp_path)
    key = _content_key(str(f))
    seed = SongAnalysis(path=str(f), duration_s=1.0, sample_rate=22050)
    (tmp_path / f"{key}.json").write_text(seed.model_dump_json())
    got = az.analyze(str(f), stems=False)
    assert got.stems is None and called["sep"] is False
