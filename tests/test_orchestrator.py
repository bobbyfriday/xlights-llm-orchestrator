"""Tests for the orchestration skeleton.

Hermetic tests use PydanticAI TestModel (no API key, no network) + fakes for the
xLights client/emitter. The live test needs an LLM key + running xLights and skips otherwise.
"""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest

from xlights_orchestrator.agents.catalog import KNOWN_REJECTED_TYPES, placeable_effect_types
from xlights_orchestrator.effect_emitter import apply_instructions
from xlights_orchestrator.models import registry
from xlights_orchestrator.music_brief import LabeledSection, MusicBrief
from xlights_orchestrator.pipeline import run_pipeline
from xlights_orchestrator.show_plan import EffectInstruction, SectionEffects, ShowPlan
from xlights_core.audio import EnergyPoint, SectionInstrumentation, Segment, SongAnalysis
from xlights_core.editing import PresetPlacementError
from xlights_core.exceptions import XLightsResponseError


def run(coro):
    return asyncio.run(coro)


def _stub_analysis() -> SongAnalysis:
    return SongAnalysis(
        path="song.mp3", duration_s=12.0, sample_rate=44100, tempo_overall=120.0,
        key_overall="C major",
        segments=[Segment(start=0, end=6, segment_id="A"), Segment(start=6, end=12, segment_id="B")],
        energy_arc=[EnergyPoint(time=0, rms=0.2), EnergyPoint(time=6, rms=0.6)],
    )


def _brief() -> MusicBrief:
    return MusicBrief(sections=[
        LabeledSection(start_ms=0, end_ms=6000, label="intro", intensity=0.3),
        LabeledSection(start_ms=6000, end_ms=12000, label="chorus", intensity=0.8)])


async def _interpret_stub(song_path, sa) -> MusicBrief:
    return _brief()


# -- registry routing (hermetic; no key) --------------------------------------

def test_registry_default_routing():
    assert registry.model_string("director") == "anthropic:claude-opus-4-8"
    assert registry.model_string("generator") == "anthropic:claude-sonnet-4-6"


def test_registry_claude_settings_thinking_no_sampling():
    s = registry._settings("director")
    dumped = s.__dict__ if hasattr(s, "__dict__") else dict(s)
    # adaptive thinking present; sampling params absent
    assert dumped.get("anthropic_thinking") == {"type": "adaptive"}
    assert "temperature" not in dumped and "top_p" not in dumped and "top_k" not in dumped


def test_registry_reroute_via_env(monkeypatch):
    monkeypatch.setenv("XLO_PROVIDER", "gemini")
    assert registry.model_string("director").startswith("google:")
    assert registry.model_string("generator").startswith("google:")


# -- catalog ------------------------------------------------------------------

def test_placeable_excludes_rejected():
    types = set(placeable_effect_types())
    assert types.isdisjoint(KNOWN_REJECTED_TYPES)            # mechanism intact
    assert "SingleStrand" in types
    assert "Color Wash" in types                            # re-verified placeable (2026-06-14)


# -- TestModel agents ---------------------------------------------------------

def _director_agent(show_plan: ShowPlan):
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    return Agent(TestModel(custom_output_args=show_plan.model_dump()),
                 output_type=ShowPlan, system_prompt="")


def _generator_agent(section_effects: SectionEffects):
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    return Agent(TestModel(custom_output_args=section_effects.model_dump()),
                 output_type=SectionEffects, system_prompt="")


class _FakeClient:
    def __init__(self, groups):
        self._groups = groups
    async def get_group_names(self):
        return list(self._groups)


