"""The orchestration pipeline: plain async stages over a typed State, with stage caching.

No graph engine — the flow is sequential (pydantic-graph's BaseNode/Graph is deprecated
in 1.106; revisit a graph engine when the refine loop needs cycles). Resume = cached
stage artifacts keyed by song content hash.
"""

from __future__ import annotations

import json
import math
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path

from xlights_core.audio import AudioAnalyzer, SongAnalysis

import logging

from .. import qa as qa_pkg
from ..qa.rules import clamp_hard_caps
from ..agents import director as director_mod
from ..agents import generator as generator_mod
from ..agents import judge as judge_mod
from ..agents import panel as panel_mod
from ..agents.catalog import placeable_effect_types
from ..effect_emitter import apply_instructions, clamp_layer_budget
from ..lyrics import fetch_lyrics
from ..music_brief import MusicBrief
from ..models.registry import model_snapshot
from ..refine import Decision, floor_visual_revisions, replace_section
from ..revision_log import (
    LogFinding,
    LogRevision,
    NullRevisionLog,
    RevisionLog,
    RevisionLogRecord,
    source_of,
)
from ..show_plan import EffectInstruction, ShowPlan
from ..creative_brief import render_creative_brief
from ..brief_schema import write_editable_brief
from ..agents.guide_extracts import scene_ids as _scene_ids
from xlights_core.knowledge.colors import NAMED_COLORS
from ..song_description import render_description
from xlights_core.knowledge.value_curves import brightness_ramp, brightness_setting

from .beats import (
    effective_intensity,
    place_beat_accents,
    section_rhythm,
    feature_prop_contrast,
    effect_palette,
    effect_speed_setting,
    ensemble_bed,
    normalize_durations,
    peak_fill,
    peak_sections,
    section_is_rhythmic,
    trim_coverage,
    wash_brightness,
)
from .groups import targetable_groups
from .weave import canon_effect_type, carrier_covers, expand_weave, fallback_weave
from .media import prepare_media
from .state import State
from .visual import RealRender, make_lit_sampler, make_visual_critique
from .cache import cache_path as _cache_path, cache_root as _cache_root, song_key as _song_key
from .generate import generate_instructions
from .finalize import finalize_sequence

log = logging.getLogger(__name__)

REGRESS_MARGIN = 1   # objective_score points; a drop beyond this reverts the revision
STALL_LIMIT = 2      # consecutive no-objective-progress iterations → terminate


async def _default_interpret(song_path: str, sa: SongAnalysis) -> MusicBrief:
    """Live interpret stage: fetch lyrics, build the panel, run it → MusicBrief."""
    lyrics = fetch_lyrics(song_path)
    have = lyrics is not None or bool((getattr(sa, "lyrics", None) or {}).get("lines"))
    analysts, synthesizer = panel_mod.build_panel(lyrics_present=have)
    return await panel_mod.run_panel(sa, lyrics, analysts=analysts, synthesizer=synthesizer)


async def _auto_checkpoint(report, verdict, ledger) -> Decision:
    """Unattended (`--auto`/tests): take the Judge's verdict verbatim."""
    if verdict.verdict in ("accept", "stop"):
        return Decision(action="accept")
    return Decision(action="approve", revisions=verdict.revisions)


async def _interactive_checkpoint(report, verdict, ledger) -> Decision:
    """Attended: show the human the score/findings/revisions; they can override the Judge."""
    print(f"\n— refine checkpoint — objective={report.objective_score} "
          f"advisory={report.advisory_score} | judge score={verdict.score} ({verdict.verdict})")
    for f in report.findings[:8]:
        print(f"  [{f.metric}] {f.scope}: {f.detail}")
    for r in verdict.revisions:
        print(f"  ↳ revise section {r.section_index}: {r.issue} → {r.suggested_fix}")
    ans = input("approve revisions / [s]top / [k]eep-as-final? [A/s/k] ").strip().lower()
    if ans.startswith(("s", "k")):
        return Decision(action="accept")
    return Decision(action="approve", revisions=verdict.revisions)


