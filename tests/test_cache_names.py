"""Readable `<slug>--<hash>` cache names: resolution, legacy fallback, and the cache-rename retrofit."""

import json

from xlights_core import cache_names
from xlights_core.audio import analyzer as an
from xlights_core.audio.analyzer import AudioAnalyzer, _content_key
from xlights_core.audio.extractors import vamp_host
from xlights_core.audio.schema import SongAnalysis
from xlights_orchestrator.pipeline import cache_rename
from xlights_orchestrator.pipeline.cache import cache_root, content_digest, song_key


def test_slugify():
    assert cache_names.slugify("mp3/04 - Carol Of The Bells.mp3") == "carol-of-the-bells"
    assert cache_names.slugify("Cher-DJ_Play_a_Christmas_Song.mp3") == "cher-dj-play-a-christmas-song"
    assert cache_names.slugify("12 - Carmina Burana.mp3") == "carmina-burana"
    assert cache_names.slugify("!!!.mp3") == "song"


def test_song_key_is_readable_and_shared_across_renames(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    a = tmp_path / "christmas canon.mp3"
    a.write_bytes(b"same bytes")
    key = song_key(str(a))
    assert key == f"christmas-canon--{content_digest(str(a))}"
    (cache_root() / key).mkdir(parents=True)
    b = tmp_path / "04 - Totally Different Name.mp3"
    b.write_bytes(b"same bytes")
    assert song_key(str(b)) == key          # identity is the hash, first name wins


def test_song_key_keeps_resolving_a_legacy_bare_hash_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    song = tmp_path / "ghostbusters.mp3"
    song.write_bytes(b"who you gonna call")
    legacy = cache_root() / content_digest(str(song))
    legacy.mkdir(parents=True)
    assert song_key(str(song)) == legacy.name


def test_analyzer_writes_slug_name_and_reads_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(vamp_host, "check_required_plugins", lambda: None)
    song = tmp_path / "Candy Cane Lane.mp3"
    song.write_bytes(b"bytes")
    az = AudioAnalyzer(cache_dir=tmp_path / "c")
    assert az._entry(str(song)) == f"candy-cane-lane--{_content_key(str(song))[:16]}"

    (tmp_path / "c").mkdir()
    seeded = SongAnalysis(path=str(song), duration_s=1.0, sample_rate=22050, tempo_overall=99.0)
    (tmp_path / "c" / f"{_content_key(str(song))}.json").write_text(seeded.model_dump_json())
    assert az._entry(str(song)) == _content_key(str(song))
    assert az.analyze(str(song)).tempo_overall == 99.0


def test_cache_rename_retrofits_both_caches(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    songs = tmp_path / "songs"
    songs.mkdir()
    song = songs / "14 - Ghostbusters.mp3"
    song.write_bytes(b"ectoplasm")
    aroot = an.default_cache_dir()
    full = _content_key(str(song))
    (aroot / full / "stems").mkdir(parents=True)
    (aroot / f"{full}.json").write_text(json.dumps({"path": str(song)}))
    digest = content_digest(str(song))
    odir = cache_root() / digest
    odir.mkdir(parents=True)
    (odir / "revision_log.jsonl").write_text(json.dumps(
        {"song_key": digest, "review_bundle": f"{odir}/visual_review/iter0"}) + "\n")
    (cache_root() / "0123456789abcdef").mkdir()      # no matching song → left alone

    dry = cache_rename.run([songs], do_apply=False)
    assert "would rename 2 entries" in dry and "??" in dry
    assert odir.exists()                              # dry run touches nothing

    cache_rename.run([songs], do_apply=True)
    new = f"ghostbusters--{digest}"
    assert (aroot / f"ghostbusters--{full[:16]}.json").exists()
    assert (aroot / f"ghostbusters--{full[:16]}" / "stems").is_dir()
    rec = json.loads((cache_root() / new / "revision_log.jsonl").read_text())
    assert rec["song_key"] == new and f"/{new}/visual_review" in rec["review_bundle"]
    assert (cache_root() / "0123456789abcdef").exists()
    assert song_key(str(song)) == new                 # the pipeline finds the renamed dir
    assert AudioAnalyzer()._entry(str(song)) == f"ghostbusters--{full[:16]}"
    again = cache_rename.run([songs], do_apply=False)
    assert "would rename 0 entries" in again          # idempotent; only the unmatched dir remains
