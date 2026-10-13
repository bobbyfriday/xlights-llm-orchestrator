"""F-C matrix narrative Text: discovery, grounded selection, realization, idempotence, round-trip.

Hermetic — no live xLights. Builds a fake layout with a matrix model + aligned lyric lines and a
brief whose `key_moments[]` of kind 'lyric' name captions, then asserts the deterministic pass places grounded, capped,
peak-excluded, on-top Text whose settings round-trip the parser. The live "worked+rendered" half is
`editing.validate_direct` (a separate `-m live` probe).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from xlights_core.knowledge.settings import parse_settings, serialize_settings
from xlights_orchestrator.pipeline.matrix_text import (
    MATRIX_TEXT_MARKER,
    MAX_TEXT_MOMENTS,
    find_matrix,
    place_matrix_text,
    select_text_moments,
    strip_matrix_text,
)
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.show_plan import EffectInstruction, KeyMoment, ShowPlan

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


def _plan(sections, captions=()):
    """A brief whose lyric key moments name `captions` [(text, at_ms)] (at_ms only orders them)."""
    return ShowPlan(concept="c", sections=sections,
                    key_moments=[KeyMoment(at_ms=at, kind="lyric", text=t) for t, at in captions])


def _lyrics(*lines):
    return {"lines": [{"text": t, "start": s / 1000.0, "end": e / 1000.0} for t, s, e in lines]}


def test_featured_phrases_snap_to_aligned_line_and_cap_at_max():
    # six candidate moments spread across sections, each fuzzy-matching an aligned line.
    lines = [(f"line number {i}", 20000 + i * 20000, 20000 + i * 20000 + 3000) for i in range(6)]
    plan = _plan(_sections((0, 12000, 0.3), *[(20000 + i * 20000, 40000 + i * 20000, 0.4)
                                              for i in range(6)]),
                 captions=[(t, 99 + k) for k, (t, _, _) in enumerate(lines)])     # bad times
    sa = SimpleNamespace(lyrics=_lyrics(*lines))
    phrases = select_text_moments(sa, plan)
    assert len(phrases) == MAX_TEXT_MOMENTS                  # capped at 4
    # snapped to the ALIGNED line span, not the brief's (wrong) ~99 ms
    for m in phrases:
        assert (m.start_ms, m.end_ms) != (99, 100) and m.start_ms >= 20000


def test_unaligned_moment_is_dropped():
    # this caption shares no tokens with any aligned line → no match → dropped
    plan = _plan(_sections((0, 12000, 0.3), (12000, 40000, 0.4)),
                 captions=[("totally different unrelated text", 13000)])
    sa = SimpleNamespace(lyrics=_lyrics(("hello world here", 13000, 15000)))
    assert select_text_moments(sa, plan) == []


def test_peak_section_excluded_and_one_per_section():
    # section 2 (index 2) is the peak; its aligned line must not become a text moment.
    plan = _plan(_sections((0, 12000, 0.3), (12000, 40000, 0.4), (40000, 70000, 0.95)),
                 captions=[("verse line one", 13000), ("peak line two", 41000)])
    sa = SimpleNamespace(lyrics=_lyrics(("verse line one", 13000, 16000),
                                        ("peak line two", 41000, 45000)))
    got = select_text_moments(sa, plan)
    assert len(got) == 1 and got[0].section_index == 1     # the peak-section moment is excluded


def test_spacing_enforced():
    plan = _plan(_sections((0, 12000, 0.3), (12000, 60000, 0.4)),
                 captions=[("aaa bbb ccc", 13000), ("ddd eee fff", 18000)])
    sa = SimpleNamespace(lyrics=_lyrics(("aaa bbb ccc", 13000, 15000),
                                        ("ddd eee fff", 18000, 20000)))   # 5s apart < 20s
    got = select_text_moments(sa, plan)
    assert len(got) == 1                                   # second moment too close → dropped


# -- realization & wiring -----------------------------------------------------

def _state_with_matrix():
    plan = _plan(_sections((0, 12000, 0.3), (12000, 40000, 0.4)),
                 captions=[("shine the light bright", 13000)])
    sa = SimpleNamespace(lyrics=_lyrics(("shine the light bright", 13000, 17000)))
    st = State(song_path="s.mp3")
    st.song_analysis, st.show_plan = sa, plan
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
    # only the brief's aligned captions appear (grounding by construction)
    assert texts == {"shine the light bright"}


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


# -- the brief's lyric captions: key_moments[].text ----------------------------------------

def test_lyric_key_moment_text_is_the_caption_source():
    plan = _plan(_sections((0, 12000, 0.3), (12000, 40000, 0.4)))
    plan.key_moments = [KeyMoment(at_ms=13000, kind="lyric", text="shine the light bright",
                                  treatment="the title line on the matrix"),
                        KeyMoment(at_ms=13000, kind="climax", text="not a caption")]
    sa = SimpleNamespace(lyrics=_lyrics(("shine the light bright", 13000, 17000)))
    st = State(song_path="s.mp3")
    st.song_analysis, st.show_plan = sa, plan
    st.model_names = ["Arches", "Matrix", "Mega Tree"]
    out = place_matrix_text(st, "Matrix")
    assert len(out) == 1 and out[0].effect_type == "Text" and out[0].target == "Matrix"
    assert dict(parse_settings(out[0].direct_settings))["E_TEXTCTRL_Text"] == "shine the light bright"
    assert (out[0].start_ms, out[0].end_ms) == (13000, 17000)            # snapped to the aligned line
    # an unaligned lyric key moment is dropped, never shown at a guessed time
    plan.key_moments = [KeyMoment(at_ms=13000, kind="lyric", text="totally unrelated words")]
    assert place_matrix_text(st, "Matrix") == []


def test_lyric_key_moment_runs_through_the_show_assembly():
    from test_realize_from_brief import _plan as _brief_plan, _state as _brief_state
    from xlights_orchestrator.pipeline.generate import generate_instructions_from_brief
    plan = _brief_plan()
    plan.key_moments.append(KeyMoment(at_ms=2000, kind="lyric", text="hello verse line"))
    st = _brief_state(plan)
    st.song_analysis.lyrics = _lyrics(("hello verse line", 2000, 5000))
    st.model_names = ["Arches", "Matrix", "Mega Tree"]
    instrs = generate_instructions_from_brief(st)
    texts = [i for i in instrs if i.effect_type == "Text" and i.target == "Matrix"]
    assert len(texts) == 1 and texts[0].section_index == 0
    assert dict(parse_settings(texts[0].direct_settings))["E_TEXTCTRL_Text"] == "hello verse line"
