"""Tests for the visual critic agent + its (advisory) integration into the refine loop."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.test import TestModel

from xlights_orchestrator.agents import judge as judge_mod
from xlights_orchestrator.agents import visual_critic as vc
from xlights_orchestrator.pipeline.run import _refine_loop
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.refine import (
    Finding,
    JudgeVerdict,
    RevisionBrief,
    floor_visual_revisions,
)
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan, ShowPlan
from xlights_core.audio import Beat, EnergyPoint, Segment, SongAnalysis


def run(c):
    return asyncio.run(c)


# -- agent unit --------------------------------------------------------------

def test_to_findings_are_advisory():
    vf = vc.VisualFindings(summary="x", findings=[
        vc.VisualFinding(section_index=1, severity="error", aspect="coverage", detail="left dark"),
        vc.VisualFinding(section_index=None, severity="warn", aspect="motion", detail="static"),
    ])
    fs = vc.to_findings(vf)
    assert len(fs) == 2
    assert all(f.objective is False for f in fs)               # never gates the objective revert
    assert fs[0].scope == "section 1" and fs[0].metric == "visual:coverage"
    assert fs[1].scope == "global" and fs[1].metric == "visual:motion"


def test_render_input_is_multimodal():
    media = [("intro", b"\x89PNG fake", b"\x00\x00fakemp4")]
    parts = vc.render_input(media, None, SimpleNamespace(candidate_themes=["fun"], key_mood="bright",
                                                         sections=[]))
    imgs = [p for p in parts if isinstance(p, BinaryContent) and p.media_type == "image/png"]
    vids = [p for p in parts if isinstance(p, BinaryContent) and p.media_type == "video/mp4"]
    assert len(imgs) == 1 and len(vids) == 1                    # still + clip both attached


def test_render_input_includes_music_context():
    from xlights_orchestrator.music_brief import LabeledSection, MusicBrief
    brief = MusicBrief(sections=[
        LabeledSection(start_ms=0, end_ms=1000, label="intro", intensity=0.3),
        LabeledSection(start_ms=1000, end_ms=2000, label="chorus", intensity=0.9)])
    media = [("intro", b"p", None), ("chorus", b"p", None)]
    text = "".join(p for p in vc.render_input(media, None, brief) if isinstance(p, str))
    assert '"intensity": 0.9' in text and '"prev": "intro"' in text   # context aligned to media index


def test_to_findings_threads_section_index():
    vf = vc.VisualFindings(findings=[vc.VisualFinding(section_index=2, severity="error",
                                                      aspect="coverage", detail="dark")])
    f = vc.to_findings(vf)[0]
    assert f.section_index == 2 and f.objective is False        # robust targeting, advisory


def test_visual_critic_testmodel():
    out = vc.VisualFindings(summary="ok", findings=[
        vc.VisualFinding(section_index=0, severity="warn", aspect="energy", detail="flat")])
    agent = Agent(TestModel(custom_output_args=out.model_dump()), output_type=vc.VisualFindings)
    r = run(agent.run(["look", BinaryContent(data=b"x", media_type="image/png")]))
    assert r.output.findings[0].detail == "flat"


# -- loop integration: visual findings reach the Judge, advisory only --------

def _state():
    st = State(song_path="s.mp3")
    st.song_analysis = SongAnalysis(path="s.mp3", duration_s=4.0, sample_rate=44100,
                                    beats=[Beat(time=0), Beat(time=1)],
                                    segments=[Segment(start=0, end=4, segment_id="A")],
                                    energy_arc=[EnergyPoint(time=0, rms=0.3)])
    st.show_plan = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=4000, target_groups=["G1"],
                                                  effect_family="On", intensity=0.5)])
    st.available_groups = ["G1"]
    st.instructions = [EffectInstruction(target="G1", effect_type="On", look_id="On#0",
                                         start_ms=0, end_ms=1000, section_index=0)]
    st.applied = {"placed": [{"section_index": 0}], "skipped": []}
    return st


class _RecordingJudge:
    async def run(self, prompt):
        return SimpleNamespace(output=JudgeVerdict(score=90, verdict="accept"))


async def _accept(report, verdict, ledger):
    from xlights_orchestrator.refine import Decision
    return Decision(action="accept")


def test_loop_appends_visual_findings_advisory(monkeypatch):
    captured = {}
    monkeypatch.setattr(judge_mod, "render_input",
                        lambda report, *a, **k: captured.setdefault("report", report) or "x")

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": 0}], "skipped": []}

    async def visual(st):
        return [Finding(scope="section 0", severity="warn", metric="visual:coverage",
                        detail="left side dark", objective=False)]

    async def regen(rev):       # injected so the loop doesn't build a real generator agent
        return []

    st = _state()
    obj_before = __import__("xlights_orchestrator.qa", fromlist=["evaluate"]).evaluate(
        st.instructions, st.song_analysis, st.show_plan, st.applied, st.available_groups).objective_score

    run(_refine_loop(st, client=SimpleNamespace(close_sequence=lambda **k: _noop()),
                     emitter=emitter, generator=None, duration_secs=4, max_iterations=1,
                     judge=_RecordingJudge(), qa=None, regenerate=regen, checkpoint=_accept,
                     visual_critique=visual))

    rep = captured["report"]
    assert any(f.metric == "visual:coverage" and f.detail == "left side dark" for f in rep.findings)
    assert rep.objective_score == obj_before        # visual findings did NOT change the objective gate


# -- backstop: critic-confirmed visual ERROR the Judge ignored ---------------

def test_floor_visual_revisions():
    findings = [
        Finding(scope="section 2", severity="error", metric="visual:coverage",
                detail="dark mid-chorus", objective=False, section_index=2),
        Finding(scope="section 0", severity="warn", metric="visual:motion",       # warn → no floor
                detail="a bit static", objective=False, section_index=0),
        Finding(scope="section 1 / G1", severity="error", metric="placement",     # not visual → no floor
                detail="empty", objective=True, section_index=1),
    ]
    revs = floor_visual_revisions(findings, existing=[])
    assert len(revs) == 1 and revs[0].section_index == 2 and "dark mid-chorus" in revs[0].issue
    # already covered by a Judge revision → no duplicate
    assert floor_visual_revisions(
        findings, existing=[RevisionBrief(section_index=2, issue="x", suggested_fix="y")]) == []


def test_loop_backstop_floors_unaddressed_visual_error():
    captured = {"regen": []}

    async def visual(st):
        return [Finding(scope="section 2", severity="error", metric="visual:coverage",
                        detail="dark mid-chorus", objective=False, section_index=2)]

    async def regen(rev):
        captured["regen"].append((rev.section_index, rev.issue))
        return [EffectInstruction(target="G1", effect_type="On", look_id="On#0",
                                  start_ms=0, end_ms=1000)]

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": 0}], "skipped": []}

    class _JudgeNoRev:                                   # Judge produces NO revision for the error
        async def run(self, prompt):
            return SimpleNamespace(output=JudgeVerdict(score=50, verdict="iterate", revisions=[]))

    async def approve(report, verdict, ledger):
        from xlights_orchestrator.refine import Decision
        return Decision(action="approve", revisions=[])

    run(_refine_loop(_state(), client=SimpleNamespace(close_sequence=lambda **k: _noop()),
                     emitter=emitter, generator=None, duration_secs=4, max_iterations=1,
                     judge=_JudgeNoRev(), qa=None, regenerate=regen, checkpoint=approve,
                     visual_critique=visual))

    assert captured["regen"] == [(2, "dark mid-chorus")]   # backstop floored section 2 with the visual issue


async def _noop():
    return None
