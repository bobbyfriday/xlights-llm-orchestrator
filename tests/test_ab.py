"""Tests for F-H — provider A/B harness + the flat, provider-independent stage cache.

Hermetic, over the golden-test fakes (TestModel agents, a fake client + emitter, injected
analysis). The cache tests pin the flat layout (design D6): every stage artifact sits directly in
the song dir regardless of provider, and artifacts left under the former model-routing namespace
(`m-xxxxxxxx/`) are never read.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from xlights_orchestrator.pipeline import run_pipeline
from xlights_orchestrator.pipeline.cache import cache_path, cache_root, song_key
from xlights_orchestrator.show_plan import EffectInstruction, SectionEffects, ShowPlan
from xlights_core.audio import EnergyPoint, Segment, SongAnalysis


def run(coro):
    return asyncio.run(coro)


def _analysis() -> SongAnalysis:
    return SongAnalysis(path="song.mp3", duration_s=12.0, sample_rate=44100, tempo_overall=120.0,
                        key_overall="C major",
                        segments=[Segment(start=0, end=6, segment_id="A"),
                                  Segment(start=6, end=12, segment_id="B")],
                        energy_arc=[EnergyPoint(time=0, rms=0.2), EnergyPoint(time=6, rms=0.6)])


async def _interpret_stub(song_path, sa):
    from xlights_orchestrator.music_brief import LabeledSection, MusicBrief
    return MusicBrief(sections=[LabeledSection(start_ms=0, end_ms=6000, label="intro", intensity=0.3),
                                LabeledSection(start_ms=6000, end_ms=12000, label="chorus", intensity=0.8)])


def _director(plan):
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    return Agent(TestModel(custom_output_args=plan.model_dump()), output_type=ShowPlan, system_prompt="")


def _generator(sect):
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    return Agent(TestModel(custom_output_args=sect.model_dump()), output_type=SectionEffects,
                 system_prompt="")


class _FakeClient:
    def __init__(self, groups):
        self._groups = groups
    async def get_group_names(self):
        return list(self._groups)
    async def get_show_folder(self):
        raise RuntimeError("no show folder in the hermetic fixture")


def _plan():
    return ShowPlan(sections=[
        {"start_ms": 0, "end_ms": 6000, "target_groups": ["G1"], "effect_family": "On", "intensity": 0.3},
        {"start_ms": 6000, "end_ms": 12000, "target_groups": ["G2"], "effect_family": "On", "intensity": 0.8}])


def _sect():
    return SectionEffects(instructions=[EffectInstruction(
        target="G1", effect_type="On", look_id="On#0", start_ms=0, end_ms=6000)])


async def _emit(client, instructions, *, duration_secs, **kw):
    return {"placed": [], "skipped": [], "rendered": True}


def _run_once(song, groups):
    return run(run_pipeline(str(song), client=_FakeClient(groups),
                            director=_director(_plan()), generator=_generator(_sect()),
                            analyze=lambda p: _analysis(), interpret=_interpret_stub,
                            emitter=_emit, use_cache=True, stems=False, timing_tracks=False))


# -- flat cache layout (design D6) --------------------------------------------

def test_stage_artifacts_land_in_the_flat_song_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "song.mp3"; song.write_bytes(b"fake-audio-bytes")
    key = song_key(str(song))
    base = cache_root() / key

    monkeypatch.setenv("XLO_PROVIDER", "anthropic")
    _run_once(song, ["G1", "G2"])
    for stage in ("song_analysis", "song_description", "creative_brief", "instructions"):
        assert cache_path(key, stage) == base / f"{stage}.json"
        assert (base / f"{stage}.json").exists()
    assert not list(base.glob("m-*"))                         # no routing subdirs are created
    # `models=` is accepted for compatibility and ignored: same flat path either way
    assert cache_path(key, "creative_brief", models=True) == cache_path(key, "creative_brief")

    # the layout is provider-independent: another routing resolves (and reuses) the SAME files
    monkeypatch.setenv("XLO_PROVIDER", "gemini")
    assert cache_path(key, "creative_brief") == base / "creative_brief.json"
    before = (base / "creative_brief.json").read_bytes()
    _run_once(song, ["G1", "G2"])
    assert (base / "creative_brief.json").read_bytes() == before
    assert not list(base.glob("m-*"))


def test_old_namespaced_artifacts_are_never_read(tmp_path, monkeypatch):
    """A pre-change cache carries `m-xxxxxxxx/` subdirs; they must not shadow or feed a run."""
    from xlights_orchestrator.pipeline.regen import load_cached_state
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "song.mp3"; song.write_bytes(b"fake-audio-bytes")
    key = song_key(str(song))
    stale_dir = cache_root() / key / "m-deadbeef"
    stale_dir.mkdir(parents=True)
    stale_plan = ShowPlan(sections=[{"start_ms": 0, "end_ms": 12000, "target_groups": ["STALE"],
                                     "effect_family": "On", "intensity": 0.1}])
    (stale_dir / "creative_brief.json").write_text(stale_plan.model_dump_json())
    (stale_dir / "instructions.json").write_text("[]")
    (stale_dir / "song_description.json").write_text("{}")

    # only namespaced artifacts exist → regen sees no cached show at all
    with pytest.raises(FileNotFoundError):
        load_cached_state(str(song))

    # a run ignores the stale brief (the director's fresh plan wins) and writes flat files
    st = _run_once(song, ["G1", "G2"])
    assert [s.target_groups for s in st.show_plan.sections] == [["G1"], ["G2"]]
    plan = ShowPlan.model_validate_json(cache_path(key, "creative_brief").read_text())
    assert [s.target_groups for s in plan.sections] == [["G1"], ["G2"]]
    assert (stale_dir / "creative_brief.json").read_text() == stale_plan.model_dump_json()  # untouched

    # regen now rehydrates from the flat files, whatever the provider
    monkeypatch.setenv("XLO_PROVIDER", "gemini")
    _key, st2 = load_cached_state(str(song))
    assert _key == key and st2.show_plan and st2.instructions
    assert [s.target_groups for s in st2.show_plan.sections] == [["G1"], ["G2"]]


# -- arm-spec parsing ---------------------------------------------------------

def test_parse_arm_base_and_overrides():
    from xlights_orchestrator.pipeline import ab
    a = ab.parse_arm("gemini+judge=anthropic")
    assert a.provider == "gemini" and a.role_overrides == {"judge": "anthropic"}
    assert a.providers() == {"gemini", "anthropic"}
    assert ab.parse_arm("anthropic").role_overrides == {}


def test_parse_arm_rejects_unknown_role_and_provider():
    from xlights_orchestrator.pipeline import ab
    with pytest.raises(ValueError):
        ab.parse_arm("not_a_provider")
    with pytest.raises(ValueError):
        ab.parse_arm("anthropic+not_a_role=gemini")
    with pytest.raises(ValueError):
        ab.parse_arm("anthropic+judge=not_a_provider")
    with pytest.raises(ValueError):
        ab.parse_arm("anthropic+judge")           # missing =provider


# -- arm_env set/restore ------------------------------------------------------

def test_arm_env_sets_and_restores(monkeypatch):
    from xlights_orchestrator.pipeline import ab
    monkeypatch.setenv("XLO_PROVIDER", "anthropic")
    monkeypatch.delenv("XLO_PROVIDER_JUDGE", raising=False)
    arm = ab.parse_arm("gemini+judge=anthropic")
    with ab.arm_env(arm):
        assert os.environ["XLO_PROVIDER"] == "gemini"
        assert os.environ["XLO_PROVIDER_JUDGE"] == "anthropic"
    assert os.environ["XLO_PROVIDER"] == "anthropic"          # restored
    assert "XLO_PROVIDER_JUDGE" not in os.environ             # restored to absent


def test_arm_env_restores_on_exception(monkeypatch):
    from xlights_orchestrator.pipeline import ab
    monkeypatch.setenv("XLO_PROVIDER", "anthropic")
    arm = ab.parse_arm("gemini")
    try:
        with ab.arm_env(arm):
            assert os.environ["XLO_PROVIDER"] == "gemini"
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert os.environ["XLO_PROVIDER"] == "anthropic"          # restored despite the exception


def test_preflight_refuses_missing_key(monkeypatch):
    from xlights_orchestrator.pipeline import ab
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        ab.preflight_keys([ab.parse_arm("anthropic"), ab.parse_arm("gemini")])
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    ab.preflight_keys([ab.parse_arm("anthropic"), ab.parse_arm("gemini")])   # both present → OK


# -- run_ab harness (over the fakes) ------------------------------------------

def test_run_ab_interleaved_distinct_runs(tmp_path, monkeypatch):
    from xlights_orchestrator.pipeline import ab
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    song = tmp_path / "song.mp3"; song.write_bytes(b"fake-audio-bytes")

    async def _fake_run_pipeline(song_path, *, client, save_as, analyze, **kw):
        # a stub pipeline: no LLM, no xLights — just prove the harness drives it
        from xlights_orchestrator.pipeline.state import State
        st = State(song_path=song_path)
        st.song_analysis = analyze(song_path)
        st.show_plan = _plan()
        return st

    arms = [ab.parse_arm("anthropic"), ab.parse_arm("gemini")]
    manifest = run(ab.run_ab(song, arms, client=_FakeClient(["G1", "G2"]), repeat=2,
                             run_pipeline=_fake_run_pipeline, analyze=lambda p: _analysis(),
                             name_prefix="AB"))
    # 2 arms × 2 repeats = 4 runs, interleaved A,B,A,B
    assert [r["save_as"] for r in manifest] == ["AB_0_0", "AB_1_0", "AB_0_1", "AB_1_1"]
    assert [r["arm"] for r in manifest] == ["anthropic", "gemini", "anthropic", "gemini"]
    assert all(r["ok"] for r in manifest)
    # ab_runs.json written incrementally and complete
    import json as _json
    mpath = cache_root() / song_key(str(song)) / "ab_runs.json"
    assert mpath.exists() and len(_json.loads(mpath.read_text())) == 4


def test_run_ab_arm_failure_is_data_not_abort(tmp_path, monkeypatch):
    from xlights_orchestrator.pipeline import ab
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    song = tmp_path / "song.mp3"; song.write_bytes(b"fake-audio-bytes")

    async def _flaky(song_path, *, client, save_as, analyze, **kw):
        if os.environ.get("XLO_PROVIDER") == "gemini":
            raise RuntimeError("gemini emitted invalid structured output")
        from xlights_orchestrator.pipeline.state import State
        st = State(song_path=song_path); st.show_plan = _plan(); return st

    arms = [ab.parse_arm("anthropic"), ab.parse_arm("gemini")]
    manifest = run(ab.run_ab(song, arms, client=_FakeClient(["G1"]), repeat=1,
                             run_pipeline=_flaky, analyze=lambda p: _analysis(), name_prefix="AB"))
    ok = {r["arm"]: r["ok"] for r in manifest}
    assert ok["anthropic"] is True and ok["gemini"] is False   # the failure is captured, not raised
    assert any("invalid structured output" in r.get("error", "") for r in manifest if not r["ok"])


# -- summarize_runs (reuses F-G arithmetic) -----------------------------------

def test_summarize_runs_medians_ranges_and_truthful_labels():
    from xlights_orchestrator.pipeline import ab
    from xlights_orchestrator.revision_log import RevisionLogRecord

    lines = []

    def _rec(**kw):
        return RevisionLogRecord(**kw).model_dump_json()

    # arm "anthropic": two runs, final objective 88 and 92
    for run_id, final in [("a1", 88), ("a2", 92)]:
        lines.append(_rec(run_id=run_id, iteration=0, song_key="s", ts="t", objective_score=70,
                          advisory_score=60, obj_before=70, obj_after=final, obj_delta=final - 70,
                          models={"generator": "anthropic:claude-sonnet-4-6",
                                  "judge": "anthropic:claude-opus-4-8"}))
        lines.append(_rec(run_id=run_id, iteration=1, song_key="s", ts="t", kind="finalize",
                          objective_score=final, advisory_score=60, obj_after=final,
                          models={"generator": "anthropic:claude-sonnet-4-6",
                                  "judge": "anthropic:claude-opus-4-8"}))
    # a mixed arm "gemini+judge=anthropic": one run
    mixed = {"generator": "google:gemini-3.1-flash-lite", "judge": "anthropic:claude-opus-4-8"}
    lines.append(_rec(run_id="m1", iteration=0, song_key="s", ts="t", objective_score=70,
                      advisory_score=60, obj_before=70, obj_after=80, obj_delta=10, models=mixed))
    lines.append(_rec(run_id="m1", iteration=1, song_key="s", ts="t", kind="finalize",
                      objective_score=80, advisory_score=60, obj_after=80, models=mixed))

    arms = ab.summarize_runs(lines)
    # two arms: a pure-anthropic arm and a mixed arm (labeled truthfully — names both providers)
    assert "anthropic" in arms
    mixed_label = next(la for la in arms if la != "anthropic")
    assert "google" in mixed_label and "anthropic" in mixed_label      # both providers named
    assert "generator=google" in mixed_label                           # the overriding role named
    a = arms["anthropic"]
    d = a.dist(lambda r: r.final_objective)
    assert d["median"] == 90 and d["min"] == 88 and d["max"] == 92 and d["n"] == 2
    assert arms[mixed_label].runs[0].final_objective == 80
    txt = ab.render_ab_summary(arms)
    assert "median" in txt and "88" in txt