def test_pipeline_flow_hermetic(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "song.mp3"; song.write_bytes(b"fake-audio-bytes")

    plan = ShowPlan(sections=[
        {"start_ms": 0, "end_ms": 6000, "target_groups": ["G1"], "effect_family": "On", "intensity": 0.3},
        {"start_ms": 6000, "end_ms": 12000, "target_groups": ["G2"], "effect_family": "On", "intensity": 0.8},
    ])
    sect = SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=6000)])

    captured = {}
    async def fake_emitter(client, instructions, *, duration_secs, **kw):
        captured["instructions"] = instructions
        captured["duration"] = duration_secs
        return {"placed": [i.model_dump() for i in instructions], "skipped": [], "rendered": True}

    st = run(run_pipeline(
        str(song), client=_FakeClient(["G1", "G2"]),
        director=_director_agent(plan), generator=_generator_agent(sect),
        analyze=lambda p: _stub_analysis(), interpret=_interpret_stub,
        emitter=fake_emitter, use_cache=False,
    ))

    assert len(st.show_plan.sections) == 2
    # one generator call per section → 2 instructions captured
    assert len(captured["instructions"]) == 2
    assert captured["duration"] == 12  # ceil(duration_s)
    assert all(i.effect_type == "On" for i in captured["instructions"])


def test_pipeline_resume_from_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "s.mp3"; song.write_bytes(b"abc")
    plan = ShowPlan(sections=[{"start_ms": 0, "end_ms": 6000, "target_groups": ["G1"],
                               "effect_family": "On", "intensity": 0.5}])
    sect = SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=6000)])

    async def emitter(client, instructions, *, duration_secs, **kw):
        return {"placed": [], "skipped": [], "rendered": True}

    common = dict(client=_FakeClient(["G1"]), analyze=lambda p: _stub_analysis(),
                  interpret=_interpret_stub, emitter=emitter)
    run(run_pipeline(str(song), director=_director_agent(plan), generator=_generator_agent(sect),
                     use_cache=True, **common))

    # second run: agents that would ERROR if called — proves cache is used
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    boom = Agent(TestModel(custom_output_args={"sections": []}), output_type=ShowPlan)
    st2 = run(run_pipeline(str(song), director=boom, generator=boom, use_cache=True, **common))
    assert len(st2.show_plan.sections) == 1  # came from cache, not the empty `boom`


# -- effect_emitter -----------------------------------------------------------

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


# -- analysis panel (hermetic; fake agents, no key/network) -------------------

from types import SimpleNamespace

from xlights_orchestrator.agents import panel as panel_mod
from xlights_orchestrator.agents import synthesizer as synth_mod
from xlights_orchestrator.music_brief import HarmonyOut, RhythmOut, StructureOut


class _StubAgent:
    def __init__(self, output):
        self._o = output
    async def run(self, prompt):
        return SimpleNamespace(output=self._o)


class _RaisingAgent:
    async def run(self, prompt):
        raise RuntimeError("analyst boom")


def _spec(key, agent):
    return panel_mod.AnalystSpec(key, agent, lambda sa, ly: "x")


def _analyst_specs():
    return [
        _spec("structure", _StubAgent(StructureOut(sections=[
            LabeledSection(start_ms=0, end_ms=6000, label="intro")], candidate_themes=["warm"]))),
        _spec("rhythm", _StubAgent(RhythmOut(groove="four-on-floor", climax_ms=6000))),
        _spec("harmony", _StubAgent(HarmonyOut(key_mood="bright"))),
    ]


def test_panel_runs_and_synthesizes():
    synth = _StubAgent(_brief())
    brief = run(panel_mod.run_panel(_stub_analysis(), None,
                                    analysts=_analyst_specs(), synthesizer=synth))
    assert isinstance(brief, MusicBrief) and len(brief.sections) == 2


def test_panel_drops_failed_analyst():
    specs = _analyst_specs() + [_spec("rhythm2", _RaisingAgent())]
    synth = _StubAgent(_brief())
    brief = run(panel_mod.run_panel(_stub_analysis(), None,
                                    analysts=specs, synthesizer=synth))
    assert isinstance(brief, MusicBrief)  # one analyst raised → dropped, panel survived


# -- I2: panel analyst retry + named drop -------------------------------------

from pydantic_ai.exceptions import ModelHTTPError


class _FlakyAgent:
    """Raises a transient ModelHTTPError on the first N runs, then returns ``output``."""
    def __init__(self, output, *, fail=1, status=529):
        self._o = output
        self._fail = fail
        self._status = status
        self.calls = 0

    async def run(self, prompt):
        self.calls += 1
        if self.calls <= self._fail:
            raise ModelHTTPError(self._status, "m")
        return SimpleNamespace(output=self._o)


