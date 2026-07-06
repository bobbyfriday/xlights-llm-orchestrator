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
    QAReport,
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


# -- I2: judge / visual-critique retry inside the loop ------------------------

def test_judge_529_once_completes_iteration(monkeypatch):
    monkeypatch.setattr("xlights_core.retry.asyncio.sleep", lambda d: _aiodone())
    from pydantic_ai.exceptions import ModelHTTPError
    st = _state()
    client = _FakeClient()

    class _FlakyJudge:
        def __init__(self):
            self.calls = 0
        async def run(self, prompt):
            self.calls += 1
            if self.calls == 1:
                raise ModelHTTPError(529, "m")         # first run overloaded → retried
            return SimpleNamespace(output=JudgeVerdict(score=90, verdict="accept"))

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}
    async def regen(rev):
        return [_ins("G1", 0, 500, sec=rev.section_index)]

    jf = _FlakyJudge()
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=2, judge=jf, qa=None, regenerate=regen,
                     checkpoint=_noninteractive))
    assert jf.calls == 2                               # retried once, then produced its verdict


def test_visual_critique_failing_twice_skips_findings_loop_continues(monkeypatch):
    monkeypatch.setattr("xlights_core.retry.asyncio.sleep", lambda d: _aiodone())
    st = _state()
    client = _FakeClient()
    vc_calls = {"n": 0}

    async def failing_critique(state):
        vc_calls["n"] += 1
        raise RuntimeError("critic boom")              # best-effort → swallowed, loop continues

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}
    async def regen(rev):
        return [_ins("G1", 0, 500, sec=rev.section_index)]
    judge = _Judge([JudgeVerdict(score=90, verdict="accept")])

    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=2, judge=judge, qa=None, regenerate=regen,
                     checkpoint=_noninteractive, visual_critique=failing_critique))
    assert vc_calls["n"] >= 1                           # attempted; failure didn't sink the loop


async def _aiodone():
    return None


def test_refine_emits_score_and_refine_events():
    """A real ProgressBus gets a score + refine event per recorded iteration; the refine payload
    mirrors the RevisionLogRecord fields (one construction site)."""
    from xlights_orchestrator.progress import ProgressBus
    st = _state()
    client = _FakeClient()

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}
    async def regen(rev):
        return [_ins("G2", 1000, 1500, sec=rev.section_index, etype="Wave")]
    judge = _Judge([JudgeVerdict(score=60, verdict="iterate",
                                 revisions=[RevisionBrief(section_index=1, issue="x", suggested_fix="y")]),
                    JudgeVerdict(score=85, verdict="accept")])
    bus = ProgressBus()
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=judge, qa=None, regenerate=regen,
                     checkpoint=_noninteractive, progress=bus))
    evs = bus.events()
    scores = [e for e in evs if e.type == "score"]
    refines = [e for e in evs if e.type == "refine"]
    assert scores and refines and len(scores) == len(refines)   # paired, one per record
    assert any(e.payload.get("kind") == "finalize" for e in refines)  # final record emitted
    assert evs[-1].type in ("score", "refine")                  # last record's events land


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


def test_loop_stops_on_plateau():
    st = _state()
    client = _FakeClient()
    calls = {"judge": 0, "regen": 0}
    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}
    async def regen(rev):
        calls["regen"] += 1
        return [_ins("G1", 1000, 1500, sec=rev.section_index)]

    class _SameJudge:                          # re-flags the SAME section/issue every iteration
        async def run(self, prompt):
            calls["judge"] += 1
            return SimpleNamespace(output=JudgeVerdict(
                score=80, verdict="iterate",
                revisions=[RevisionBrief(section_index=1, issue="same issue", suggested_fix="y")]))

    def qa_same(instructions, analysis, plan, applied, groups):
        return QAReport(objective_score=92, advisory_score=70)   # 92→92→… plateau
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=5, judge=_SameJudge(), qa=qa_same, regenerate=regen,
                     checkpoint=_noninteractive))                # checkpoint APPROVES — would continue
    # iteration 2 sees the identical (objective, advisory, revisions) signature → stops cold
    assert calls["judge"] == 2 and calls["regen"] == 1


def test_loop_no_plateau_stop_while_scores_move():
    st = _state()
    client = _FakeClient()
    calls = {"judge": 0}
    scores = iter([60, 60, 70, 70, 80, 80, 90, 90])   # report+post-apply pairs per iteration
    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}
    async def regen(rev):
        return [_ins("G1", 1000, 1500, sec=rev.section_index)]

    class _SameJudge:
        async def run(self, prompt):
            calls["judge"] += 1
            return SimpleNamespace(output=JudgeVerdict(
                score=80, verdict="iterate",
                revisions=[RevisionBrief(section_index=1, issue="same issue", suggested_fix="y")]))

    def qa_moving(instructions, analysis, plan, applied, groups):
        return QAReport(objective_score=next(scores, 90), advisory_score=50)
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=_SameJudge(), qa=qa_moving, regenerate=regen,
                     checkpoint=_noninteractive))
    assert calls["judge"] == 3                 # objective still moving → all iterations run


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


