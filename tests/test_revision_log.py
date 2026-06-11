"""Tests for the revision log (flight-recorder of the refine loop)."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from xlights_orchestrator.pipeline.run import _refine_loop
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.refine import Finding, JudgeVerdict, RevisionBrief
from xlights_orchestrator.revision_log import (
    LogFinding,
    LogRevision,
    NullRevisionLog,
    RevisionLog,
    RevisionLogRecord,
    _render_md,
    source_of,
)
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan, ShowPlan
from xlights_core.audio import Beat, EnergyPoint, Segment, SongAnalysis


def run(c):
    return asyncio.run(c)


class _MemLog:
    def __init__(self):
        self.records = []

    def write(self, record):
        self.records.append(record)


# -- unit ---------------------------------------------------------------------

def test_source_of():
    assert source_of("visual:coverage") == "visual"
    assert source_of("sync") == "sync"


def test_render_md_shows_origin_and_scores():
    rec = RevisionLogRecord(
        run_id="r1", iteration=0, song_key="k", ts="t", objective_score=78, advisory_score=60,
        findings=[LogFinding(source="visual", severity="error", scope="section 2",
                             section_index=2, detail="dark mid-chorus")],
        judge={"score": 78, "verdict": "iterate"},
        revisions=[LogRevision(section_index=2, issue="light it", origin="judge"),
                   LogRevision(section_index=1, issue="fix", origin="backstop")],
        regenerated_sections=[2, 1], obj_before=72, obj_after=78, obj_delta=6, reverted=False,
        human_decision="approve")
    md = _render_md(rec)
    assert "objective 72 → 78 (+6), kept" in md
    assert "section 2 (judge)" in md and "section 1 (backstop)" in md
    assert "[error · visual] section 2 — dark mid-chorus" in md


def test_file_writer_emits_jsonl_and_md(tmp_path):
    jl, md = tmp_path / "revision_log.jsonl", tmp_path / "revision_log.md"
    w = RevisionLog(jl, md)
    rec = RevisionLogRecord(run_id="r", iteration=0, song_key="k", ts="t",
                            objective_score=80, advisory_score=50)
    w.write(rec)
    line = jl.read_text().strip()
    assert RevisionLogRecord.model_validate_json(line).objective_score == 80   # round-trips
    assert md.read_text().strip()                                             # md written


def test_writer_failure_is_swallowed():
    class _Boom(RevisionLog):
        def __init__(self):
            pass
        def write(self, record):
            return RevisionLog.write(self, record)   # no paths set → raises internally, caught
    _Boom().write(RevisionLogRecord(run_id="r", iteration=0, song_key="k", ts="t",
                                    objective_score=1, advisory_score=1))   # must not raise


# -- loop integration ---------------------------------------------------------

def _state():
    st = State(song_path="s.mp3")
    st.song_analysis = SongAnalysis(path="s.mp3", duration_s=4.0, sample_rate=44100,
                                    beats=[Beat(time=0)], segments=[Segment(start=0, end=4, segment_id="A")],
                                    energy_arc=[EnergyPoint(time=0, rms=0.3)])
    st.show_plan = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=4000, target_groups=["G1"],
                                                  effect_family="On", intensity=0.5)])
    st.available_groups = ["G1"]
    st.instructions = [EffectInstruction(target="G1", effect_type="On", look_id="On#0",
                                         start_ms=0, end_ms=1000, section_index=0)]
    st.applied = {"placed": [{"section_index": 0}], "skipped": []}
    return st


async def _noop():
    return None


async def _accept(report, verdict, ledger):
    from xlights_orchestrator.refine import Decision
    return Decision(action="accept")


class _JudgeAccept:
    async def run(self, prompt):
        return SimpleNamespace(output=JudgeVerdict(score=92, verdict="accept"))


def test_accept_iteration_is_logged():
    """The accept/stop iteration must be recorded (it breaks before the iterate path)."""
    mem = _MemLog()

    async def regen(rev):       # injected so the loop doesn't build a real generator agent
        return []

    run(_refine_loop(_state(), client=SimpleNamespace(close_sequence=lambda **k: _noop()),
                     emitter=lambda *a, **k: _noop(), generator=None, duration_secs=4,
                     max_iterations=1, judge=_JudgeAccept(), qa=None, regenerate=regen,
                     checkpoint=_accept, visual_critique=None, revlog=mem, run_id="r",
                     song_key="k", models={"judge": "x"}, clock=lambda: "t"))
    kinds = [r.kind for r in mem.records]
    assert "iteration" in kinds and "finalize" in kinds           # accept iter + finalize both logged
    acc = next(r for r in mem.records if r.kind == "iteration")
    assert acc.human_decision == "accept" and acc.judge["verdict"] == "accept"


def test_backstop_revision_tagged_in_log():
    mem = _MemLog()

    async def visual(st):
        return [Finding(scope="section 2", severity="error", metric="visual:coverage",
                        detail="dark", objective=False, section_index=2)]

    async def regen(rev):
        return [EffectInstruction(target="G1", effect_type="On", look_id="On#0",
                                  start_ms=0, end_ms=1000)]

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": 0}], "skipped": []}

    class _JudgeNoRev:
        async def run(self, prompt):
            return SimpleNamespace(output=JudgeVerdict(score=50, verdict="iterate", revisions=[]))

    async def approve(report, verdict, ledger):
        from xlights_orchestrator.refine import Decision
        return Decision(action="approve", revisions=[])

    run(_refine_loop(_state(), client=SimpleNamespace(close_sequence=lambda **k: _noop()),
                     emitter=emitter, generator=None, duration_secs=4, max_iterations=1,
                     judge=_JudgeNoRev(), qa=None, regenerate=regen, checkpoint=approve,
                     visual_critique=visual, revlog=mem, run_id="r", song_key="k",
                     models={}, clock=lambda: "t"))
    it = next(r for r in mem.records if r.kind == "iteration")
    assert [(rv.section_index, rv.origin) for rv in it.revisions] == [(2, "backstop")]
    assert it.regenerated_sections == [2]


def test_null_log_writes_nothing(tmp_path):
    """NullRevisionLog is a no-op; refine still completes."""
    n = NullRevisionLog()
    n.write(RevisionLogRecord(run_id="r", iteration=0, song_key="k", ts="t",
                              objective_score=1, advisory_score=1))   # no error, nothing persisted
    assert not list(tmp_path.iterdir())
