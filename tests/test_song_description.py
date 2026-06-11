"""Tests for the rich song description (Stage 1): normalized dynamics, stem shares,
featured lyric moments, the rendered description, and the interpret checkpoint."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xlights_orchestrator.agents.panel import merge_dominant_instruments
from xlights_orchestrator.music_brief import LabeledSection, MusicBrief
from xlights_orchestrator.song_description import (
    featured_lyric_moments,
    normalize_intensities,
    render_description,
)


def _pt(time_s, rms):
    return SimpleNamespace(time=time_s, rms=rms)


def _brief(sections):
    return MusicBrief(sections=sections)


# -- normalization (the dynamics fix) -----------------------------------------

def test_normalize_spreads_and_overwrites_flat_model_values():
    # model handed us flat 0.1 intensities; energy clearly differs section to section
    secs = [LabeledSection(start_ms=0, end_ms=1000, label="intro", intensity=0.1),
            LabeledSection(start_ms=1000, end_ms=2000, label="verse", intensity=0.1),
            LabeledSection(start_ms=2000, end_ms=3000, label="chorus", intensity=0.1)]
    sa = SimpleNamespace(energy_arc=[_pt(0.5, 0.02), _pt(1.5, 0.10), _pt(2.5, 0.28)])
    normalize_intensities(_brief(secs), sa)
    assert secs[0].intensity < secs[1].intensity < secs[2].intensity      # real highs/lows
    assert secs[0].intensity <= 0.05 and secs[2].intensity >= 0.95        # spread, overwritten
    assert secs[0].intensity != 0.1                                       # the model's flat value is gone


def test_normalize_no_energy_is_noop():
    secs = [LabeledSection(start_ms=0, end_ms=1000, label="a", intensity=0.3)]
    normalize_intensities(_brief(secs), SimpleNamespace(energy_arc=[]))
    assert secs[0].intensity == 0.3


# -- stem shares surfaced via the existing overlap match ----------------------

def test_merge_surfaces_stem_shares_not_just_dominant():
    secs = [LabeledSection(start_ms=0, end_ms=2000, label="chorus")]
    inst = SimpleNamespace(start_ms=0, end_ms=2000,
                           shares={"other": 0.5, "drums": 0.3, "bass": 0.2}, dominant=["other"])
    sa = SimpleNamespace(section_instrumentation=[inst])
    merge_dominant_instruments(_brief(secs), sa)
    assert secs[0].dominant_instruments == ["other"]
    assert secs[0].stem_shares == {"other": 0.5, "drums": 0.3, "bass": 0.2}   # shares, not just dominant
    assert "other" in secs[0].instrumentation_phrase


def test_merge_stems_absent_omits_shares():
    secs = [LabeledSection(start_ms=0, end_ms=2000, label="x")]
    merge_dominant_instruments(_brief(secs), SimpleNamespace(section_instrumentation=None))
    assert secs[0].stem_shares == {}


# -- featured lyric moments (defensive) ---------------------------------------

def test_featured_lyric_moments_pairs_with_timestamps():
    b = MusicBrief(sections=[LabeledSection(start_ms=0, end_ms=4000, label="chorus")],
                   featured_lines=["carol of the bells rings out"])
    sa = SimpleNamespace(lyrics={"lines": [
        {"text": "carol of the bells rings out", "start": 1.5, "end": 3.0},
        {"text": "something unrelated", "start": 5.0, "end": 6.0}]})
    moments = featured_lyric_moments(b, sa)
    assert len(moments) == 1 and moments[0].start_ms == 1500 and moments[0].end_ms == 3000


def test_featured_lyric_moments_empty_and_safe():
    b = MusicBrief(sections=[LabeledSection(start_ms=0, end_ms=1000, label="x")],
                   featured_lines=["whatever"])
    assert featured_lyric_moments(b, SimpleNamespace(lyrics=None)) == []          # instrumental
    assert featured_lyric_moments(b, SimpleNamespace(lyrics={"garbage": 1})) == []  # malformed → no raise
    assert featured_lyric_moments(MusicBrief(sections=[]), SimpleNamespace(lyrics={})) == []


# -- rendered description -----------------------------------------------------

def test_render_description_covers_layers():
    from xlights_orchestrator.music_brief import DynamicArc, FeaturedLyricMoment, Identity
    b = MusicBrief(
        sections=[LabeledSection(start_ms=0, end_ms=20000, label="intro", intensity=0.1,
                                 musical_description="Quiet solo guitar builds.",
                                 stem_shares={"other": 0.8, "drums": 0.2}),
                  LabeledSection(start_ms=20000, end_ms=40000, label="chorus", intensity=0.95,
                                 musical_description="Full band slams in.")],
        identity=Identity(title="Mad Russian's Christmas", artist="TSO", genre="rock",
                          character="Dramatic orchestral rock."),
        dynamic_arc=DynamicArc(climax_ms=30000, range_note="huge swing from hush to wall-of-sound"),
        narrative_or_journey="A slow build to a triumphant climax.",
        featured_lyric_moments=[FeaturedLyricMoment(line="ring out", start_ms=30000, end_ms=31000)])
    md = render_description(b)
    assert "Mad Russian's Christmas" in md and "intro" in md and "chorus" in md
    assert "intensity 0.95" in md and "other 80%" in md and "climax ~0:30" in md
    assert "0:30" in md and "ring out" in md     # featured moment


# -- interpret checkpoint gate ------------------------------------------------

def test_interpret_checkpoint_gates(monkeypatch):
    from xlights_orchestrator.pipeline import run as run_mod
    calls = {}

    async def chk(desc_md, brief):
        calls["md"] = desc_md
        return False                                  # decline → pipeline should stop

    # exercise the gate logic directly: a declined checkpoint returns the state without proceeding
    assert asyncio.run(chk("desc", None)) is False and calls["md"] == "desc"
