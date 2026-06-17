"""Targeted single-section regeneration (`xlo regen`) — hermetic, with fake generator/emitter."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from xlights_orchestrator.pipeline.cache import cache_path, song_key
from xlights_orchestrator.pipeline.generate import song_end_fade
from xlights_orchestrator.pipeline.regen import (
    list_sections,
    load_cached_state,
    regen_section,
    regenerate_into,
)
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.show_plan import (
    EffectInstruction,
    SectionEffects,
    SectionPlan,
    ShowPlan,
)
from xlights_core.audio import Beat, EnergyPoint, Segment, SongAnalysis

GROUPS = ["G1", "G2", "G3", "G4", "SEM_ALL"]


def run(c):
    return asyncio.run(c)


def _ins(target, start, end, sec, etype="On"):
    return EffectInstruction(target=target, effect_type=etype, look_id=f"{etype}#0",
                             start_ms=start, end_ms=end, section_index=sec)


def _analysis():
    # dense envelope, loud until ~5.5s → the song-end fade region is just the final tail (~[5.5s, 6s])
    return SongAnalysis(path="s.mp3", duration_s=6.0, sample_rate=44100,
                        beats=[Beat(time=b / 1000) for b in range(0, 6000, 500)],
                        segments=[Segment(start=0, end=6, segment_id="A")],
                        energy_arc=[EnergyPoint(time=t / 10, rms=0.3) for t in range(0, 61, 5)])


def _plan(n=3):
    return ShowPlan(sections=[SectionPlan(start_ms=i * 2000, end_ms=(i + 1) * 2000,
                    target_groups=["G1", "G2"], effect_family="On", intensity=0.5,
                    look=f"look {i}") for i in range(n)])


def _orig_instructions():
    return [_ins("G1", 0, 2000, 0), _ins("G2", 2000, 4000, 1), _ins("G1", 4000, 6000, 2)]


def _faded_orig():
    """The cached instructions as a real `xlo run` leaves them — song-end fade already applied."""
    st = State(song_path="s.mp3")
    st.song_analysis, st.show_plan = _analysis(), _plan(3)
    return song_end_fade(st, _orig_instructions())


def _section_effects():
    return SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=2000, end_ms=4000)])


class _FakeGen:
    def __init__(self, effects):
        self._e, self.inputs = effects, []

    async def run(self, rendered):
        self.inputs.append(rendered)
        return SimpleNamespace(output=self._e)


def _state():
    st = State(song_path="s.mp3")
    st.song_analysis = _analysis()
    st.show_plan = _plan(3)
    st.music_brief = None
    st.available_groups = list(GROUPS)
    st.instructions = _orig_instructions()
    return st


def _write_cache(tmp_path, song):
    key = song_key(str(song))
    cache_path(key, "creative_brief").parent.mkdir(parents=True, exist_ok=True)
    cache_path(key, "creative_brief").write_text(_plan(3).model_dump_json())
    cache_path(key, "instructions").write_text(
        json.dumps([i.model_dump() for i in _faded_orig()]))   # as a real run leaves them
    cache_path(key, "song_analysis").write_text(_analysis().model_dump_json())
    return key


# -- regenerate_into: isolation + pinning ------------------------------------

def test_regenerate_into_isolates_other_sections():
    st = _state()
    before0 = [i.model_dump() for i in st.instructions if i.section_index == 0]
    before2 = [i.model_dump() for i in st.instructions if i.section_index == 2]
    out = run(regenerate_into(st, 1, "", gen_agent=_FakeGen(_section_effects())))
    assert [i.model_dump() for i in out if i.section_index == 0] == before0   # byte-identical
    assert [i.model_dump() for i in out if i.section_index == 2] == before2
    assert [i for i in out if i.section_index == 1]                            # section 1 regenerated


def test_regenerate_into_pins_section_structure():
    st = _state()
    run(regenerate_into(st, 1, "", gen_agent=_FakeGen(_section_effects())))
    sec = st.show_plan.sections[1]
    assert (sec.start_ms, sec.end_ms, sec.target_groups) == (2000, 4000, ["G1", "G2"])


def test_invalid_index_rejected():
    with pytest.raises(IndexError):
        run(regenerate_into(_state(), 9, "", gen_agent=_FakeGen(_section_effects())))


def test_note_becomes_revision_brief(monkeypatch):
    captured = {}

    async def fake_regen(st, rev, *, gen_agent):
        captured["rev"] = rev
        return [_ins("G2", 2000, 4000, 1)]

    monkeypatch.setattr("xlights_orchestrator.pipeline.regen.regenerate_section", fake_regen)
    run(regenerate_into(_state(), 1, "too busy, calm it down", gen_agent=None))
    rev = captured["rev"]
    assert rev.section_index == 1
    assert "calm it down" in rev.issue
    assert rev.suggested_fix == "too busy, calm it down"


# -- listing + cache guards --------------------------------------------------

def test_list_sections_and_missing_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "song.mp3"
    song.write_bytes(b"abc")
    with pytest.raises(FileNotFoundError):
        list_sections(str(song))
    with pytest.raises(FileNotFoundError):
        load_cached_state(str(song))
    _write_cache(tmp_path, song)
    rows = list_sections(str(song))
    assert len(rows) == 3 and rows[0] == (0, "look 0", 0, 2000)
    _key, st = load_cached_state(str(song))
    assert len(st.show_plan.sections) == 3 and len(st.instructions) == 3


# -- regen_section end-to-end ------------------------------------------------

def test_regen_section_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "song.mp3"
    song.write_bytes(b"abc")
    key = _write_cache(tmp_path, song)

    async def fake_tg(client, *, cache_root):
        return list(GROUPS)

    monkeypatch.setattr("xlights_orchestrator.pipeline.regen.targetable_groups", fake_tg)

    emitted = {}

    async def fake_emitter(client, instructions, *, duration_secs, **kw):
        emitted["instructions"] = list(instructions)
        emitted["duration"] = duration_secs
        return {"placed": [i.model_dump() for i in instructions], "skipped": []}

    st = run(regen_section(str(song), client=object(), section_index=1, note="calmer",
                           save_as=None, generator=_FakeGen(_section_effects()),
                           emitter=fake_emitter))

    faded = _faded_orig()                                                 # the cached (already-faded) baseline
    assert [i.model_dump() for i in st.instructions if i.section_index == 0] == [faded[0].model_dump()]
    assert [i.model_dump() for i in st.instructions if i.section_index == 2] == [faded[2].model_dump()]
    assert emitted["instructions"] and emitted["duration"] == 6           # re-emitted the spliced list
    persisted = json.loads(cache_path(key, "instructions").read_text())
    assert any(x["section_index"] == 1 for x in persisted)                # cache updated in place
    assert {x["section_index"] for x in persisted} == {0, 1, 2}           # other sections preserved


def test_regen_final_section_keeps_tail_fade(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "song.mp3"
    song.write_bytes(b"abc")
    _write_cache(tmp_path, song)

    async def fake_tg(client, *, cache_root):
        return list(GROUPS)

    async def fake_emitter(client, instructions, *, duration_secs, **kw):
        return {"placed": [], "skipped": []}

    monkeypatch.setattr("xlights_orchestrator.pipeline.regen.targetable_groups", fake_tg)

    # the generator returns a fresh final-section effect spanning to the section/file end (no fade)
    final_fx = SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=4000, end_ms=6000)])
    st = run(regen_section(str(song), client=object(), section_index=2, note="",
                           save_as=None, generator=_FakeGen(final_fx), emitter=fake_emitter))

    sec2 = [i for i in st.instructions if i.section_index == 2]
    assert sec2, "final section regenerated"
    assert any("T_TEXTCTRL_Fadeout" in i.extra_settings for i in sec2), \
        "the song-end tail fade is re-applied after regenerating the final section"