def test_variety_rewards_distinct_effect_types():
    from xlights_orchestrator.show_plan import EffectInstruction
    def ins(t, ms):
        return EffectInstruction(target="G1", effect_type=t, look_id=f"{t}#0",
                                 start_ms=ms, end_ms=ms + 400)
    groups = ["G1", "G2", "G3", "G4"]
    # a broad palette of distinct types scores higher than a samey one of the same size
    broad = [ins(t, i * 500) for i, t in enumerate(
        ["SingleStrand", "Bars", "Garlands", "Wave", "On", "Twinkle"])]
    samey = [ins("On", i * 500) for i in range(6)]
    s_broad, f_broad = variety.evaluate(broad, groups)
    s_samey, f_samey = variety.evaluate(samey, groups)
    assert s_broad > s_samey
    assert any("distinct effect types" in f.detail for f in f_samey)   # surfaced to the Judge
    assert not any("distinct effect types" in f.detail for f in f_broad)


# -- high-objective skip gate -------------------------------------------------

def test_loop_skips_judging_when_first_pass_objective_high():
    st = _state()
    client = _FakeClient()
    calls = {"judge": 0, "regen": 0}

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}

    async def regen(rev):
        calls["regen"] += 1
        return [_ins("G1", 1000, 1500, sec=rev.section_index)]

    class _CountJudge:
        async def run(self, prompt):
            calls["judge"] += 1
            return SimpleNamespace(output=JudgeVerdict(
                score=50, verdict="iterate",
                revisions=[RevisionBrief(section_index=1, issue="x", suggested_fix="y")]))

    def qa_high(instructions, analysis, plan, applied, groups):
        return QAReport(objective_score=95, advisory_score=80)

    before = [i.model_dump() for i in st.instructions]
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=_CountJudge(), qa=qa_high, regenerate=regen,
                     checkpoint=_noninteractive, skip_objective=88))
    # already-good first pass → no Judge, no regeneration, draft untouched
    assert calls["judge"] == 0 and calls["regen"] == 0
    assert [i.model_dump() for i in st.instructions] == before


def test_loop_iterates_when_first_pass_below_threshold():
    st = _state()
    client = _FakeClient()
    calls = {"judge": 0, "regen": 0}

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}

    async def regen(rev):
        calls["regen"] += 1
        return [_ins("G2", 1000, 1500, sec=rev.section_index, etype="Wave")]

    class _CountJudge:
        async def run(self, prompt):
            calls["judge"] += 1
            return SimpleNamespace(output=JudgeVerdict(
                score=60, verdict="accept" if calls["judge"] > 1 else "iterate",
                revisions=[RevisionBrief(section_index=1, issue="x", suggested_fix="y")]))

    def qa_low(instructions, analysis, plan, applied, groups):
        return QAReport(objective_score=70, advisory_score=80)   # below the 88 gate

    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=_CountJudge(), qa=qa_low, regenerate=regen,
                     checkpoint=_noninteractive, skip_objective=88))
    assert calls["judge"] >= 1 and calls["regen"] >= 1            # gate didn't fire → normal refine
    assert any(i.effect_type == "Wave" for i in st.instructions)


def test_loop_default_skip_off_preserves_behavior():
    # skip_objective defaults to None → a high objective still enters the loop (back-compat)
    st = _state()
    client = _FakeClient()
    calls = {"judge": 0}

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}

    async def regen(rev):
        return [_ins("G1", 1000, 1500, sec=rev.section_index)]

    class _CountJudge:
        async def run(self, prompt):
            calls["judge"] += 1
            return SimpleNamespace(output=JudgeVerdict(score=99, verdict="accept"))

    def qa_high(instructions, analysis, plan, applied, groups):
        return QAReport(objective_score=95, advisory_score=80)

    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=_CountJudge(), qa=qa_high, regenerate=regen,
                     checkpoint=_noninteractive))   # no skip_objective passed
    assert calls["judge"] == 1                       # entered the loop, judged, then accepted


def test_skip_writes_finalize_record():
    st = _state()
    client = _FakeClient()

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}

    class _CaptureLog:
        def __init__(self):
            self.records = []

        def write(self, rec):
            self.records.append(rec)

    async def regen(rev):                       # never called on the skip path; present so the
        return []                               # loop doesn't build a real generator agent

    def qa_high(instructions, analysis, plan, applied, groups):
        return QAReport(objective_score=92, advisory_score=80)

    log = _CaptureLog()
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=_Judge([]), qa=qa_high, regenerate=regen,
                     checkpoint=_noninteractive, revlog=log, skip_objective=88))
    assert len(log.records) == 1
    rec = log.records[0]
    assert rec.kind == "finalize" and rec.human_decision == "skip-high-objective"
    assert rec.obj_after == 92


