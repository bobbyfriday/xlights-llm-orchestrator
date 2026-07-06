"""F-C matrix narrative Text: discovery, grounded selection, realization, idempotence, round-trip.

Hermetic — no live xLights. Builds a fake layout with a matrix model + aligned lyric lines and a
brief with featured lyric moments, then asserts the deterministic pass places grounded, capped,
peak-excluded, on-top Text whose settings round-trip the parser. The live "worked+rendered" half is
`editing.validate_direct` (a separate `-m live` probe).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from xlights_core.knowledge.settings import parse_settings, serialize_settings
from xlights_orchestrator.music_brief import (
    FeaturedLyricMoment,
    Identity,
    LabeledSection,
    MusicBrief,
)
from xlights_orchestrator.pipeline.matrix_text import (
    MATRIX_TEXT_MARKER,
    MAX_TEXT_MOMENTS,
    find_matrix,
    place_matrix_text,
    select_text_moments,
    strip_matrix_text,
)
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.show_plan import EffectInstruction, ShowPlan

FIXTURES = Path(__file__).parent / "fixtures"


# -- matrix discovery ---------------------------------------------------------

def test_find_matrix_resolves_from_fixture_models():
    models = json.loads((FIXTURES / "getModels.json").read_text())["models"]
    assert find_matrix(models) == "Matrix"                 # the real fixture layout has a Matrix


def test_find_matrix_case_insensitive_substring():
    assert find_matrix(["Panel MATRIX Left", "Arches"]) == "Panel MATRIX Left"


def test_find_matrix_none_when_absent():
    assert find_matrix(["Arches", "Mega Tree", "House Outline"]) is None
    assert find_matrix([]) is None
    assert find_matrix(None) is None


# -- selection engine ---------------------------------------------------------

def _sections(*spans):
    return [{"start_ms": a, "end_ms": b, "target_groups": ["SEM_FOCAL"],
             "effect_family": "On", "intensity": inten, "palette": ["White", "Blue"]}
            for a, b, inten in spans]


def _plan(sections):
    return ShowPlan(concept="c", sections=sections)


def _lyrics(*lines):
    return {"lines": [{"text": t, "start": s / 1000.0, "end": e / 1000.0} for t, s, e in lines]}


def _brief(title="SILENT NIGHT", artist="", moments=None):
    return MusicBrief(
        sections=[LabeledSection(start_ms=0, end_ms=1, label="x")],
        identity=Identity(title=title, artist=artist),
        featured_lyric_moments=list(moments or []))


def test_title_card_only_when_intro_long_enough_and_titled():
    plan = _plan(_sections((0, 12000, 0.3), (12000, 24000, 0.9)))
    sa = SimpleNamespace(lyrics=None)
    got = select_text_moments(_brief(title="NOEL"), sa, plan)
    assert len(got) == 1 and got[0].is_title
    assert got[0].section_index == 0 and got[0].start_ms == 0 and got[0].end_ms < 12000


def test_title_card_skipped_for_short_intro_or_empty_title():
    short = _plan(_sections((0, 5000, 0.3), (5000, 24000, 0.9)))     # intro < 8s
    assert select_text_moments(_brief(title="NOEL"), SimpleNamespace(lyrics=None), short) == []
    long_no_title = _plan(_sections((0, 12000, 0.3), (12000, 24000, 0.9)))
    assert select_text_moments(_brief(title=""), SimpleNamespace(lyrics=None), long_no_title) == []


def test_instrumental_shows_title_only():
    plan = _plan(_sections((0, 12000, 0.3), (12000, 24000, 0.9)))
    sa = SimpleNamespace(lyrics=None)     # no aligned lines
    got = select_text_moments(_brief(title="OVERTURE"), sa, plan)
    assert [m.is_title for m in got] == [True]


def test_featured_phrases_snap_to_aligned_line_and_cap_at_max():
    # six candidate moments spread across sections, each fuzzy-matching an aligned line.
    lines = [(f"line number {i}", 20000 + i * 20000, 20000 + i * 20000 + 3000) for i in range(6)]
    plan = _plan(_sections((0, 12000, 0.3), *[(20000 + i * 20000, 40000 + i * 20000, 0.4)
                                              for i in range(6)]))
    sa = SimpleNamespace(lyrics=_lyrics(*lines))
    moments = [FeaturedLyricMoment(line=t, start_ms=99, end_ms=100) for t, _, _ in lines]  # bad times
    got = select_text_moments(_brief(title="", moments=moments), sa, plan)
    phrases = [m for m in got if not m.is_title]
    assert len(phrases) == MAX_TEXT_MOMENTS                  # capped at 4
    # snapped to the ALIGNED line span, not the brief's (wrong) 99/100 ms
    for m in phrases:
        assert (m.start_ms, m.end_ms) != (99, 100) and m.start_ms >= 20000


def test_unaligned_moment_is_dropped():
    plan = _plan(_sections((0, 12000, 0.3), (12000, 40000, 0.4)))
    sa = SimpleNamespace(lyrics=_lyrics(("hello world here", 13000, 15000)))
    # this featured line shares no tokens with any aligned line → no match → dropped
    moments = [FeaturedLyricMoment(line="totally different unrelated text", start_ms=13000, end_ms=15000)]
    got = select_text_moments(_brief(title="", moments=moments), sa, plan)
    assert [m for m in got if not m.is_title] == []


def test_peak_section_excluded_and_one_per_section():
    # section 2 (index 2) is the peak; its aligned line must not become a text moment.
    plan = _plan(_sections((0, 12000, 0.3), (12000, 40000, 0.4), (40000, 70000, 0.95)))
    sa = SimpleNamespace(lyrics=_lyrics(("verse line one", 13000, 16000),
                                        ("peak line two", 41000, 45000)))
    moments = [FeaturedLyricMoment(line="verse line one", start_ms=13000, end_ms=16000),
               FeaturedLyricMoment(line="peak line two", start_ms=41000, end_ms=45000)]
    got = [m for m in select_text_moments(_brief(title="", moments=moments), sa, plan)
           if not m.is_title]
    assert len(got) == 1 and got[0].section_index == 1     # the peak-section moment is excluded


def test_spacing_enforced():
    plan = _plan(_sections((0, 12000, 0.3), (12000, 60000, 0.4)))
    sa = SimpleNamespace(lyrics=_lyrics(("aaa bbb ccc", 13000, 15000),
                                        ("ddd eee fff", 18000, 20000)))   # 5s apart < 20s
    moments = [FeaturedLyricMoment(line="aaa bbb ccc", start_ms=13000, end_ms=15000),
               FeaturedLyricMoment(line="ddd eee fff", start_ms=18000, end_ms=20000)]
    got = [m for m in select_text_moments(_brief(title="", moments=moments), sa, plan)
           if not m.is_title]
    assert len(got) == 1                                   # second moment too close → dropped


# -- realization & wiring -----------------------------------------------------

def _state_with_matrix():
    plan = _plan(_sections((0, 12000, 0.3), (12000, 40000, 0.4)))
    sa = SimpleNamespace(lyrics=_lyrics(("shine the light bright", 13000, 17000)))
    brief = _brief(title="STAR", moments=[
        FeaturedLyricMoment(line="shine the light bright", start_ms=13000, end_ms=17000)])
    st = State(song_path="s.mp3")
    st.song_analysis, st.music_brief, st.show_plan = sa, brief, plan
    st.model_names = ["Arches", "Matrix", "Mega Tree"]
    return st


def test_place_matrix_text_targets_model_on_top_max_blend():
    st = _state_with_matrix()
    out = place_matrix_text(st, "Matrix")
    assert out and all(i.target == "Matrix" and i.effect_type == "Text" for i in out)
    assert all(i.on_top for i in out)
    assert all(i.extra_settings.get("T_CHOICE_LayerMethod") == "Max" for i in out)
    assert all(i.extra_settings.get(MATRIX_TEXT_MARKER) == "1" for i in out)
    assert all(i.section_index is not None and not any(g.startswith("SEM_") for g in [i.target])
               for i in out)                               # model, never a SEM_ group
    # lightest palette color applied (White beats Blue on luminance)
    from xlights_orchestrator.pipeline.beats import _lightest_hex
    light = _lightest_hex(["White", "Blue"])
    assert any(i.palette_colors == [light] for i in out)


def test_place_matrix_text_settings_round_trip_and_grounded():
    st = _state_with_matrix()
    out = place_matrix_text(st, "Matrix")
    texts = set()
    for i in out:
        assert serialize_settings(parse_settings(i.direct_settings)) == i.direct_settings
        d = dict(parse_settings(i.direct_settings))
        texts.add(d["E_TEXTCTRL_Text"])
    # only strings from identity/featured moments appear (grounding by construction)
    assert texts <= {"STAR", "shine the light bright"}


def test_place_matrix_text_none_without_matrix():
    st = _state_with_matrix()
    assert place_matrix_text(st, None) == []


def test_place_matrix_text_dims_concurrent_matrix_background_only():
    st = _state_with_matrix()
    # a wash on the matrix concurrent with the phrase, plus a wash on another prop
    matrix_wash = EffectInstruction(target="Matrix", effect_type="On", look_id="On#0",
                                    start_ms=12000, end_ms=18000,
                                    extra_settings={"C_SLIDER_Brightness": "200"})
    other_wash = EffectInstruction(target="Arches", effect_type="On", look_id="On#0",
                                   start_ms=12000, end_ms=18000,
                                   extra_settings={"C_SLIDER_Brightness": "200"})
    st.instructions = [matrix_wash, other_wash]
    place_matrix_text(st, "Matrix")
    assert int(matrix_wash.extra_settings["C_SLIDER_Brightness"]) < 200    # dimmed under the text
    assert other_wash.extra_settings["C_SLIDER_Brightness"] == "200"       # non-matrix prop untouched


def test_place_matrix_text_refuses_under_50px():
    st = _state_with_matrix()
    st.matrix_height = 32   # below MIN_MATRIX_PX
    assert place_matrix_text(st, "Matrix") == []


# -- idempotence / regen ------------------------------------------------------

def test_strip_and_replace_is_idempotent():
    st = _state_with_matrix()
    first = place_matrix_text(st, "Matrix")
    combined = list(st.instructions) + first
    # simulate a re-run: strip prior text, place again → same count, no stacking
    stripped = strip_matrix_text(combined)
    assert not any(i.extra_settings.get(MATRIX_TEXT_MARKER) == "1" for i in stripped)
    st.instructions = stripped
    second = place_matrix_text(st, "Matrix")
    assert len(second) == len(first)
    keys1 = sorted((i.start_ms, i.end_ms, dict(parse_settings(i.direct_settings))["E_TEXTCTRL_Text"])
                   for i in first)
    keys2 = sorted((i.start_ms, i.end_ms, dict(parse_settings(i.direct_settings))["E_TEXTCTRL_Text"])
                   for i in second)
    assert keys1 == keys2                                  # exactly the same moments, once


def test_generate_pass_no_ops_without_model_names():
    """place_matrix_narrative is a clean no-op when the layout exposes no matrix model."""
    from xlights_orchestrator.pipeline.generate import place_matrix_narrative
    st = _state_with_matrix()
    st.model_names = ["Arches", "Mega Tree"]               # no matrix
    base = [EffectInstruction(target="Arches", effect_type="On", look_id="On#0",
                              start_ms=0, end_ms=1000, section_index=0)]
    out = place_matrix_narrative(st, list(base))
    assert out == base                                     # unchanged, no Text added


def test_clean_display_text_strips_time_range_keeps_parentheticals():
    from xlights_orchestrator.pipeline.matrix_text import _clean_display_text as c
    assert c("Who you gon' call? (32.96-34.36)") == "Who you gon' call?"
    assert c("Bustin' makes me feel good (168.12-170.2)") == "Bustin' makes me feel good"
    # a real lyric parenthetical (letters) is NOT a time range → left intact
    assert c("Who you gon' call? (Ghostbusters!)") == "Who you gon' call? (Ghostbusters!)"
    assert c("GHOSTBUSTERS") == "GHOSTBUSTERS"
