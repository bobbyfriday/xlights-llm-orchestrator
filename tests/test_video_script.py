"""Tests for the centerpiece video script: code owns the timing (beats → shots on the brief's
section boundaries, downbeat splitting, lyrics), the contract, and the medium lint over the
written story. Hermetic. The `xlo video-plan` stage itself is covered in tests/test_cli_stages.py."""

from __future__ import annotations

import pytest

from xlights_orchestrator.pipeline.video import parse_size
from xlights_orchestrator.video_script import (
    Beat,
    Shot,
    VideographerOut,
    VideoScript,
    VideoStory,
    assign_lyrics,
    constraints_for,
    lint_media,
    lyric_lines,
    resolve_beats,
    split_long_shots,
)


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


def test_videographer_out_is_an_alias_of_video_story():
    assert VideographerOut is VideoStory


# -- the medium contract (lint over the written story) -------------------------------

def _beats(overrides: dict | None = None):
    overrides = overrides or {}
    base = {i: beat(i) for i in range(3)}
    for i, b in base.items():
        b.procedural_stand_in = "a lantern glows in falling snow"
    for i, kw in overrides.items():
        base[i] = base[i].model_copy(update=kw)
    return VideographerOut(logline="l", motifs=["lantern"], beats=list(base.values()))


def test_lint_flags_people_in_procedural_beats_only():
    media = {0: "procedural", 1: "filmed", 2: "procedural"}
    ok = _beats({1: {"imagery": "wrinkled hands pass a lantern"}})
    assert lint_media(ok, media) == []                               # hands on FILM are fine
    bad = _beats({0: {"action": "a child runs to the window"}})
    [msg] = lint_media(bad, media)
    assert "section 0" in msg and "'child'" in msg and "PROCEDURAL" in msg


def test_lint_requires_a_clean_stand_in_on_filmed_beats():
    media = {0: "procedural", 1: "filmed", 2: "procedural"}
    missing = _beats({1: {"procedural_stand_in": ""}})
    assert any("no procedural_stand_in" in m for m in lint_media(missing, media))
    dirty = _beats({1: {"procedural_stand_in": "her face in the window"}})
    assert any("'face'" in m for m in lint_media(dirty, media))
    assert lint_media(_beats({1: {"procedural_stand_in": "Lantern light on fresh snow."}}), media) == []


def test_pre_plan_script_json_still_loads():
    """A video_script.json written before media planning has no medium/asset fields."""
    old = {"song": "s", "logline": "l", "motifs": [], "constraints": constraints_for(1024, 768, 50, 1000).model_dump(),
           "shots": [{"index": 0, "section_index": 0, "start_ms": 0, "end_ms": 1000, "frames": 20,
                      "beat": {"section_index": 0, "title": "t", "imagery": "i", "action": "a",
                               "camera": "c", "lighting": "l"}}]}
    vs = VideoScript.model_validate(old)
    assert vs.media is None and vs.shots[0].medium == "filmed" and vs.shots[0].promote_rank is None
    assert isinstance(vs.shots[0], Shot)