class _AlwaysFlakyAgent:
    def __init__(self, status=529):
        self._status = status
        self.calls = 0

    async def run(self, prompt):
        self.calls += 1
        raise ModelHTTPError(self._status, "m")


def test_panel_analyst_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setattr("xlights_core.retry.asyncio.sleep", lambda d: _aiodone())
    flaky = _FlakyAgent(StructureOut(sections=[LabeledSection(start_ms=0, end_ms=6000, label="i")],
                                     candidate_themes=["x"]), fail=1)
    specs = [_spec("structure", flaky),
             _spec("rhythm", _StubAgent(RhythmOut(groove="g", climax_ms=1))),
             _spec("harmony", _StubAgent(HarmonyOut(key_mood="m")))]
    brief = run(panel_mod.run_panel(_stub_analysis(), None,
                                    analysts=specs, synthesizer=_StubAgent(_brief())))
    assert isinstance(brief, MusicBrief) and flaky.calls == 2   # retried once, in the brief


def test_panel_analyst_dropped_after_two_calls_names_key(monkeypatch, caplog):
    monkeypatch.setattr("xlights_core.retry.asyncio.sleep", lambda d: _aiodone())
    always = _AlwaysFlakyAgent()
    specs = [_spec("structure", _StubAgent(StructureOut(
                sections=[LabeledSection(start_ms=0, end_ms=6000, label="i")], candidate_themes=["x"]))),
             _spec("rhythm", _StubAgent(RhythmOut(groove="g", climax_ms=1))),
             _spec("harmony", always)]
    with caplog.at_level("WARNING"):
        brief = run(panel_mod.run_panel(_stub_analysis(), None,
                                        analysts=specs, synthesizer=_StubAgent(_brief())))
    assert isinstance(brief, MusicBrief)
    assert always.calls == 2                                      # exactly 2 attempts (retry once)
    assert any("harmony" in r.message for r in caplog.records)    # drop names the analyst key


def test_panel_all_fail_still_raises(monkeypatch):
    monkeypatch.setattr("xlights_core.retry.asyncio.sleep", lambda d: _aiodone())
    specs = [_spec("structure", _AlwaysFlakyAgent()),
             _spec("rhythm", _AlwaysFlakyAgent())]
    with pytest.raises(RuntimeError):
        run(panel_mod.run_panel(_stub_analysis(), None,
                                analysts=specs, synthesizer=_StubAgent(_brief())))


async def _aiodone():
    return None


def test_panel_deterministic_stem_merge():
    sa = _stub_analysis()
    sa.section_instrumentation = [
        SectionInstrumentation(segment_id="A", start_ms=0, end_ms=6000,
                               shares={"drums": 0.7}, dominant=["drums"]),
        SectionInstrumentation(segment_id="B", start_ms=6000, end_ms=12000,
                               shares={"vocals": 0.6}, dominant=["vocals"]),
    ]
    brief = run(panel_mod.run_panel(sa, None, analysts=_analyst_specs(),
                                    synthesizer=_StubAgent(_brief())))
    assert brief.sections[0].dominant_instruments == ["drums"]
    assert brief.sections[1].dominant_instruments == ["vocals"]


def test_panel_single_mode_no_synthesizer():
    brief = run(panel_mod.run_panel(_stub_analysis(), None,
                                    analysts=[_spec("musicologist", _StubAgent(_brief()))],
                                    synthesizer=None))
    assert isinstance(brief, MusicBrief) and len(brief.sections) == 2


def test_build_panel_includes_lyric_only_when_present(monkeypatch):
    monkeypatch.setattr(panel_mod, "build_agent", lambda role, **kw: object())
    monkeypatch.setattr(synth_mod, "build_agent", lambda role, **kw: object())
    with_lyrics, synth = panel_mod.build_panel(lyrics_present=True)
    without, _ = panel_mod.build_panel(lyrics_present=False)
    assert [s.key for s in with_lyrics] == ["structure", "rhythm", "harmony", "lyric"]
    assert [s.key for s in without] == ["structure", "rhythm", "harmony"]
    assert synth is not None