def test_refine_skip_objective_env(monkeypatch):
    from xlights_orchestrator.pipeline.run import REFINE_SKIP_OBJECTIVE, _refine_skip_objective
    monkeypatch.delenv("XLO_REFINE_SKIP_OBJECTIVE", raising=False)
    assert _refine_skip_objective() == REFINE_SKIP_OBJECTIVE
    monkeypatch.setenv("XLO_REFINE_SKIP_OBJECTIVE", "95")
    assert _refine_skip_objective() == 95
    monkeypatch.setenv("XLO_REFINE_SKIP_OBJECTIVE", "not-a-number")
    assert _refine_skip_objective() == REFINE_SKIP_OBJECTIVE   # invalid → fall back
    monkeypatch.setenv("XLO_REFINE_SKIP_OBJECTIVE", "101")
    assert _refine_skip_objective() == 101                     # disables the gate


# -- I1: telemetry threaded into the revision log -----------------------------

def _usage_res(output, **toks):
    from pydantic_ai.usage import RunUsage
    return SimpleNamespace(output=output, usage=RunUsage(requests=1, **toks))


def test_loop_usage_total_sums_and_deltas_partition():
    """The finalize usage_total equals the whole-run sum; per-iteration deltas partition it."""
    from xlights_orchestrator import telemetry
    st = _state()
    client = _FakeClient()
    records = []

    class _CaptureLog:
        def write(self, rec):
            records.append(rec)

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}

    async def regen(rev):
        return [_ins("G2", 1000, 1500, sec=rev.section_index, etype="Wave")]

    class _JudgeWithUsage:
        def __init__(self):
            self.n = 0
        async def run(self, prompt):
            self.n += 1
            v = (JudgeVerdict(score=60, verdict="iterate",
                              revisions=[RevisionBrief(section_index=1, issue="x", suggested_fix="y")])
                 if self.n == 1 else JudgeVerdict(score=90, verdict="accept"))
            return _usage_res(v, input_tokens=100, output_tokens=10)  # 100/10 per judge call

    telemetry.start_run()
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=3, judge=_JudgeWithUsage(), qa=None, regenerate=regen,
                     checkpoint=_noninteractive, revlog=_CaptureLog(),
                     models={"judge": "anthropic:claude-opus-4-8"}))
    fin = next(r for r in records if r.kind == "finalize")
    # two judge calls captured → run total 200 in / 20 out
    assert fin.usage_total["judge"].input_tokens == 200
    assert fin.usage_total["judge"].output_tokens == 20
    # per-iteration deltas partition the total exactly
    delta_in = sum(r.usage.get("judge").input_tokens for r in records if r.usage.get("judge"))
    assert delta_in == fin.usage_total["judge"].input_tokens
    # cost derived from real Opus rates: 200*5 + 20*25 = 1500 (per 1e6) = 0.0015
    assert fin.cost_usd == (200 * 5.0 + 20 * 25.0) / 1_000_000


def test_loop_cost_unknown_when_model_unpriced():
    from xlights_orchestrator import telemetry
    st = _state()
    client = _FakeClient()
    records = []

    class _CaptureLog:
        def write(self, rec):
            records.append(rec)

    async def emitter(c, instr, *, duration_secs):
        return {"placed": [{"section_index": i.section_index} for i in instr], "skipped": []}

    async def regen(rev):
        return []

    class _JudgeAcceptUsage:
        async def run(self, prompt):
            return _usage_res(JudgeVerdict(score=90, verdict="accept"),
                              input_tokens=50, output_tokens=5)

    telemetry.start_run()
    run(_refine_loop(st, client=client, emitter=emitter, generator=None, duration_secs=4,
                     max_iterations=1, judge=_JudgeAcceptUsage(), qa=None, regenerate=regen,
                     checkpoint=_noninteractive, revlog=_CaptureLog(),
                     models={"judge": "google:gemini-nonexistent-model"}))  # unpriced (unlisted id)
    fin = next(r for r in records if r.kind == "finalize")
    assert fin.usage_total["judge"].input_tokens == 50
    assert fin.cost_usd is None                        # unpriced ⇒ unknown, never zero


def test_estimate_cost_units():
    from xlights_orchestrator.models import registry
    from xlights_orchestrator.telemetry import RoleUsage
    # 142k in / 31k out on sonnet-4-6 ⇒ $0.891
    u = {"generator": RoleUsage(input_tokens=142000, output_tokens=31000)}
    assert registry.estimate_cost({"generator": "anthropic:claude-sonnet-4-6"}, u) == 0.891
    # unpriced model (id not in the table) ⇒ None
    assert registry.estimate_cost({"generator": "google:gemini-nonexistent-model"}, u) is None
    # zero usage ⇒ 0.0 (genuinely zero, not unknown)
    assert registry.estimate_cost({"g": "anthropic:claude-opus-4-8"}, {"g": RoleUsage()}) == 0.0
    # cache tokens priced at cache rates (opus cache_read 0.50/1M)
    cache = {"g": RoleUsage(cache_read_tokens=1_000_000)}
    assert registry.estimate_cost({"g": "anthropic:claude-opus-4-8"}, cache) == 0.50