async def _design_review(brief_md: str, plan) -> bool:
    """Attended design gate: show the creative brief; approve to generate, abort to correct."""
    print("\n" + "=" * 70 + "\n" + brief_md + "\n" + "=" * 70)
    print("Review the creative brief above (also written to creative_brief.md).")
    ans = input("Proceed to effect generation? [Y/n] (n = stop so you can correct) ").strip().lower()
    return not ans.startswith("n")


async def _interpret_review(desc_md: str, brief) -> bool:
    """Attended interpret gate: show the song description; approve to proceed, abort to stop
    (hand-edit description.md / adjust and re-run). Returns True to continue."""
    print("\n" + "=" * 70 + "\n" + desc_md + "\n" + "=" * 70)
    print("Review the song description above (also written to description.md).")
    ans = input("Proceed to creative direction? [Y/n] (n = stop so you can correct) ").strip().lower()
    return not ans.startswith("n")


async def _final_approval(st: State) -> bool:
    ans = input(f"\nSave final sequence ({len(st.instructions)} effects)? [y/N] ").strip().lower()
    return ans.startswith("y")


async def _refine_loop(st: State, *, client, emitter, generator, duration_secs,
                       max_iterations, judge, qa, regenerate, checkpoint,
                       visual_critique=None, revlog=None, run_id="run", song_key="",
                       models=None, clock=None, review_base=None,
                       sampler=None, save_as=None, redesign=None, real_render=None) -> None:
    qa_eval = qa or qa_pkg.evaluate
    judge_agent = judge or judge_mod.judge_agent()
    decide = checkpoint or _interactive_checkpoint
    # Build the default generator only if we'll actually use it (no injected regenerate) —
    # constructing a real Agent needs an API key, which hermetic tests don't have.
    gen_agent = generator if regenerate is not None else (generator or generator_mod.generator_agent())

    async def _regen(rev):
        if regenerate is not None:
            return await regenerate(rev)
        section = st.show_plan.sections[rev.section_index]
        motifs = {g: st.show_plan.group_motifs[g]
                  for g in section.target_groups if g in st.show_plan.group_motifs}
        out = (await gen_agent.run(generator_mod.render_input(
            section, revision=rev, concept=st.show_plan.concept, motifs=motifs))).output
        _rm = st.music_brief.repetition_map if st.music_brief else None
        _si = effective_intensity(getattr(section, "intensity", 0.5), rev.section_index, _rm)
        _rhythm = section_rhythm(st.song_analysis, section)
        instrs = trim_coverage(list(out.instructions), _si)   # energy-gated coverage on regen too
        for ins in instrs:
            ins.effect_type = canon_effect_type(ins.effect_type)   # 'Single Strand' → placeable
        instrs = normalize_durations(instrs, _rhythm)
        wash_b = wash_brightness(_si)
        for j, ins in enumerate(instrs):
            if section.palette and not ins.palette_colors:   # LLM's explicit color (feature props) wins
                ins.palette_colors = effect_palette(section.palette, ins.effect_type, j)
            if _si >= 0.7 and ins.end_ms - ins.start_ms > 15000:
                ins.extra_settings.update(brightness_ramp(0.7 * wash_b, wash_b))
            else:
                ins.extra_settings.update(brightness_setting(wash_b))
            ins.extra_settings.update(effect_speed_setting(ins.effect_type, _si))
        _is_peak = rev.section_index in peak_sections(st.show_plan)   # payoff section?
        bed = (peak_fill(section, _si, st.available_groups, instrs) if _is_peak
               else ensemble_bed(section, _si, st.available_groups, {k.target for k in instrs}))
        if bed is not None:
            bed.section_index = rev.section_index
            instrs.append(bed)
        weave_obj = getattr(out, "weave", None) or fallback_weave(section, st.available_groups)
        woven = expand_weave(section, weave_obj, _rhythm, _si, st.available_groups,
                             based_targets={k.target for k in instrs})   # cells blend over washes
        for ins in woven:
            ins.section_index = rev.section_index
        instrs += woven                                  # the cell fabric on regen too
        clamp_hard_caps(instrs, getattr(st.song_analysis, "tempo_overall", None))
        accents = place_beat_accents(            # beat layer on regen too — only if the brief is rhythmic
            section, _rhythm, st.available_groups,
            carrier_covers=carrier_covers(weave_obj, section, st.available_groups)) \
            if section_is_rhythmic(section) else []
        under = {k.target for k in instrs}
        for ins in accents:
            ins.section_index = rev.section_index
            if ins.target in under:                      # a pulse ADDS over its base, not occludes
                ins.extra_settings.setdefault("T_CHOICE_LayerMethod", "Max")
        instrs += accents
        feature_prop_contrast(instrs, section)           # featured sparkle/snow props pop (white-on-bed)
        return instrs

    redesigned: set[int] = set()
    _rd_agent = None

    async def _redesign(rev, findings):
        nonlocal _rd_agent
        if redesign is not None:
            return await redesign(rev, findings)
        if _rd_agent is None:                          # lazy — real agent needs an API key
            _rd_agent = director_mod.section_redesigner()
        sec = st.show_plan.sections[rev.section_index]
        return (await _rd_agent.run(director_mod.redesign_input(sec, st.show_plan, findings))).output

    def _design_implicated(si, findings):
        if not (st.show_plan and 0 <= si < len(st.show_plan.sections)):
            return False
        eff = set(st.show_plan.sections[si].effect_types or [])
        return any(getattr(f, "section_index", None) == si and getattr(f, "metric", "") == "rules"
                   and any(e and e in f.detail for e in eff) for f in findings)

    async def _report(applied):
        if sampler is not None and save_as:
            try:                                  # flush the .fseq so coverage sees THIS render
                await client.save_sequence(save_as)
                if real_render is not None:       # export the REAL render for coverage + critic
                    await real_render.refresh(client)
            except Exception:  # noqa: BLE001 — sampling degrades to neutral
                pass
        if sampler is not None:                   # injected qa fakes keep the legacy signature
            return qa_eval(st.instructions, st.song_analysis, st.show_plan, applied,
                           st.available_groups, sampler=sampler)
        return qa_eval(st.instructions, st.song_analysis, st.show_plan, applied,
                       st.available_groups)

    async def _obj(applied):
        return (await _report(applied)).objective_score

    best, best_applied, best_obj = list(st.instructions), st.applied, await _obj(st.applied)
    open_is_best = True
    ledger, stall = [], 0
    revlog = revlog or NullRevisionLog()
    clock = clock or (lambda: "")

    def _bundle(i):
        if review_base is None:
            return None
        p = Path(review_base) / f"iter{i}"
        return str(p) if p.is_dir() else None             # guard: no dangling pointer

    def _record(i, report, verdict, **kw):                # pure observability — wrapped, never raises into the loop
        revlog.write(RevisionLogRecord(
            run_id=run_id, iteration=i, song_key=song_key, ts=clock(),
            objective_score=report.objective_score, advisory_score=report.advisory_score,
            findings=[LogFinding(source=source_of(f.metric), severity=f.severity, scope=f.scope,
                                 section_index=f.section_index, detail=f.detail)
                      for f in report.findings],
            judge=({"score": verdict.score, "verdict": verdict.verdict} if verdict else None),
            models=models or {}, review_bundle=_bundle(i), **kw))

    iters = 0
    prev_sig = None       # plateau detector: scores + flagged sections unchanged → more spend, same answer
    for i in range(max_iterations):                       # HARD cap — cannot be exceeded
        iters = i + 1
        obj_before = best_obj                             # snapshot BEFORE the keep/revert branch mutates it
        report = await _report(st.applied)
        if visual_critique is not None:        # advisory visual findings → Judge/human (NOT objective_score)
            try:
                report.findings.extend(await visual_critique(st))
            except Exception as exc:  # noqa: BLE001 — visual critique is best-effort
                log.warning("visual critique failed: %s", exc)
        verdict = (await judge_agent.run(
            judge_mod.render_input(report, st.show_plan, st.music_brief, ledger))).output
        decision = await decide(report, verdict, ledger)
        if decision.action in ("accept", "stop"):
            _record(i, report, verdict, human_decision=decision.action,   # log the accept/stop too
                    obj_before=obj_before, obj_after=obj_before, obj_delta=0)
            break
        sig = (report.objective_score, report.advisory_score,
               frozenset((r.section_index, (r.issue or "")[:64]) for r in verdict.revisions))
        if sig == prev_sig:                   # plateau: the iteration would re-spend on the same answer
            log.info("plateau: objective+advisory+revisions unchanged — stopping")
            _record(i, report, verdict, human_decision="plateau",
                    obj_before=obj_before, obj_after=obj_before, obj_delta=0)
            break
        prev_sig = sig
        judge_revs = list(decision.revisions or verdict.revisions)
        floored = floor_visual_revisions(report.findings, judge_revs)     # backstop: critic-confirmed visual errors
        revisions = judge_revs + floored
        prior = {r.section_index for r in ledger}     # sections already revised in earlier iterations
        for rev in revisions:
            si = rev.section_index
            # design escalation: a brief-implicated violation OR a repeat offender → the Director
            # re-plans the SECTION (once per run); generation then realizes the new design.
            if si not in redesigned and (si in prior or _design_implicated(si, report.findings)):
                try:
                    sec_f = [f for f in report.findings if getattr(f, "section_index", None) == si]
                    new_sec = await _redesign(rev, sec_f)
                    if new_sec is not None:
                        old = st.show_plan.sections[si]
                        new_sec.start_ms, new_sec.end_ms = old.start_ms, old.end_ms  # structure pinned
                        if not new_sec.target_groups:
                            new_sec.target_groups = list(old.target_groups)
                        st.show_plan.sections[si] = new_sec
                        redesigned.add(si)
                        log.info("design-escalated section %d (%d findings)", si, len(sec_f))
                except Exception as exc:  # noqa: BLE001 — escalation is best-effort
                    log.warning("section redesign failed for %d: %s", si, exc)
            st.instructions = replace_section(st.instructions, si, await _regen(rev))
            ledger.append(rev)
        st.instructions, _ = clamp_layer_budget(st.instructions)      # rule #10 on regen too
        await client.close_sequence(force=True, quiet=True)
        st.applied = await emitter(client, st.instructions, duration_secs=duration_secs)
        obj = await _obj(st.applied)
        reverted = obj < best_obj - REGRESS_MARGIN
        if reverted:                                      # objective REGRESSION → revert it
            st.instructions, st.applied, open_is_best = list(best), best_applied, False
            stall += 1                                    # repeated regressions → stall stop
        else:                                             # gain OR held-objective → keep the revision
            gained = obj > best_obj + REGRESS_MARGIN      # (a creative change that holds sync/placement
            best, best_applied = list(st.instructions), st.applied   #  is the Judge's call, not the score's)
            best_obj, open_is_best = max(best_obj, obj), True
            stall = 0 if gained else stall
        _record(i, report, verdict, human_decision=decision.action,
                revisions=([LogRevision(section_index=r.section_index, issue=r.issue, origin="judge")
                            for r in judge_revs]
                           + [LogRevision(section_index=r.section_index, issue=r.issue, origin="backstop")
                              for r in floored]),
                regenerated_sections=[r.section_index for r in revisions],
                obj_before=obj_before, obj_after=obj, obj_delta=obj - obj_before, reverted=reverted)
        if stall >= STALL_LIMIT:                          # objective keeps regressing → terminate
            break

    st.instructions, st.applied = list(best), best_applied
    if not open_is_best:                                  # ensure the OPEN sequence == finalized best
        await client.close_sequence(force=True, quiet=True)
        st.applied = await emitter(client, st.instructions, duration_secs=duration_secs)
    final = await _report(st.applied)
    _record(iters, final, None, kind="finalize", obj_after=best_obj)

