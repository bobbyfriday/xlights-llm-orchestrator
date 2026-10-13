"""Tests for the shared deterministic pieces: the state guard, the catalog, the emitter, the
degradations collector, and lyric fetching. Hermetic: fakes for the xLights client, no network."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from xlights_core.editing import PresetPlacementError
from xlights_core.exceptions import XLightsResponseError
from xlights_orchestrator.effect_emitter import apply_instructions
from xlights_orchestrator.pipeline.catalog import KNOWN_REJECTED_TYPES, placeable_effect_types
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan


def run(coro):
    return asyncio.run(coro)


def test_require_returns_value_and_narrows():
    from xlights_orchestrator.pipeline.state import require
    sentinel = object()
    assert require(sentinel, "song_analysis") is sentinel          # identity on a set value
    assert require(0, "x") == 0                                     # falsy-but-present passes
    assert require("", "x") == ""


def test_require_none_raises_naming_the_field():
    from xlights_orchestrator.pipeline.state import require
    with pytest.raises(RuntimeError, match="show_plan"):
        require(None, "show_plan")


def test_placeable_excludes_rejected():
    types = set(placeable_effect_types())
    assert types.isdisjoint(KNOWN_REJECTED_TYPES)            # mechanism intact
    assert "SingleStrand" in types
    assert "Color Wash" in types                            # re-verified placeable (2026-06-14)


class _FakeWriteClient:
    def __init__(self, already_open=False):
        self.already_open = already_open
        self.rendered = False
        self.closed = False
    async def close_sequence(self, *, force=False, quiet=False):
        self.closed = True
        self.already_open = False              # quiet+force discards silently (clean slate)
    async def new_sequence(self, **kw):
        if self.already_open and not kw.get("force"):
            raise XLightsResponseError(status_code=503, message="Sequence already open.", command="newSequence")
    async def render_all(self):
        self.rendered = True


def test_emitter_auto_closes_open_sequence(monkeypatch):
    # ⑪: generation replaces an open sequence (close-first + force) instead of refusing.
    c = _FakeWriteClient(already_open=True)
    run(apply_instructions(c, [], duration_secs=10, settle_secs=0))
    assert c.closed and c.rendered           # closed the open one, then created + rendered — no raise


def test_emitter_skips_and_bumps_layer(monkeypatch):
    calls = []
    async def fake_place(client, target, effect_type, look_id, **kw):
        calls.append((target, kw.get("layer"), look_id))
        if look_id == "bad":
            raise PresetPlacementError("nope")
        return "settings"
    monkeypatch.setattr("xlights_orchestrator.effect_emitter.place_preset", fake_place)

    instrs = [
        EffectInstruction(target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=1000, layer=0),
        EffectInstruction(target="G1", effect_type="On", look_id="On#1", start_ms=0, end_ms=1000, layer=0),  # overlaps → layer 1
        EffectInstruction(target="G1", effect_type="On", look_id="bad", start_ms=2000, end_ms=3000, layer=0),  # rejected
    ]
    c = _FakeWriteClient()
    rep = run(apply_instructions(c, instrs, duration_secs=10, settle_secs=0))
    assert len(rep["placed"]) == 2 and len(rep["skipped"]) == 1
    assert calls[0][1] == 0 and calls[1][1] == 1  # second bumped to layer 1
    assert c.rendered


def test_coverage_blind_warns_once(caplog):
    """The coverage sampler failing many times warns exactly once (note_once)."""
    from xlights_orchestrator import degradations
    from xlights_orchestrator.qa import coverage

    dl = degradations.start_run()
    plan = SimpleNamespace(sections=[SectionPlan(start_ms=0, end_ms=1000, target_groups=["G"],
                                                 effect_family="On", intensity=0.8)])

    def bad_sampler(t_ms):
        raise FileNotFoundError("no .fseq")

    with caplog.at_level("WARNING"):
        for _ in range(5):
            score, findings = coverage.evaluate(plan, bad_sampler)
            assert score == 100 and findings == []        # neutral, never gates blind
    warnings = [r for r in caplog.records if "qa:coverage-blind" in r.message
                and r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert dl.items["qa:coverage-blind"].count == 5


def test_emit_view_fallback_records(monkeypatch, caplog):
    """A missing SEM Master view records emit:view and falls back to the default view."""
    from xlights_orchestrator import degradations
    dl = degradations.start_run()          # asyncio.run inherits the ContextVar's DegradationLog ref

    class _ViewFailClient:
        def __init__(self):
            self.new_calls = []
            self.rendered = False
        async def close_sequence(self, *, force=False, quiet=False):
            pass
        async def new_sequence(self, *, duration_secs, frame_ms=50, force=False, view=None,
                               media_file=None):
            self.new_calls.append(view)
            if view is not None:                          # the SEM Master view isn't loaded
                raise XLightsResponseError(status_code=503, message="unknown view")
        async def render_all(self):
            self.rendered = True

    c = _ViewFailClient()
    run(apply_instructions(c, [], duration_secs=10, settle_secs=0))
    assert c.new_calls == ["SEM Master", None]            # tried the view, fell back to default
    assert "emit:view" in {d.capability for d in dl.summary()}   # recorded on the shared collector


def test_fetch_lyrics_no_token(monkeypatch):
    monkeypatch.delenv("GENIUS_ACCESS_TOKEN", raising=False)
    from xlights_orchestrator import lyrics
    assert lyrics.fetch_lyrics("/tmp/song.mp3") is None


def test_fetch_lyrics_graceful_on_error(monkeypatch, tmp_path):
    monkeypatch.setenv("GENIUS_ACCESS_TOKEN", "x")
    from xlights_orchestrator import lyrics
    monkeypatch.setattr(lyrics, "_tags", lambda p: (None, "Some Title"))
    import lyricsgenius
    def _boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(lyricsgenius, "Genius", _boom)
    f = tmp_path / "s.mp3"; f.write_bytes(b"x")
    assert lyrics.fetch_lyrics(str(f)) is None  # degrades, no raise


def test_search_titles_strips_edition_suffixes():
    from xlights_orchestrator.lyrics import _search_titles
    assert _search_titles("Hallowed Be Thy Name (2015 Remaster)") == [
        "Hallowed Be Thy Name (2015 Remaster)", "Hallowed Be Thy Name"]
    assert _search_titles("Paint It Black - Remastered 2011")[-1] == "Paint It Black"
    assert _search_titles("Uptown Funk (Radio Edit)")[-1] == "Uptown Funk"
    assert _search_titles("Light Of Christmas [feat. Owl City]")[-1] == "Light Of Christmas"
    assert _search_titles("Carol Of The Bells") == ["Carol Of The Bells"]
    assert _search_titles("Danger Zone (From Top Gun)") == ["Danger Zone (From Top Gun)"]


def test_fetch_lyrics_retries_without_edition_suffix(monkeypatch, tmp_path):
    monkeypatch.setenv("GENIUS_ACCESS_TOKEN", "x")
    from xlights_orchestrator import lyrics
    monkeypatch.setattr(lyrics, "_tags", lambda p: ("Iron Maiden", "Hallowed Be Thy Name (2015 Remaster)"))
    searched = []

    class _Song:
        title, artist, lyrics = "Hallowed Be Thy Name", "Iron Maiden", "[Verse 1]\nI'm waiting"

    class _Genius:
        def __init__(self, *a, **k): pass
        def search_song(self, title, artist):
            searched.append(title)
            return _Song() if "Remaster" not in title else None

    import lyricsgenius
    monkeypatch.setattr(lyricsgenius, "Genius", _Genius)
    ld = lyrics.fetch_lyrics(str(tmp_path / "s.mp3"))
    assert searched == ["Hallowed Be Thy Name (2015 Remaster)", "Hallowed Be Thy Name"]
    assert ld is not None and ld.text.startswith("[Verse 1]")
