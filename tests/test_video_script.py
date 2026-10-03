"""Tests for the centerpiece video script (add-matrix-video-script). Hermetic: TestModel, tmp cache."""

from __future__ import annotations

import asyncio
import json

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from xlights_orchestrator.agents.videographer import LIGHTING_FIELDS, render_input
from xlights_orchestrator.models.registry import _cfg, price_for, provider_for
from xlights_orchestrator.pipeline import cache as cache_mod
from xlights_orchestrator.pipeline.video import parse_size, run_video_script
from xlights_orchestrator.video_script import (
    Beat,
    VideographerOut,
    assign_lyrics,
    constraints_for,
    labels_by_overlap,
    lyric_lines,
    resolve_beats,
    split_long_shots,
)


def run(coro):
    return asyncio.run(coro)


SECTIONS = [(0, 10_000), (10_000, 40_000), (40_000, 52_000)]


def beat(i: int, title: str = "") -> Beat:
    return Beat(section_index=i, title=title or f"beat {i}", imagery="snow at a window",
                action="flakes drift", camera="slow push-in", lighting="deep blue",
                motifs=["window"], continuity="", draws_on="We are waiting")


def out(*idx: int) -> VideographerOut:
    return VideographerOut(logline="A vigil kept across generations.", motifs=["window", "candle"],
                           beats=[beat(i) for i in idx])


# -- timing is owned by code ---------------------------------------------------

def test_beat_spans_equal_cached_sections_and_tile():
    shots = resolve_beats(out(0, 1, 2), SECTIONS, frame_ms=50)
    assert [(s.start_ms, s.end_ms) for s in shots] == SECTIONS
    assert all(a.end_ms == b.start_ms for a, b in zip(shots, shots[1:]))
    assert shots[1].frames == 600                          # 30 s at 50 ms


def test_missing_section_inherits_previous_beat():
    shots = resolve_beats(out(0, 2), SECTIONS, frame_ms=50)
    assert shots[1].inherited and shots[1].beat.title == "beat 0"
    assert shots[1].beat.section_index == 1               # re-keyed to its own section
    assert not shots[0].inherited and not shots[2].inherited


def test_leading_gap_takes_first_available_beat():
    shots = resolve_beats(out(1, 2), SECTIONS, frame_ms=50)
    assert shots[0].inherited and shots[0].beat.title == "beat 1"


def test_out_of_range_and_duplicate_beats_dropped():
    o = out(0, 1, 2)
    o.beats += [beat(7, "bogus"), beat(1, "dup")]
    shots = resolve_beats(o, SECTIONS, frame_ms=50)
    assert len(shots) == 3
    assert shots[1].beat.title == "beat 1"               # first beat for an index wins


def test_no_usable_beats_raises():
    with pytest.raises(ValueError):
        resolve_beats(out(9), SECTIONS, frame_ms=50)


def test_lyrics_attach_to_the_beat_they_start_in():
    lyr = [(5_000, "Merry Christmas"), (12_000, "We are waiting"), (45_000, "This night we pray")]
    shots = resolve_beats(out(0, 1, 2), SECTIONS, frame_ms=50, lyrics=lyr)
    assert [s.lyrics for s in shots] == [["Merry Christmas"], ["We are waiting"], ["This night we pray"]]


def test_lyric_lines_dedupes_repeated_alignments():
    raw = [{"text": "Merry Christmas", "start": 5.26}] * 3 + [{"text": "We are waiting", "start": 30.0},
                                                              {"text": "", "start": 1.0}]
    assert lyric_lines(raw) == [(5260, "Merry Christmas"), (30000, "We are waiting")]


def test_labels_match_by_time_not_position():
    # the Director consolidates: 2 plan sections over 4 brief sections
    plan = [(0, 20_000), (20_000, 60_000)]
    brief = [{"start_ms": 0, "end_ms": 5_000, "label": "intro"},
             {"start_ms": 5_000, "end_ms": 20_000, "label": "verse"},
             {"start_ms": 20_000, "end_ms": 30_000, "label": "verse"},
             {"start_ms": 30_000, "end_ms": 60_000, "label": "chorus"}]
    assert labels_by_overlap(plan, brief) == ["verse", "chorus"]


