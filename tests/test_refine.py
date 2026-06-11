"""Tests for the refine loop (hermetic — pure QA + stubbed Judge/checkpoint/regen)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xlights_orchestrator import qa
from xlights_orchestrator.pipeline.run import _refine_loop
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.qa import placement, sync, variety
from xlights_orchestrator.refine import (
    Decision,
    JudgeVerdict,
    RevisionBrief,
    replace_section,
)
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan, ShowPlan
from xlights_core.audio import Beat, EnergyPoint, Segment, SongAnalysis


def run(c):
    return asyncio.run(c)


def _ins(target, start, end, etype="On", sec=0):
    return EffectInstruction(target=target, effect_type=etype, look_id=f"{etype}#0",
                             start_ms=start, end_ms=end, section_index=sec)


def _analysis(beats_ms=(0, 1000, 2000, 3000)):
    return SongAnalysis(path="s.mp3", duration_s=4.0, sample_rate=44100,
                        beats=[Beat(time=b / 1000) for b in beats_ms],
                        segments=[Segment(start=0, end=4, segment_id="A")],
                        energy_arc=[EnergyPoint(time=0, rms=0.3)])


def _plan(n=2):
    return ShowPlan(sections=[SectionPlan(start_ms=i * 1000, end_ms=(i + 1) * 1000,
                    target_groups=["G1"], effect_family="On", intensity=0.5) for i in range(n)])


# -- pure QA ------------------------------------------------------------------

def test_sync_objective_on_vs_off_beat():
    on = [_ins("G1", 0, 500), _ins("G1", 1000, 1500)]      # on beats
    off = [_ins("G1", 433, 900), _ins("G1", 1477, 1900)]   # off beats
    s_on, f_on = sync.evaluate(on, _analysis())
    s_off, f_off = sync.evaluate(off, _analysis())
    assert s_on > s_off
    assert all(f.objective for f in f_off) and f_off


def test_sync_empty_beats_neutral():
    s, f = sync.evaluate([_ins("G1", 433, 900)], _analysis(beats_ms=()))
    assert s == 100 and f == []   # no beat reference → neutral, no gating, no error


def test_variety_advisory_monotone_and_coverage():
    mono = [_ins("G1", 0, 500), _ins("G1", 1000, 1500), _ins("G1", 2000, 2500)]
    score, findings = variety.evaluate(mono, groups=["G1", "G2", "G3", "G4"])
    assert score < 100 and all(not f.objective for f in findings)


def test_placement_per_section_attribution():
    applied = {"placed": [{"section_index": 0}], "skipped": [{"section_index": 1}]}
    score, findings = placement.evaluate(_plan(2), applied)
    # section 1 had zero placed → flagged as objective error scoped to that section
    assert any(f.scope == "section 1" and f.severity == "error" for f in findings)
    assert score == 50   # 1 of 2 sections non-empty


def test_evaluate_splits_objective_vs_advisory():
    instrs = [_ins("G1", 0, 500, sec=0), _ins("G1", 1000, 1500, sec=1)]
    applied = {"placed": [{"section_index": 0}, {"section_index": 1}], "skipped": []}
    report = qa.evaluate(instrs, _analysis(), _plan(2), applied, ["G1", "G2"])
    assert 0 <= report.objective_score <= 100 and 0 <= report.advisory_score <= 100
    assert "sync" in report.subscores and "variety" in report.subscores


# -- replace_section ----------------------------------------------------------

def test_replace_section_swaps_only_target():
    instrs = [_ins("G1", 0, 500, sec=0), _ins("G2", 1000, 1500, sec=1)]
    new = [_ins("G9", 1000, 1500, sec=1)]
    out = replace_section(instrs, 1, new)
    assert [i.target for i in out] == ["G1", "G9"]   # section 0 untouched, section 1 swapped


# -- the loop -----------------------------------------------------------------

class _FakeClient:
    def __init__(self):
        self.closed = 0
    async def close_sequence(self, *, force=False, quiet=False):
        self.closed += 1


def _state():
    st = State(song_path="s.mp3")
    st.song_analysis = _analysis()
    st.show_plan = _plan(2)
    st.available_groups = ["G1", "G2"]
    st.instructions = [_ins("G1", 0, 500, sec=0), _ins("G1", 1000, 1500, sec=1)]
    st.applied = {"placed": [{"section_index": 0}, {"section_index": 1}], "skipped": []}
    return st


class _Judge:
    def __init__(self, verdicts):
        self._v = list(verdicts)
    async def run(self, prompt):
        return SimpleNamespace(output=self._v.pop(0) if self._v else
                               JudgeVerdict(score=90, verdict="accept"))


async def _noninteractive(report, verdict, ledger):
    if verdict.verdict in ("accept", "stop"):
        return Decision(action="accept")
    return Decision(action="approve", revisions=verdict.revisions)


def test_loop_iterates_then_accepts_and_rebuilds():
    st = _state()
    client = _FakeClient()
    rebuilds = {"n": 0}
    async def emitter(c, instr, *, duration_secs):
        rebuilds["n"] += 1
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}
    async def regen(rev):
        return [_ins("G2", 1000, 1500, sec=rev.section_index, etype="Wave")]
    judge = _Judge([JudgeVerdict(score=60, verdict="iterate",
                                 revisions=[RevisionBrief(section_index=1, issue="x", suggested_fix="y")]),
                    JudgeVerdict(score=85, verdict="accept")])
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=judge, qa=None, regenerate=regen,
                     checkpoint=_noninteractive))
    assert any(i.effect_type == "Wave" for i in st.instructions)   # section 1 regenerated
    assert rebuilds["n"] >= 1 and client.closed >= 1               # rebuilt


def test_loop_terminates_independent_of_judge():
    st = _state()
    client = _FakeClient()
    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}
    async def regen(rev):
        return [_ins("G1", 1000, 1500, sec=rev.section_index)]   # no objective change → stall
    always = _Judge([JudgeVerdict(score=10, verdict="iterate",
                     revisions=[RevisionBrief(section_index=1, issue="x", suggested_fix="y")])] * 50)
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=always, qa=None, regenerate=regen,
                     checkpoint=_noninteractive))
    # a Judge that always says iterate still terminates (cap + stall) — we get here, no hang
    assert True


def test_loop_checkpoint_stop_overrides_judge():
    st = _state()
    client = _FakeClient()
    calls = {"regen": 0}
    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}
    async def regen(rev):
        calls["regen"] += 1
        return [_ins("G1", 0, 500, sec=rev.section_index)]
    async def stopper(report, verdict, ledger):
        return Decision(action="stop")
    judge = _Judge([JudgeVerdict(score=10, verdict="iterate",
                    revisions=[RevisionBrief(section_index=0, issue="x", suggested_fix="y")])])
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=judge, qa=None, regenerate=regen, checkpoint=stopper))
    assert calls["regen"] == 0   # human stop → no regeneration despite Judge 'iterate'
