"""The refine loop and its guards, extracted from ``run.py`` (I3 decomposition).

Behavior-preserving: ``run.py`` sets ``_refine_loop = refine_loop`` and re-exports the
thresholds + ``refine_skip_objective`` so every historical import keeps resolving, and the
golden pipeline snapshot stays byte-identical. Each termination/escalation guard lives here
as a named, individually-testable unit (``should_skip_refine``, ``plateau_signature``,
``design_implicated``, ``BestTracker``, ``EscalationLedger``, ``ReportBuilder``,
``IterationRecorder``, ``apply_revisions``) rather than being reachable only through the loop.

The two symbols that still live in ``run.py`` — ``regenerate_section`` (shared with ``xlo
regen`` via ``regen.py``) and ``_interactive_checkpoint`` (the attended default) — are imported
lazily inside the loop to avoid an import cycle.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from .. import degradations
from .. import qa as qa_pkg
from ..agents import director as director_mod
from ..agents import generator as generator_mod
from ..agents import judge as judge_mod
from ..effect_emitter import clamp_layer_budget
from ..models.registry import run_agent
from ..progress import NullProgressBus
from ..refine import floor_visual_revisions, replace_section
from ..revision_log import (
    LogFinding,
    LogRevision,
    NullRevisionLog,
    RevisionLogRecord,
    source_of,
)
from .generate import finalize_effects, place_matrix_narrative
from .tuning import REGRESS_MARGIN, REFINE_SKIP_OBJECTIVE, STALL_LIMIT

log = logging.getLogger(__name__)


# -- pure guards --------------------------------------------------------------

def refine_skip_objective() -> int:
    """The first-pass objective at/above which refinement is skipped (env-overridable)."""
    try:
        return int(os.environ.get("XLO_REFINE_SKIP_OBJECTIVE", REFINE_SKIP_OBJECTIVE))
    except (TypeError, ValueError):
        return REFINE_SKIP_OBJECTIVE


def should_skip_refine(first_pass_objective: int, skip_objective: int | None) -> bool:
    """Skip the loop when the first-pass objective is already at/above the cutoff.

    ``None`` disables the gate; equality skips (``>=``)."""
    return skip_objective is not None and first_pass_objective >= skip_objective


def plateau_signature(report, verdict) -> tuple:
    """Iteration fingerprint: scores + the flagged (section, issue[:64]) set. Two equal
    consecutive signatures mean more spend for the same answer → stop."""
    return (report.objective_score, report.advisory_score,
            frozenset((r.section_index, (r.issue or "")[:64]) for r in verdict.revisions))


def design_implicated(plan, section_index, findings) -> bool:
    """True when a ``rules`` finding for this section names one of its planned effect types —
    i.e. the brief itself is implicated, so the section warrants a Director re-plan."""
    if not (plan and 0 <= section_index < len(plan.sections)):
        return False
    eff = set(plan.sections[section_index].effect_types or [])
    return any(getattr(f, "section_index", None) == section_index and getattr(f, "metric", "") == "rules"
               and any(e and e in f.detail for e in eff) for f in findings)


# -- stateful guards ----------------------------------------------------------

@dataclass
class Outcome:
    reverted: bool
    gained: bool


class BestTracker:
    """Owns the best-so-far instructions/render/objective, the open-sequence tracking, and the
    stall counter (guards #4/#5/#9). Comparison operators are ported verbatim from the loop:
    a revert is ``obj < best - margin``, a gain is ``obj > best + margin``, a held objective
    keeps but does not reset stall, and the kept objective is ``max(best_obj, obj)``."""

    def __init__(self, instructions, applied, obj, *, margin=REGRESS_MARGIN, stall_limit=STALL_LIMIT):
        self.best = list(instructions)
        self.best_applied = applied
        self.best_obj = obj
        self.open_is_best = True
        self.stall = 0
        self.margin = margin
        self.stall_limit = stall_limit

    def assess(self, obj) -> Outcome:
        reverted = obj < self.best_obj - self.margin
        gained = (not reverted) and obj > self.best_obj + self.margin
        return Outcome(reverted=reverted, gained=gained)

    def revert(self):
        """Return the best instructions/render to restore (does NOT mutate best)."""
        return list(self.best), self.best_applied

    def on_reverted(self, applied):
        """After a revert is re-emitted: the re-emitted render becomes the open best; stall++."""
        self.best_applied = applied
        self.open_is_best = True
        self.stall += 1

    def keep(self, instructions, applied, obj, *, gained):
        self.best = list(instructions)
        self.best_applied = applied
        self.best_obj = max(self.best_obj, obj)
        self.open_is_best = True
        self.stall = 0 if gained else self.stall

    @property
    def stalled(self) -> bool:
        return self.stall >= self.stall_limit


class EscalationLedger:
    """Owns the revision ledger (guard #6) and the once-per-run design-escalation set
    (guard #7). ``prior_sections`` is snapshotted by the caller BEFORE a round's revisions are
    recorded, so a repeat within the same round does not self-trigger escalation."""

    def __init__(self):
        self.ledger: list = []          # RevisionBriefs recorded across the run
        self.redesigned: set[int] = set()

    def record(self, rev) -> None:
        self.ledger.append(rev)

    def prior_sections(self) -> set[int]:
        return {r.section_index for r in self.ledger}

    def mark_redesigned(self, si: int) -> None:
        self.redesigned.add(si)

    def should_escalate(self, si, plan, findings, *, prior) -> bool:
        """Escalate a section to the Director once per run when it is a repeat offender
        (in ``prior``) or the brief is design-implicated by a rules finding."""
        return si not in self.redesigned and (si in prior or design_implicated(plan, si, findings))


# -- collaborators ------------------------------------------------------------

class ReportBuilder:
    """Wraps ``_report``/``_obj``: flush the .fseq (save → real-render refresh) so coverage
    samples THIS render, then evaluate QA. The save/refresh is best-effort (sampling degrades to
    neutral). Injected qa fakes keep the legacy 5-arg signature (no ``sampler`` kwarg)."""

    def __init__(self, st, *, client, qa_eval, sampler, save_as, real_render):
        self.st = st
        self.client = client
        self.qa_eval = qa_eval
        self.sampler = sampler
        self.save_as = save_as
        self.real_render = real_render

    async def report(self, applied):
        if self.sampler is not None and self.save_as:
            try:                                  # flush the .fseq so coverage sees THIS render
                await self.client.save_sequence(self.save_as)
                if self.real_render is not None:  # export the REAL render for coverage + critic
                    await self.real_render.refresh(self.client)
            except Exception as exc:  # noqa: BLE001 — sampling degrades to neutral
                degradations.note("qa:render-flush", exc, stage="refine")
        if self.sampler is not None:              # injected qa fakes keep the legacy signature
            return self.qa_eval(self.st.instructions, self.st.song_analysis, self.st.show_plan,
                                applied, self.st.available_groups, sampler=self.sampler)
        return self.qa_eval(self.st.instructions, self.st.song_analysis, self.st.show_plan,
                            applied, self.st.available_groups)

    async def objective(self, applied):
        return (await self.report(applied)).objective_score


class IterationRecorder:
    """Wraps ``_record``/``_bundle``: assemble the ``RevisionLogRecord`` and guard the review
    bundle path. Pure observability — ``revlog.write`` is itself best-effort, so this never
    raises into the loop. The F-I progress ``score``/``refine`` events are emitted HERE from the
    same record fields so the SSE stream and the revision log can never disagree (one site)."""

    def __init__(self, revlog, *, run_id, song_key, clock, models, review_base, progress=None):
        self.revlog = revlog
        self.run_id = run_id
        self.song_key = song_key
        self.clock = clock
        self.models = models
        self.review_base = review_base
        self.progress = progress or NullProgressBus()

    def _bundle(self, i):
        if self.review_base is None:
            return None
        p = Path(self.review_base) / f"iter{i}"
        return str(p) if p.is_dir() else None              # guard: no dangling pointer

    def record(self, i, report, verdict, **kw) -> None:
        rec = RevisionLogRecord(
            run_id=self.run_id, iteration=i, song_key=self.song_key, ts=self.clock(),
            objective_score=report.objective_score, advisory_score=report.advisory_score,
            findings=[LogFinding(source=source_of(f.metric), severity=f.severity, scope=f.scope,
                                 section_index=f.section_index, detail=f.detail)
                      for f in report.findings],
            judge=({"score": verdict.score, "verdict": verdict.verdict} if verdict else None),
            models=self.models or {}, review_bundle=self._bundle(i), **kw)
        self.revlog.write(rec)
        # progress from the SAME record — the sparkline feed + refine-decision tap.
        self.progress.emit("score", stage="refine", payload={
            "iteration": i, "objective": rec.objective_score, "advisory": rec.advisory_score,
            "kind": rec.kind, "findings": len(rec.findings),
            "top_findings": [f"{f.severity}:{f.scope}:{(f.detail or '')[:80]}"
                             for f in rec.findings[:3]]})
        self.progress.emit("refine", stage="refine", payload={
            "iteration": i, "kind": rec.kind, "human_decision": rec.human_decision,
            "judge": rec.judge, "obj_before": rec.obj_before, "obj_after": rec.obj_after,
            "obj_delta": rec.obj_delta, "reverted": rec.reverted,
            "regenerated_sections": rec.regenerated_sections})


async def apply_revisions(st, revisions, *, regen, redesign, ledger, findings, log=log) -> None:
    """Guard #7 + splice. Snapshot the prior-revised sections once, then per revision: maybe
    design-escalate (structure pinned — start/end copied back, target_groups defaulted), then
    regenerate and splice the section, and record the revision in the ledger."""
    prior = ledger.prior_sections()
    for rev in revisions:
        si = rev.section_index
        # design escalation: a brief-implicated violation OR a repeat offender → the Director
        # re-plans the SECTION (once per run); generation then realizes the new design.
        if ledger.should_escalate(si, st.show_plan, findings, prior=prior):
            try:
                sec_f = [f for f in findings if getattr(f, "section_index", None) == si]
                new_sec = await redesign(rev, sec_f)
                if new_sec is not None:
                    old = st.show_plan.sections[si]
                    new_sec.start_ms, new_sec.end_ms = old.start_ms, old.end_ms  # structure pinned
                    if not new_sec.target_groups:
                        new_sec.target_groups = list(old.target_groups)
                    st.show_plan.sections[si] = new_sec
                    ledger.mark_redesigned(si)
                    log.info("design-escalated section %d (%d findings)", si, len(sec_f))
            except Exception as exc:  # noqa: BLE001 — escalation is best-effort
                degradations.note("refine:redesign", f"section {si}: {exc}", stage="refine")
        st.instructions = replace_section(st.instructions, si, await regen(rev))
        ledger.record(rev)


# -- the loop -----------------------------------------------------------------

async def refine_loop(st, *, client, emitter, generator, duration_secs,
                      max_iterations, judge, qa, regenerate, checkpoint,
                      visual_critique=None, revlog=None, run_id="run", song_key="",
                      models=None, clock=None, review_base=None,
                      sampler=None, save_as=None, redesign=None, real_render=None,
                      skip_objective=None, progress=None) -> None:
    progress = progress or NullProgressBus()
    qa_eval = qa or qa_pkg.evaluate
    judge_agent = judge or judge_mod.judge_agent()
    if checkpoint is not None:
        decide = checkpoint
    else:
        from .run import _interactive_checkpoint    # lazy: avoid the run.py import cycle
        decide = _interactive_checkpoint
    # Build the default generator only if we'll actually use it (no injected regenerate) —
    # constructing a real Agent needs an API key, which hermetic tests don't have.
    gen_agent = generator if regenerate is not None else (generator or generator_mod.generator_agent())

    async def _regen(rev):
        if regenerate is not None:
            return await regenerate(rev)
        from .run import regenerate_section       # lazy: shared with xlo regen, lives in run.py
        return await regenerate_section(st, rev, gen_agent=gen_agent)

    _rd_agent = None

    async def _redesign(rev, findings):
        nonlocal _rd_agent
        if redesign is not None:
            return await redesign(rev, findings)
        if _rd_agent is None:                          # lazy — real agent needs an API key
            _rd_agent = director_mod.section_redesigner()
        sec = st.show_plan.sections[rev.section_index]
        return (await run_agent(_rd_agent, director_mod.redesign_input(sec, st.show_plan, findings),
                                role="redesigner", attempts=2)).output

    revlog = revlog or NullRevisionLog()
    clock = clock or (lambda: "")
    reporter = ReportBuilder(st, client=client, qa_eval=qa_eval, sampler=sampler,
                             save_as=save_as, real_render=real_render)
    recorder = IterationRecorder(revlog, run_id=run_id, song_key=song_key, clock=clock,
                                 models=models, review_base=review_base, progress=progress)
    ledger = EscalationLedger()

    first_obj = await reporter.objective(st.applied)
    tracker = BestTracker(st.instructions, st.applied, first_obj)

    if should_skip_refine(first_obj, skip_objective):
        # already good → accept the draft without spending judge/critic/regen iterations
        log.info("refine skipped: first-pass objective %d ≥ %d (already good)", first_obj, skip_objective)
        recorder.record(0, await reporter.report(st.applied), None, kind="finalize",
                        obj_after=first_obj, human_decision="skip-high-objective")
        return

    iters = 0
    prev_sig = None       # plateau detector: scores + flagged sections unchanged → more spend, same answer
    for i in range(max_iterations):                       # HARD cap — cannot be exceeded
        iters = i + 1
        obj_before = tracker.best_obj                     # snapshot BEFORE the keep/revert branch mutates it
        report = await reporter.report(st.applied)
        if visual_critique is not None:        # advisory visual findings → Judge/human (NOT objective_score)
            try:
                report.findings.extend(await visual_critique(st))
            except Exception as exc:  # noqa: BLE001 — visual critique is best-effort
                degradations.note("visual:critique", exc, stage="refine")
        verdict = (await run_agent(
            judge_agent,
            judge_mod.render_input(report, st.show_plan, st.music_brief, ledger.ledger),
            role="judge", attempts=3)).output
        decision = await decide(report, verdict, ledger.ledger)
        if decision.action in ("accept", "stop"):
            recorder.record(i, report, verdict, human_decision=decision.action,   # log the accept/stop too
                            obj_before=obj_before, obj_after=obj_before, obj_delta=0)
            break
        sig = plateau_signature(report, verdict)
        if sig == prev_sig:                   # plateau: the iteration would re-spend on the same answer
            log.info("plateau: objective+advisory+revisions unchanged — stopping")
            recorder.record(i, report, verdict, human_decision="plateau",
                            obj_before=obj_before, obj_after=obj_before, obj_delta=0)
            break
        prev_sig = sig
        judge_revs = list(decision.revisions or verdict.revisions)
        floored = floor_visual_revisions(report.findings, judge_revs)     # backstop: critic-confirmed visual errors
        revisions = judge_revs + floored
        await apply_revisions(st, revisions, regen=_regen, redesign=_redesign,
                              ledger=ledger, findings=report.findings, log=log)
        st.instructions, _ = clamp_layer_budget(st.instructions)      # rule #10 on regen too
        # re-run the matrix narrative-text pass after the splice: a regenerated section may own a
        # text moment (recreate exactly one; strip-and-replace is idempotent) and the background
        # dim must re-apply against the fresh section effects (D6, mirrors the transitions pass).
        st.instructions = place_matrix_narrative(st, st.instructions)
        # occlusion guard + sub-frame stretch + tail fade on the spliced list — a regenerated
        # section must not reintroduce an opaque wash (the 2:15 bug) or sub-frame slivers
        st.instructions = finalize_effects(st, st.instructions)
        await client.close_sequence(force=True, quiet=True)
        st.applied = await emitter(client, st.instructions, duration_secs=duration_secs)
        obj = await reporter.objective(st.applied)
        outcome = tracker.assess(obj)
        if outcome.reverted:                              # objective REGRESSION → revert it
            st.instructions, st.applied = tracker.revert()
            # Re-emit the reverted best NOW: the open xLights sequence otherwise keeps
            # the regressed effects, and the next iteration's report/sampler/critic
            # would measure (and the Judge would see) the render we just discarded.
            await client.close_sequence(force=True, quiet=True)
            st.applied = await emitter(client, st.instructions, duration_secs=duration_secs)
            tracker.on_reverted(st.applied)
        else:                                             # gain OR held-objective → keep the revision
            tracker.keep(st.instructions, st.applied, obj, gained=outcome.gained)
        recorder.record(i, report, verdict, human_decision=decision.action,
                        revisions=([LogRevision(section_index=r.section_index, issue=r.issue, origin="judge")
                                    for r in judge_revs]
                                   + [LogRevision(section_index=r.section_index, issue=r.issue, origin="backstop")
                                      for r in floored]),
                        regenerated_sections=[r.section_index for r in revisions],
                        obj_before=obj_before, obj_after=obj, obj_delta=obj - obj_before,
                        reverted=outcome.reverted)
        if tracker.stalled:                               # objective keeps regressing → terminate
            break

    st.instructions, st.applied = list(tracker.best), tracker.best_applied
    if not tracker.open_is_best:                          # ensure the OPEN sequence == finalized best
        await client.close_sequence(force=True, quiet=True)
        st.applied = await emitter(client, st.instructions, duration_secs=duration_secs)
    final = await reporter.report(st.applied)
    recorder.record(iters, final, None, kind="finalize", obj_after=tracker.best_obj)