def _emit_editable_brief(st, out_dir) -> None:
    """Write the schema-backed, hand-editable creative_brief.json (+ schema) — the run's vocabulary
    as enum dropdowns. Idempotent on a cached/edited brief (rewrites the loaded plan)."""
    write_editable_brief(
        st.show_plan, out_dir,
        groups=list(st.available_groups or []),
        effect_types=list(st.placeable_types or placeable_effect_types()),
        scene_ids=_scene_ids(),
        stems=[f.stem for f in (getattr(st.song_analysis, "stems", None) or [])],
        colors=list(NAMED_COLORS),
    )


async def run_pipeline(
    song_path: str,
    *,
    client,
    director=None,
    generator=None,
    analyze: Callable[[str], SongAnalysis] | None = None,
    interpret: Callable[[str, SongAnalysis], Awaitable[MusicBrief]] | None = None,
    emitter: Callable[..., Awaitable[dict]] = apply_instructions,
    save_as: str | None = None,
    use_cache: bool = True,
    stems: bool = True,
    duration_secs: int | None = None,
    refine: bool = False,
    max_iterations: int = 3,
    judge=None,
    qa=None,
    regenerate=None,
    checkpoint=None,
    visual_critique=None,
    log_revisions: bool = True,
    interpret_checkpoint=None,
    design_checkpoint=None,
    timing_tracks: bool = True,
) -> State:
    st = State(song_path=song_path)
    key = _song_key(song_path)

    # 1. analyze. The default analyzer requests stems (per-section instrument signal);
    #    an injected analyze callable keeps the simple (path)->SongAnalysis shape.
    if analyze is not None:
        st.song_analysis = analyze(song_path)
    else:
        st.song_analysis = AudioAnalyzer().analyze(song_path, stems=stems)
    # timed lyrics as part of the INITIAL analysis: fetch text, align on the vocal stem (cached).
    # This also flips the synthesizer's `instrumental` flag (it reads sa.lyrics) for vocal songs.
    # Re-attach when the cache predates marker-aware fetching (no headers_fetch flag) so lyric
    # section markers upgrade old caches once.
    _ly = getattr(st.song_analysis, "lyrics", None) or {}
    if not _ly.get("lines") or not _ly.get("headers_fetch"):
        try:
            _ld = fetch_lyrics(song_path)
            if _ld and _ld.text:
                if AudioAnalyzer().attach_lyrics(st.song_analysis, song_path, text=_ld.text,
                                                 title=_ld.title or "", artist=_ld.artist or ""):
                    log.info("timed lyrics attached (%d lines)",
                             len(st.song_analysis.lyrics.get("lines", [])))
        except Exception as exc:  # noqa: BLE001 — lyrics are enrichment
            log.info("lyric attach skipped: %s", exc)
    # Instrumental complement: still no timed lines → subdivide long audio sections at
    # musical seams so no single look runs past ~32s (best-effort; never blocks the run).
    if not (getattr(st.song_analysis, "lyrics", None) or {}).get("lines"):
        try:
            if AudioAnalyzer().refine_instrumental(st.song_analysis, song_path):
                log.info("instrumental sections refined (%d segments)",
                         len(st.song_analysis.segments))
        except Exception as exc:  # noqa: BLE001 — refinement is enrichment
            log.info("instrumental refine skipped: %s", exc)

    st.available_groups = await targetable_groups(client, cache_root=_cache_root())  # only addEffect-able
    st.placeable_types = placeable_effect_types()

    # 2. interpret -> rich SongDescription (panel of analysts + synthesizer; cached).
    #    Cache key bumped from "music_brief" so old flat briefs don't shadow the richer one.
    mb_cache = _cache_path(key, "song_description")
    if use_cache and mb_cache.exists():
        try:
            st.music_brief = MusicBrief.model_validate_json(mb_cache.read_text())
        except Exception:  # noqa: BLE001 — stale/invalid cache shape → recompute
            st.music_brief = None
    if st.music_brief is None:
        st.music_brief = await (interpret or _default_interpret)(song_path, st.song_analysis)
        mb_cache.parent.mkdir(parents=True, exist_ok=True)
        mb_cache.write_text(st.music_brief.model_dump_json())
    desc_md = render_description(st.music_brief)            # human-readable song description
    (mb_cache.parent / "description.md").write_text(desc_md)
    if interpret_checkpoint is not None:                    # hard review gate (attended); --auto passes None
        if not await interpret_checkpoint(desc_md, st.music_brief):
            return st                                        # human declined → stop before downstream

    # 3. design -> creative brief (ShowPlan; cached). Key bumped from "show_plan" so old thin
    #    plans don't shadow the rich brief.
    sp_cache = _cache_path(key, "creative_brief")
    if use_cache and sp_cache.exists():
        st.show_plan = ShowPlan.model_validate_json(sp_cache.read_text())
    else:
        agent = director or director_mod.director_agent()
        prompt = director_mod.render_input(st.music_brief, st.available_groups, st.placeable_types)
        st.show_plan = (await agent.run(prompt)).output
    _emit_editable_brief(st, sp_cache.parent)             # schema-backed, hand-editable brief (+ schema)
    brief_md = render_creative_brief(st.show_plan)         # human-readable creative brief
    (sp_cache.parent / "creative_brief.md").write_text(brief_md)
    if design_checkpoint is not None:                      # hard review gate (attended); --auto passes None
        log.info("creative brief is editable (schema-backed dropdowns) at %s — edit + re-run to apply",
                 sp_cache)
        if not await design_checkpoint(brief_md, st.show_plan):
            return st

    # 3. generate -> EffectInstruction[] (cached) — each section FOLLOWS the brief
    ins_cache = _cache_path(key, "instructions")
    if use_cache and ins_cache.exists():
        st.instructions = [EffectInstruction.model_validate(x)
                           for x in json.loads(ins_cache.read_text())]
    else:
        st.instructions = await generate_instructions(st, generator=generator)
        ins_cache.parent.mkdir(parents=True, exist_ok=True)
        ins_cache.write_text(json.dumps([i.model_dump() for i in st.instructions]))

    # 4. apply + render — ANIMATION only (audio is patched into the .xsq at finalize, because
    #    attaching media via the live API crashes xLights). Stage the song now for that patch.
    dur = duration_secs or max(1, math.ceil(st.song_analysis.duration_s))
    try:
        show_folder = await client.get_show_folder()
    except Exception:  # noqa: BLE001
        show_folder = None
    media = prepare_media(song_path, show_folder)
    st.instructions, _dropped = clamp_layer_budget(st.instructions)   # catalog rule #10: ≤4 layers
    if _dropped:
        log.info("layer budget trimmed %d over-stacked placements", _dropped)
    st.applied = await emitter(client, st.instructions, duration_secs=dur)

    # 5. refine (opt-in): test -> decide -> regenerate flagged sections -> rebuild
    if refine:
        real = RealRender(save_as, st.song_analysis.duration_s) if save_as else None
        vc = visual_critique
        if vc is None:
            vc = make_visual_critique(client, save_as=save_as, song_key=key,
                                      cache_root=_cache_root(), real=real)
        revlog, run_id = NullRevisionLog(), "run"
        if log_revisions:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            base = _cache_root() / key
            revlog = RevisionLog(base / "revision_log.jsonl", base / "revision_log.md")
        sampler = None if qa is not None else make_lit_sampler(save_as=save_as,
                                                                show_folder=show_folder, real=real)
        await _refine_loop(st, client=client, emitter=emitter, generator=generator,
                           duration_secs=dur, max_iterations=max_iterations,
                           judge=judge, qa=qa, regenerate=regenerate, checkpoint=checkpoint,
                           visual_critique=vc, revlog=revlog, run_id=run_id, song_key=key,
                           models=model_snapshot(),
                           clock=lambda: datetime.now(timezone.utc).isoformat(),
                           review_base=_cache_root() / key / "visual_review",
                           sampler=sampler, save_as=save_as, real_render=real)
        try:    # persist design escalations AND the refined instructions (not the pre-refine cache)
            _emit_editable_brief(st, _cache_root() / key)   # keep the brief schema-backed after refine
            (_cache_root() / key / "creative_brief.md").write_text(render_creative_brief(st.show_plan))
            _cache_path(key, "instructions").write_text(
                json.dumps([i.model_dump() for i in st.instructions], indent=1))
        except Exception as exc:  # noqa: BLE001
            log.warning("could not persist revised design: %s", exc)

    # 6. finalize (with a final human approval when attended)
    if save_as:
        if checkpoint is None and refine and not await _final_approval(st):
            return st
        await finalize_sequence(st, client=client, save_as=save_as, media=media,
                                show_folder=show_folder, duration_s=st.song_analysis.duration_s,
                                timing_tracks=timing_tracks)
    return st
