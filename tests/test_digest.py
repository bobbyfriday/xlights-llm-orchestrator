"""The analysis digest (`pipeline/digest.py`): deterministic, bounded Markdown from a cached
`SongAnalysis`, with no model call.

The instrumental case is the real cached golden analysis (`fixtures/cache_payloads/
song_analysis.json`); the vocal case is that analysis with lyric-aligner-shaped lyrics attached
(timed lines, [Verse]/[Chorus] markers, repeated lines) and the segments relabeled the way
`refine_segments_with_lyrics` would.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from xlights_core.audio import SongAnalysis
from xlights_core.audio.schema import Chord, EnergyPoint, Segment, StemFeatures
from xlights_orchestrator.pipeline.digest import (
    DIGEST_NAME,
    SIZE_BUDGET,
    render_digest,
    section_energies,
    write_digest,
)

FIXTURE = Path(__file__).parent / "fixtures" / "cache_payloads" / "song_analysis.json"


# -- fixtures -------------------------------------------------------------------------

@pytest.fixture
def instrumental() -> SongAnalysis:
    return SongAnalysis.model_validate_json(FIXTURE.read_text())


@pytest.fixture
def vocal(instrumental) -> SongAnalysis:
    sa = instrumental.model_copy(deep=True)
    sa.segments = [Segment(start=0, end=4, segment_id="intro"),
                   Segment(start=4, end=12, segment_id="Verse"),
                   Segment(start=12, end=24, segment_id="Chorus")]
    sa.chords = [Chord(time=t, label=l) for t, l in
                 ((0, "N"), (2, "C"), (6, "Am"), (8, "F"), (10, "G"),
                  (12, "C"), (14, "G"), (16, "Am"), (18, "F"), (20, "C"))]
    sa.lyrics = {
        "title": "Fixture Song", "artist": "Nobody", "text": "...", "headers_fetch": True,
        "lines": [
            {"text": "Hello darkness my old friend", "start": 4.5, "end": 6.0, "words": []},
            {"text": "I've come to talk with you again", "start": 7.0, "end": 9.5, "words": []},
            {"text": "Light it up light it up", "start": 12.2, "end": 13.8, "words": []},
            {"text": "Light it up light it up", "start": 16.2, "end": 17.8, "words": []},
            {"text": "Light it up light it up", "start": 20.2, "end": 21.8, "words": []},
        ],
        "sections": [{"label": "Verse", "start": 4.0}, {"label": "Chorus", "start": 12.0}],
        "repeated": [{"text": "light it up light it up", "times": [12.2, 16.2, 20.2]}],
    }
    return sa


# -- content ---------------------------------------------------------------------------

def test_digest_lists_sections_energies_and_lyrics(vocal):
    md = render_digest(vocal)
    # headings the conversation navigates by
    for h in ("# Analysis digest", "## Overview", "## Energy arc", "## Sections", "## Lyrics",
              "## Instrument entrances", "## Harmony", "## Mood"):
        assert h in md
    # overview facts
    assert "0:24.0" in md and "120.0 BPM" in md and "meter: 4/4" in md and "key: C major" in md
    assert "Nobody — Fixture Song" in md
    # every section: id, mm:ss.s range, normalized energy
    e = section_energies(vocal)
    assert len(e) == 3 and e[0] == 0.0 and e[-1] == 1.0 and 0.0 < e[1] < 1.0
    assert "| 0 | intro | 0:00.0–0:04.0 | 0.00 |" in md
    assert f"| 1 | Verse | 0:04.0–0:12.0 | {e[1]:.2f} |" in md
    assert "| 2 | Chorus | 0:12.0–0:24.0 | 1.00 |" in md
    # dominant stems (by overlap with section_instrumentation) and chord density
    assert "drums 60% · bass 40%" in md and "drums 70% · vocals 30%" in md
    assert "Am, F, G (3 chords" in md and "changes/min" in md
    # timed lines grouped under the section they fall in
    verse = md.split("### 1. Verse")[1].split("### 2. Chorus")[0]
    chorus = md.split("### 2. Chorus")[1].split("## Lyrics")[0]
    assert "0:04.5 Hello darkness my old friend" in verse
    assert "0:07.0 I've come to talk with you again" in verse
    assert chorus.count("Light it up light it up") == 3 and "0:12.2" in chorus
    assert "Hello darkness" not in chorus
    # repeated lines + markers + source provenance
    assert "×3 “light it up light it up” at 0:12.2, 0:16.2, 0:20.2" in md
    assert "- 0:04.0 Verse" in md and "- 0:12.0 Chorus" in md
    assert "| lyrics |" in md and "lyric markers + audio" in md


def test_instrumental_renders_and_says_so(instrumental):
    md = render_digest(instrumental)
    assert "lyrics: none" in md
    assert "_No lyrics: instrumental" in md
    assert "| 0 | A | 0:00.0–0:12.0 | 0.00 |" in md
    assert "| 1 | B | 0:12.0–0:24.0 | 1.00 |" in md
    assert "audio segmentation" in md and "| audio |" in md
    assert "- instrumental" in md


def test_instrument_entrances_listed():
    # a guitar stem quiet for 20s then loud and sustained → one entrance, with time + instrument
    arc = [EnergyPoint(time=t, rms=(0.05 if t < 20 else 0.9)) for t in range(0, 60)]
    sa = SongAnalysis(path="x.mp3", duration_s=60.0, sample_rate=44100, tempo_overall=100.0,
                      segments=[Segment(start=0, end=60, segment_id="A")],
                      stems=[StemFeatures(stem="guitar", energy_arc=arc, onsets=[20.0, 21.0])])
    md = render_digest(sa)
    # the detector's 5 s look-ahead fires a little BEFORE the step (0:18 here); the digest
    # reports whatever it says, with the instrument named
    m = re.search(r"^- 0:(\d\d)\.\d guitar surges in$", md, re.M)
    assert m and 15 <= int(m.group(1)) <= 20
    assert md.count("surges in") == 1


def test_mood_descriptors_render_when_present(vocal):
    vocal.mood = {"valence": 0.73, "arousal": 0.41, "tags": ["warm", "nostalgic"]}
    md = render_digest(vocal)
    assert "- arousal: 0.410" in md and "- valence: 0.730" in md
    assert '- tags: ["warm", "nostalgic"]' in md


# -- determinism + bounds ------------------------------------------------------------

def test_render_is_deterministic(vocal, instrumental):
    assert render_digest(vocal) == render_digest(vocal)
    assert render_digest(instrumental) == render_digest(instrumental)
    # a re-parsed copy (what a cache reload yields) renders byte-identically too
    again = SongAnalysis.model_validate_json(vocal.model_dump_json())
    assert render_digest(again) == render_digest(vocal)


def test_size_under_budget_for_a_long_vocal_song(instrumental):
    # a 5-minute song: 20 sections, 30 lines each, a dense energy arc and chord track
    sa = instrumental.model_copy(deep=True)
    sa.duration_s = 300.0
    sa.segments = [Segment(start=i * 15, end=(i + 1) * 15, segment_id=f"S{i}") for i in range(20)]
    sa.energy_arc = [EnergyPoint(time=t / 10, rms=0.2 + 0.6 * ((t % 100) / 100)) for t in range(3000)]
    sa.chords = [Chord(time=t, label=["C", "G", "Am", "F"][t % 4]) for t in range(0, 300, 2)]
    lines = [{"text": f"line {i} of the song that keeps on going and going", "start": i * 0.5,
              "end": i * 0.5 + 0.4, "words": []} for i in range(600)]
    sa.lyrics = {"text": "...", "lines": lines,
                 "sections": [{"label": "Verse" if i % 2 else "Chorus", "start": i * 15.0} for i in range(1, 20)],
                 "repeated": [{"text": f"hook {i}", "times": [i * 1.0, i * 2.0]} for i in range(40)]}
    md = render_digest(sa)
    assert len(md.encode("utf-8")) < 20 * 1024 <= SIZE_BUDGET + 1
    assert "Lyric lines capped at" in md and "… +" in md       # the cap is stated and applied
    assert render_digest(sa) == md


def test_write_digest(tmp_path, vocal):
    out = write_digest(tmp_path / "song--abc123", vocal)
    assert out == tmp_path / "song--abc123" / DIGEST_NAME
    assert out.read_text(encoding="utf-8") == render_digest(vocal)
    # the fixture on disk is JSON the schema still accepts (guards the test's premise)
    assert json.loads(FIXTURE.read_text())["duration_s"] == 24.0
