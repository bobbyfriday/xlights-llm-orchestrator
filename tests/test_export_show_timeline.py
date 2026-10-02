"""Show-timeline exporter: one clock for the xLights timing tracks and the video cue sheet.
Bars/sections/shots resolve on the downbeat grid, impacts are the biggest bar-line energy surges,
and the .xtiming is xLights' multi-track import format."""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from export_show_timeline import (
    bar_of,
    build_timeline,
    detect_impacts,
    downbeats_ms,
    export,
    timecode,
)
from xlights_core.audio.schema import Beat, Chord, EnergyPoint, SongAnalysis

SHOW = Path(__file__).resolve().parent.parent / "shows" / "highway-to-hell"
BEAT_S = 0.5                       # 120 bpm → 2.0 s bars; bar 1 at 1.0 s
SURGES_AT_BAR = (5, 9, 24)         # whole-mix energy steps up on these bars


def _bar_start_s(n: int) -> float:
    return 1.0 + (n - 1) * 4 * BEAT_S


def _sa(duration=208.0, labelled=True):
    beats = [Beat(time=round(1.0 + i * BEAT_S, 3), bar_position=(i % 4) + 1 if labelled else None)
             for i in range(int((duration - 1.0) / BEAT_S))]
    energy = []
    for i in range(int(duration * 10)):
        t = i / 10
        energy.append(EnergyPoint(time=t, rms=0.1 + 0.1 * sum(t >= _bar_start_s(b)
                                                                for b in SURGES_AT_BAR)))
    return SongAnalysis(path="mp3/Song.mp3", duration_s=duration, sample_rate=22050,
                        tempo_overall=120.0, key_overall="D major", beats=beats,
                        energy_arc=energy, chords=[Chord(time=1.0, label="A"),
                                                   Chord(time=3.0, label="D")])


def test_timecode_matches_frame_count():
    assert timecode(0, 30) == "00:00:00"
    assert timecode(5700, 30) == "00:05:21"          # frame 171
    assert timecode(208111, 30) == "03:28:03"        # frame 6243


def test_downbeats_use_bar_positions_else_stride():
    labelled = downbeats_ms(_sa(), 4)
    assert labelled[:3] == [1000, 3000, 5000]
    assert downbeats_ms(_sa(labelled=False), 4)[:3] == [1000, 3000, 5000]
    assert bar_of(500, labelled) is None
    assert bar_of(3000, labelled) == 2 and bar_of(4999, labelled) == 2


def test_impacts_are_the_biggest_bar_line_surges():
    sa = _sa()
    db = downbeats_ms(sa, 4)
    hits = detect_impacts(sa, db, 208000, n=3)
    assert hits == [int(_bar_start_s(b) * 1000) for b in SURGES_AT_BAR]
    assert detect_impacts(sa, db, 208000, n=16) == hits   # only positive jumps count


def test_impacts_keep_min_gap():
    sa = _sa()
    db = downbeats_ms(sa, 4)
    assert len(detect_impacts(sa, db, 208000, n=3, min_gap_bars=10)) == 2   # bar 9 is within 10 of 5


def test_sections_and_shots_resolve_on_the_grid():
    sections = [{"label": "Intro", "start_ms": 0}, {"label": "Verse", "bar": 5},
                {"label": "Chorus", "start_ms": 17200}]          # snaps to bar 9 (17000)
    shots = [{"title": "Open", "start_ms": 0}, {"title": "Go", "bar": 5}]
    tl = build_timeline(_sa(), sections, shots, fps=30, name="Song", n_impacts=3)
    assert [(s["label"], s["start_ms"]) for s in tl["sections"]] == [
        ("Intro", 0), ("Verse", 9000), ("Chorus", 17000)]
    assert tl["sections"][0]["bars"] == 4 and tl["sections"][-1]["end_ms"] == 208000
    go = tl["shots"][1]
    assert (go["bar_in"], go["section"], go["frame_in"]) == (5, "Verse", 270)
    assert go["impacts"] == [1, 2, 3]
    assert tl["impacts"][0]["shot"] == "Go"


def test_bad_bar_is_rejected():
    with pytest.raises(ValueError, match="bar 999"):
        build_timeline(_sa(), [{"label": "X", "bar": 999}], None, fps=30, name="S")


def test_export_writes_xtiming_and_cue_sheet(tmp_path):
    sections = json.loads((SHOW / "sections.json").read_text())
    shots = json.loads((SHOW / "shots.json").read_text())
    paths = export(_sa(), tmp_path, sections, shots, fps=30, name="Song")
    assert [p.name for p in paths] == ["Song.xtiming", "cue_sheet.csv", "cue_sheet.json",
                                       "video_timeline.json"]

    root = ET.parse(paths[0]).getroot()
    assert root.tag == "timings"
    names = [t.get("name") for t in root.findall("timing")]
    assert {"Sections", "Bars", "Beats", "Chords", "Impacts"} <= set(names)
    bars = root.find("timing[@name='Bars']/EffectLayer")
    assert bars[0].get("starttime") == "1000" and bars[0].get("label") == "1"

    tl = json.loads(paths[3].read_text())
    assert len(tl["shots"]) == 33 and len(tl["sections"]) == 10
    assert tl["shots"][0]["start_ms"] == 0 and tl["shots"][-1]["end_ms"] == 208000
    assert all(a["end_ms"] == b["start_ms"] for a, b in zip(tl["shots"], tl["shots"][1:]))

    rows = list(csv.DictReader(paths[1].open()))
    assert {r["type"] for r in rows} == {"Section", "Bar", "Chord", "Impact", "Shot"}
    assert rows == sorted(rows, key=lambda r: int(r["start_ms"]))