# -- optional downbeat splitting -------------------------------------------------

DOWNBEATS = list(range(0, 60_001, 2_000))                  # a downbeat every 2 s


def test_no_split_without_a_maximum():
    shots = resolve_beats(out(0, 1, 2), SECTIONS, frame_ms=50)
    assert split_long_shots(shots, max_shot_s=None, downbeats_ms=DOWNBEATS, frame_ms=50) == shots


def test_long_shot_splits_on_downbeats_within_maximum():
    shots = resolve_beats(out(0, 1, 2), SECTIONS, frame_ms=50)
    split = split_long_shots(shots, max_shot_s=10, downbeats_ms=DOWNBEATS, frame_ms=50)
    parts = [s for s in split if s.section_index == 1]
    assert len(parts) == 3 and [p.part for p in parts] == [1, 2, 3]
    assert parts[0].start_ms == 10_000 and parts[-1].end_ms == 40_000
    assert all(a.end_ms == b.start_ms for a, b in zip(parts, parts[1:]))
    assert all(p.end_ms - p.start_ms <= 10_000 for p in parts)
    assert all(p.start_ms in DOWNBEATS for p in parts[1:])        # interior cuts on downbeats
    assert all(p.beat.title == "beat 1" for p in parts)
    assert [s.index for s in split] == list(range(len(split)))


def test_short_shots_untouched_by_split():
    shots = resolve_beats(out(0, 1, 2), SECTIONS, frame_ms=50)
    split = split_long_shots(shots, max_shot_s=15, downbeats_ms=DOWNBEATS, frame_ms=50)
    assert [s for s in split if s.section_index == 0][0].part is None
    assert [s for s in split if s.section_index == 2][0].part is None


def test_split_without_downbeats_still_tiles_within_maximum():
    shots = resolve_beats(out(0, 1, 2), SECTIONS, frame_ms=50)
    parts = [s for s in split_long_shots(shots, max_shot_s=10, downbeats_ms=[], frame_ms=50)
             if s.section_index == 1]
    assert parts[0].start_ms == 10_000 and parts[-1].end_ms == 40_000
    assert all(p.end_ms - p.start_ms <= 10_000 for p in parts)


def test_lyrics_reassigned_to_split_parts():
    lyr = [(12_000, "first"), (35_000, "last")]
    shots = resolve_beats(out(0, 1, 2), SECTIONS, frame_ms=50, lyrics=lyr)
    split = split_long_shots(shots, max_shot_s=10, downbeats_ms=DOWNBEATS, frame_ms=50)
    assign_lyrics(split, lyr)
    parts = [s for s in split if s.section_index == 1]
    assert parts[0].lyrics == ["first"] and parts[-1].lyrics == ["last"]


# -- the contract ----------------------------------------------------------------

def test_fps_is_derived_from_the_frame_interval():
    assert constraints_for(1024, 768, 50, 60_000).fps == 20
    assert constraints_for(1024, 768, 25, 60_000).fps == 40
    assert constraints_for(1024, 768, 50, 60_000).total_frames == 1200


def test_contract_terms_always_present():
    c = constraints_for(1024, 768, 50, 1_000)
    assert c.full_frame_opaque and c.no_rendered_text
    notes = " ".join(c.notes).lower()
    assert "never depict the light" in notes and "no rendered words" in notes


@pytest.mark.parametrize("text, expected", [("1024x768", (1024, 768)), ("1920X1080", (1920, 1080)),
                                             (" 640 × 480 ", (640, 480))])
def test_parse_size(text, expected):
    assert parse_size(text) == expected


@pytest.mark.parametrize("text", ["", "1024", "1024x", "0x768", "big", "1024x768x3"])
def test_parse_size_rejects_garbage(text):
    with pytest.raises(ValueError):
        parse_size(text)