# -- I5: degradations integration ---------------------------------------------

def test_pipeline_clean_run_no_degradations(tmp_path, monkeypatch):
    """All fakes healthy → no degradations.json written."""
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    from xlights_orchestrator.pipeline import groups as G
    song = tmp_path / "song.mp3"; song.write_bytes(b"clean-bytes")

    plan = ShowPlan(sections=[
        {"start_ms": 0, "end_ms": 6000, "target_groups": ["G1"], "effect_family": "On", "intensity": 0.3}])
    sect = SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=6000)])

    async def emitter(client, instructions, *, duration_secs, **kw):
        return {"placed": [], "skipped": [], "rendered": True}

    # make the targetability probe succeed cleanly (no groups:probe degradation)
    async def _ok_place(client, target, effect_type, look_id, **kw):
        return "settings"
    monkeypatch.setattr(G, "place_preset", _ok_place)
    monkeypatch.setattr(G, "candidate_look_ids", lambda t: ["On#0"])
    monkeypatch.setattr(G, "_SETTLE_SECS", 0)

    class _CleanClient:
        async def get_group_names(self):
            return ["G1"]
        async def get_model_names(self):
            return ["M1"]
        async def close_sequence(self, *, force=False, quiet=False):
            pass
        async def new_sequence(self, **kw):
            pass
        async def get_show_folder(self):
            return ""                                  # empty (no folder) is not a failure here

    run(run_pipeline(str(song), client=_CleanClient(),
                     director=_director_agent(plan), generator=_generator_agent(sect),
                     analyze=lambda p: _stub_analysis(), interpret=_interpret_stub,
                     emitter=emitter, use_cache=False, stems=False))
    # (the collector is run-scoped inside asyncio.run's context) — a clean run writes NO artifact
    assert not list(tmp_path.rglob("degradations.json"))


def test_pipeline_reports_failed_show_folder(tmp_path, monkeypatch):
    """A get_show_folder failure is recorded as finalize:media and the run still completes; the
    machine-readable degradations.json is written beside the cache."""
    import json
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "song.mp3"; song.write_bytes(b"deg-bytes")

    plan = ShowPlan(sections=[
        {"start_ms": 0, "end_ms": 6000, "target_groups": ["G1"], "effect_family": "On", "intensity": 0.3}])
    sect = SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=6000)])

    async def emitter(client, instructions, *, duration_secs, **kw):
        return {"placed": [], "skipped": [], "rendered": True}

    class _NoFolderClient:
        async def get_group_names(self):
            return ["G1"]
        async def get_show_folder(self):
            raise XLightsResponseError(status_code=503, message="No show folder")

    st = run(run_pipeline(str(song), client=_NoFolderClient(),
                          director=_director_agent(plan), generator=_generator_agent(sect),
                          analyze=lambda p: _stub_analysis(), interpret=_interpret_stub,
                          emitter=emitter, use_cache=False, stems=False))
    assert st.show_plan.sections                          # run completed despite the loss
    # a degraded run wrote the machine-readable artifact beside the cache
    artifacts = list(tmp_path.rglob("degradations.json"))
    assert artifacts
    keys = {d["capability"] for d in json.loads(artifacts[0].read_text())}
    assert "finalize:media" in keys


def test_coverage_blind_warns_once(caplog):
    """The coverage sampler failing many times warns exactly once (note_once)."""
    from xlights_orchestrator import degradations
    from xlights_orchestrator.qa import coverage
    from xlights_orchestrator.music_brief import LabeledSection

    dl = degradations.start_run()
    plan = SimpleNamespace(sections=[LabeledSection(start_ms=0, end_ms=1000, label="x", intensity=0.8)])

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


# -- F-I: progress emission ---------------------------------------------------

