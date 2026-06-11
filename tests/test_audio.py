"""Tests for audio analysis.

Unit tests are hermetic (no audio processing). The integration test runs the real
pipeline over a show .mp3 and skips if the plugins or audio aren't available.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest

from xlights_core.audio import AudioAnalyzer, SongAnalysis
from xlights_core.audio.analyzer import _content_key
from xlights_core.audio.exceptions import AudioPluginsMissing
from xlights_core.audio.extractors import vamp_host


# -- schema (hermetic) --------------------------------------------------------

def test_schema_minimal_and_enrichment_absent():
    sa = SongAnalysis(path="x.mp3", duration_s=10.0, sample_rate=44100, tempo_overall=120.0)
    assert sa.stems is None and sa.section_instrumentation is None
    assert sa.mood is None and sa.lyrics is None
    assert sa.confidences == {}
    # round-trips
    assert SongAnalysis.model_validate_json(sa.model_dump_json()).tempo_overall == 120.0


# -- required plugins (hermetic via monkeypatch) ------------------------------

def test_missing_required_plugin_raises(monkeypatch):
    monkeypatch.setattr(vamp_host, "list_plugins", lambda: ["nnls-chroma:chordino"])
    with pytest.raises(AudioPluginsMissing) as ei:
        vamp_host.check_required_plugins()
    assert "qm-vamp-plugins" in str(ei.value) and "segmentino" in str(ei.value)


def test_all_required_present_ok(monkeypatch):
    monkeypatch.setattr(vamp_host, "list_plugins",
                        lambda: ["qm-vamp-plugins:x", "nnls-chroma:chordino", "segmentino:segmentino"])
    vamp_host.check_required_plugins()  # no raise


# -- caching (hermetic: stub the plugin check, pre-seed the cache) ------------

def test_cache_hit_skips_recompute(tmp_path, monkeypatch):
    monkeypatch.setattr(vamp_host, "check_required_plugins", lambda: None)
    dummy = tmp_path / "audio.bin"
    dummy.write_bytes(b"not really audio")
    cache = tmp_path / "cache"
    cache.mkdir()
    key = _content_key(str(dummy))
    seeded = SongAnalysis(path=str(dummy), duration_s=3.0, sample_rate=44100, tempo_overall=128.0)
    (cache / f"{key}.json").write_text(seeded.model_dump_json())

    az = AudioAnalyzer(cache_dir=cache)
    got = az.analyze(str(dummy), use_cache=True)  # served from cache; never decodes the dummy
    assert got.tempo_overall == 128.0


# -- integration over a real song (skips if unavailable) ----------------------

def _plugins_ready() -> bool:
    try:
        have = {p.split(":", 1)[0] for p in vamp_host.list_plugins()}
        return vamp_host.REQUIRED_PLUGIN_LIBS.issubset(have)
    except Exception:
        return False


_MP3S = sorted(glob.glob("/Users/rob/xlights/*.mp3"))
integration = pytest.mark.skipif(
    not (_MP3S and _plugins_ready()), reason="needs VAMP plugins + a show .mp3"
)


@integration
def test_analyze_real_song(tmp_path):
    az = AudioAnalyzer(cache_dir=tmp_path / "cache")
    sa = az.analyze(_MP3S[0], use_cache=True)

    assert sa.duration_s > 1
    assert sa.tempo_overall and 40 <= sa.tempo_overall <= 220
    assert sa.beats and all(b2.time >= b1.time for b1, b2 in zip(sa.beats, sa.beats[1:]))
    assert any(b.is_downbeat for b in sa.beats)            # bar positions parsed
    assert len(sa.segments) >= 1
    assert sa.energy_arc and len(sa.energy_arc) <= 400
    assert sa.key_overall
    # measurements only — no human/semantic section labels
    semantic = {"verse", "chorus", "bridge", "intro", "outro"}
    assert all(s.segment_id.lower() not in semantic for s in sa.segments)

    # second run is a cache hit (same object content)
    again = az.analyze(_MP3S[0], use_cache=True)
    assert again.model_dump() == sa.model_dump()