# -- the agent sees the story, never the lights ----------------------------------

DESCRIPTION = {"narrative_or_journey": "A dream passed down to younger generations.",
               "candidate_themes": ["Legacy and Remembrance", "Faith and Hope"],
               "sentiment": "Pensive, reverent, hopeful", "key_mood": "Somber",
               "featured_lines": ["This dream he had each child still knows"],
               "sections": [{"start_ms": 0, "end_ms": 52_000, "label": "verse"}]}
LIGHT_SENTINEL = "ZZ-ARCHES-CHASE-ZZ"
BRIEF = {"concept": "A midnight vigil.",
         "palette": {"name": "Midnight Vigil", "colors": ["deep blue", "gold"]},
         "sections": [{"start_ms": s, "end_ms": e, "intensity": 0.5,
                       **{f: f"{LIGHT_SENTINEL} {f}" for f in LIGHTING_FIELDS}} for s, e in SECTIONS]}


def test_agent_input_carries_story_material():
    text = render_input(song="Christmas Canon", description=DESCRIPTION, brief=BRIEF,
                        sections=SECTIONS, labels=["intro", "verse", "outro"], energies=[0.3, 1.0, 0.2],
                        lyrics=[(12_000, "We are waiting")])
    for needle in ("A dream passed down", "Legacy and Remembrance", "Pensive", "Somber",
                   "This dream he had", "Midnight Vigil", "deep blue", "[1] We are waiting", "CLIMAX"):
        assert needle in text, needle


def test_agent_input_never_contains_lighting_descriptions():
    text = render_input(song="x", description=DESCRIPTION, brief=BRIEF, sections=SECTIONS,
                        labels=["", "", ""], energies=[0.1, 0.2, 0.3], lyrics=[])
    assert LIGHT_SENTINEL not in text


def test_missing_story_fields_are_marked_not_invented():
    text = render_input(song="x", description={}, brief={"sections": []}, sections=SECTIONS,
                        labels=["", "", ""], energies=[0.1, 0.2, 0.3], lyrics=[])
    assert "Narrative / journey: (not available)" in text
    assert "no aligned lyrics" in text


# -- cost and cache safety ---------------------------------------------------------

def test_videographer_role_is_priced_for_every_provider():
    spec = _cfg()["roles"]["videographer"]
    for provider, row in spec.items():
        assert price_for(row["model"]) is not None, f"{provider}: {row['model']} has no price row"


def test_videographer_does_not_change_the_cache_fingerprint(monkeypatch):
    from xlights_orchestrator.models import registry
    snap = registry.model_snapshot()
    assert "videographer" in snap
    with_role = cache_mod.models_fingerprint()
    monkeypatch.setattr(registry, "model_snapshot",
                        lambda: {r: m for r, m in snap.items() if r != "videographer"})
    assert cache_mod.models_fingerprint() == with_role


def test_role_resolves_to_a_provider():
    assert provider_for("videographer")


# -- end to end (hermetic) ---------------------------------------------------------