def test_pipeline_emits_progress_sequence(tmp_path, monkeypatch):
    """A real ProgressBus receives stage brackets, one section per section, and a terminal done."""
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    from xlights_orchestrator.progress import ProgressBus
    song = tmp_path / "song.mp3"; song.write_bytes(b"prog-bytes")

    plan = ShowPlan(sections=[
        {"start_ms": 0, "end_ms": 6000, "target_groups": ["G1"], "effect_family": "On", "intensity": 0.3},
        {"start_ms": 6000, "end_ms": 12000, "target_groups": ["G2"], "effect_family": "On", "intensity": 0.8},
    ])
    sect = SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=6000)])

    async def emitter(client, instructions, *, duration_secs, **kw):
        return {"placed": [{"section_index": 0}], "skipped": [], "rendered": True}

    bus = ProgressBus()
    run(run_pipeline(str(song), client=_FakeClient(["G1", "G2"]),
                     director=_director_agent(plan), generator=_generator_agent(sect),
                     analyze=lambda p: _stub_analysis(), interpret=_interpret_stub,
                     emitter=emitter, use_cache=False, stems=False, progress=bus))
    types = [e.type for e in bus.events()]
    stages = [e.stage for e in bus.events() if e.type == "stage"]
    assert "analyze" in stages and "generate" in stages and "apply" in stages
    assert types[-1] == "done"                                  # terminal done last
    sections = [e for e in bus.events() if e.type == "section"]
    assert len(sections) == 2                                   # one per plan section


def test_pipeline_null_progress_emits_nothing(tmp_path, monkeypatch):
    """progress=None (the default) records no events — the golden path is inert."""
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    from xlights_orchestrator.progress import ProgressBus
    song = tmp_path / "song.mp3"; song.write_bytes(b"null-prog")

    plan = ShowPlan(sections=[
        {"start_ms": 0, "end_ms": 6000, "target_groups": ["G1"], "effect_family": "On", "intensity": 0.3}])
    sect = SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=6000)])

    async def emitter(client, instructions, *, duration_secs, **kw):
        return {"placed": [], "skipped": [], "rendered": True}

    # a bus we DON'T pass — proves the default NullProgressBus never touches it
    spy = ProgressBus()
    run(run_pipeline(str(song), client=_FakeClient(["G1"]),
                     director=_director_agent(plan), generator=_generator_agent(sect),
                     analyze=lambda p: _stub_analysis(), interpret=_interpret_stub,
                     emitter=emitter, use_cache=False, stems=False))     # progress omitted
    assert spy.events() == []


def test_no_browser_terminal_checkpoints_still_gate(monkeypatch):
    """Fallback: with no live gate, the terminal input() checkpoints gate exactly as today."""
    from xlights_orchestrator.pipeline.run import _interpret_review, _design_review
    # 'n' → stop; anything else → proceed (byte-for-byte the current terminal behavior)
    monkeypatch.setattr("builtins.input", lambda *a: "n")
    assert run(_interpret_review("desc", None)) is False
    assert run(_design_review("brief", None)) is False
    monkeypatch.setattr("builtins.input", lambda *a: "")
    assert run(_interpret_review("desc", None)) is True
    assert run(_design_review("brief", None)) is True


# -- lyrics (hermetic; no network) --------------------------------------------

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


# -- live end-to-end (opt-in) -------------------------------------------------

def _xlights_up() -> bool:
    try:
        httpx.get("http://127.0.0.1:49913/getVersion", timeout=2); return True
    except Exception:
        return False


@pytest.mark.live
@pytest.mark.skipif(not (os.environ.get("ANTHROPIC_API_KEY") and _xlights_up()),
                    reason="needs ANTHROPIC_API_KEY + running xLights")
def test_live_generate():
    import glob
    from xlights_core import XLightsClient
    song = sorted(glob.glob("/Users/rob/xlights/*.mp3"))[0]
    async def go():
        async with XLightsClient() as c:
            return await run_pipeline(song, client=c, save_as="LLM_ORCH_TEST", use_cache=False)
    st = run(go())
    assert st.show_plan.sections
    assert st.applied and len(st.applied["placed"]) >= 1
