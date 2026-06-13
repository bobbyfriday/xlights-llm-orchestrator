"""Tests for design escalation: persistent/brief-implicated defects → the Director re-plans."""
import asyncio
from types import SimpleNamespace

from xlights_core.audio.schema import Beat, EnergyPoint, Segment, SongAnalysis

from xlights_orchestrator.pipeline.run import _refine_loop
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.refine import Decision, Finding, JudgeVerdict, QAReport, RevisionBrief
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan, ShowPlan


def run(c):
    return asyncio.run(c)


def _state(effect_types=("Plasma",)):
    st = State(song_path="s.mp3")
    st.song_analysis = SongAnalysis(path="s.mp3", duration_s=4.0, sample_rate=44100,
                                    beats=[Beat(time=0)], segments=[Segment(start=0, end=4, segment_id="A")],
                                    energy_arc=[EnergyPoint(time=0, rms=0.3)])
    st.show_plan = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=4000, target_groups=["G1"],
                                                  effect_family="Plasma", intensity=0.9,
                                                  effect_types=list(effect_types))])
    st.available_groups = ["G1"]
    st.instructions = [EffectInstruction(target="G1", effect_type="Plasma", look_id="x",
                                         start_ms=0, end_ms=1000, section_index=0)]
    st.applied = {"placed": [{"section_index": 0}], "skipped": []}
    return st


def _qa_with(findings):
    def qa(instructions, analysis, plan, applied, groups):
        return QAReport(objective_score=70, advisory_score=100, findings=findings)
    return qa


class _JudgeIterate:
    async def run(self, prompt):
        return SimpleNamespace(output=JudgeVerdict(
            score=60, verdict="iterate",
            revisions=[RevisionBrief(section_index=0, issue="fix it", suggested_fix="", do_not_repeat="")]))


async def _approve(report, verdict, ledger):
    return Decision(action="approve", revisions=verdict.revisions)


def _loop(st, qa, redesign, max_iterations=1):
    async def regen(rev):
        return []
    client = SimpleNamespace(close_sequence=lambda **k: _noop())
    return _refine_loop(st, client=client, emitter=lambda *a, **k: _noop(), generator=None,
                        duration_secs=4, max_iterations=max_iterations, judge=_JudgeIterate(),
                        qa=qa, regenerate=regen, checkpoint=_approve, visual_critique=None,
                        redesign=redesign)


async def _noop():
    return None


def _rules_finding():
    return Finding(scope="section 0 / G1", severity="error", metric="rules", section_index=0,
                   detail="Plasma (energy 1–3) in an energy-5 section — a defect, not a choice")


def test_brief_implicated_violation_escalates_once():
    st = _state()
    calls = []

    async def redesign(rev, findings):
        calls.append((rev.section_index, len(findings)))
        return SectionPlan(start_ms=999, end_ms=999, target_groups=[], effect_family="Spirals",
                           intensity=0.9, effect_types=["Spirals"])

    run(_loop(st, _qa_with([_rules_finding()]), redesign, max_iterations=2))
    assert len(calls) == 1 and calls[0][0] == 0           # escalated exactly ONCE despite 2 iterations
    sec = st.show_plan.sections[0]
    assert sec.effect_types == ["Spirals"]                # the new design landed
    assert (sec.start_ms, sec.end_ms) == (0, 4000)        # structure pinned to the original
    assert sec.target_groups == ["G1"]                    # groups preserved when redesign omits them


def test_repeat_offender_escalates_on_second_iteration():
    st = _state(effect_types=("Spirals",))                # NOT implicated by the finding text
    calls = []

    async def redesign(rev, findings):
        calls.append(rev.section_index)
        return None                                       # redesign declines → nothing replaced

    f = Finding(scope="section 0", severity="error", metric="coverage", section_index=0,
                detail="renders mostly dark")
    seq = iter([70, 71, 72, 73, 74])                      # moving objective — a FLAT score with the
                                                          # same revision is now a plateau stop

    def qa(instructions, analysis, plan, applied, groups):
        return QAReport(objective_score=next(seq, 75), advisory_score=100, findings=[f])

    run(_loop(st, qa, redesign, max_iterations=2))
    assert calls == [0]                                   # not on iter 0 (no prior), yes on iter 1 (repeat)
    assert st.show_plan.sections[0].effect_types == ["Spirals"]   # None → untouched


def test_clean_section_never_escalates():
    st = _state()
    calls = []

    async def redesign(rev, findings):
        calls.append(rev.section_index)
        return None

    f = Finding(scope="global", severity="warn", metric="sync", section_index=None, detail="off-beat")
    run(_loop(st, _qa_with([f]), redesign, max_iterations=1))
    assert calls == []                                    # no design-implication, no repeat → no escalation