@pytest.fixture
def cached_song(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    song = tmp_path / "christmas canon.mp3"
    song.write_bytes(b"fake audio")
    d = cache_mod.cache_root() / cache_mod.song_key(str(song))
    d.mkdir(parents=True)
    (d / "song_analysis.json").write_text(json.dumps({
        "beats": [{"time": t / 1000, "bar_position": 1} for t in DOWNBEATS],
        "lyrics": {"title": "Christmas Canon", "artist": "TSO",
                   "lines": [{"text": "We are waiting", "start": 12.0}]}}))
    (d / "creative_brief.json").write_text(json.dumps(BRIEF))
    (d / "song_description.json").write_text(json.dumps(DESCRIPTION))
    return song, d


def _agent(o: VideographerOut) -> Agent:
    return Agent(TestModel(custom_output_args=o.model_dump()), output_type=VideographerOut)


def test_end_to_end_writes_both_forms(cached_song):
    song, d = cached_song
    md = run(run_video_script(str(song), matrix_size="1024x768", agent=_agent(out(0, 1, 2))))
    data = json.loads((d / "video_script.json").read_text())
    assert data["song"] == "Christmas Canon — TSO"
    assert data["constraints"]["width"] == 1024 and data["constraints"]["fps"] == 20
    assert [(s["start_ms"], s["end_ms"]) for s in data["shots"]] == SECTIONS
    assert data["shots"][1]["lyrics"] == ["We are waiting"]
    text = md.read_text()
    assert "A vigil kept across generations." in text and "1024×768" in text


def test_regeneration_replaces_rather_than_appends(cached_song):
    song, d = cached_song
    run(run_video_script(str(song), matrix_size="1024x768", agent=_agent(out(0, 1, 2))))
    first = (d / "video_script.md").read_text()
    run(run_video_script(str(song), matrix_size="1024x768", agent=_agent(out(0, 1, 2))))
    assert (d / "video_script.md").read_text() == first


def test_end_to_end_split(cached_song):
    song, d = cached_song
    run(run_video_script(str(song), matrix_size="1024x768", max_shot_s=10, agent=_agent(out(0, 1, 2))))
    shots = json.loads((d / "video_script.json").read_text())["shots"]
    assert max(s["end_ms"] - s["start_ms"] for s in shots) <= 10_000


@pytest.mark.parametrize("size", [None, "", "huge"])
def test_bad_size_refuses_and_writes_nothing(cached_song, size):
    song, d = cached_song
    with pytest.raises(ValueError):
        run(run_video_script(str(song), matrix_size=size, agent=_agent(out(0, 1, 2))))
    assert not (d / "video_script.json").exists() and not (d / "video_script.md").exists()


def test_missing_cache_refuses_naming_the_artifact(cached_song):
    song, d = cached_song
    (d / "song_description.json").unlink()
    with pytest.raises(FileNotFoundError, match="song_description"):
        run(run_video_script(str(song), matrix_size="1024x768", agent=_agent(out(0, 1, 2))))
    assert not (d / "video_script.json").exists()


def test_invalid_agent_output_writes_nothing(cached_song):
    song, d = cached_song
    bad = Agent(TestModel(custom_output_args={"logline": "x"}), output_type=VideographerOut)
    with pytest.raises(Exception):
        run(run_video_script(str(song), matrix_size="1024x768", agent=bad))
    assert not (d / "video_script.json").exists()


def test_cli_refuses_without_size_before_any_spend(cached_song, monkeypatch):
    from xlights_orchestrator import cli
    song, d = cached_song
    monkeypatch.setattr(cli, "has_llm_key", lambda: pytest.fail("key check reached"))
    with pytest.raises(SystemExit, match="matrix-size is required"):
        cli.main(["video-script", "--song", str(song)])
    assert not (d / "video_script.json").exists()


def test_older_cache_without_analysis_is_analyzed_once_and_persisted(cached_song, monkeypatch):
    """Older caches predate song_analysis.json: analyze the audio offline (as `xlo regen` does)."""
    import xlights_core.audio as audio_mod
    song, d = cached_song
    persisted = (d / "song_analysis.json").read_text()
    (d / "song_analysis.json").unlink()
    calls = []

    class FakeAnalysis:
        def model_dump_json(self):
            return persisted

    class FakeAnalyzer:
        def analyze(self, path):
            calls.append(path)
            return FakeAnalysis()

    monkeypatch.setattr(audio_mod, "AudioAnalyzer", FakeAnalyzer)
    run(run_video_script(str(song), matrix_size="1024x768", agent=_agent(out(0, 1, 2))))
    assert calls == [str(song)]
    assert (d / "song_analysis.json").read_text() == persisted     # persisted for next time
    run(run_video_script(str(song), matrix_size="1024x768", agent=_agent(out(0, 1, 2))))
    assert len(calls) == 1                                          # not re-analyzed
