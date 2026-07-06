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

from .. import telemetry
from ..agents import director as director_mod
from ..agents import panel as panel_mod
from ..agents.catalog import placeable_effect_types
from ..effect_emitter import apply_instructions, clamp_layer_budget
from ..lyrics import fetch_lyrics
from ..music_brief import MusicBrief
from ..models.registry import active_provider, estimate_cost, model_snapshot
from ..refine import Decision
from ..revision_log import (
    NullRevisionLog,
    RevisionLog,
)
from ..show_plan import EffectInstruction, ShowPlan
from ..creative_brief import render_creative_brief
from ..brief_schema import write_editable_brief
from ..agents.guide_extracts import scene_ids as _scene_ids
from xlights_core.knowledge.colors import NAMED_COLORS
from ..song_description import render_description

from .beats import feature_prop_contrast
from .groups import targetable_groups
from .media import prepare_media
from .state import State
from .visual import RealRender, make_fseq_series_provider, make_lit_sampler, make_visual_critique
from .cache import cache_path as _cache_path, cache_root as _cache_root, song_key as _song_key
from .generate import generate_instructions, realize_section
from .finalize import finalize_sequence
from .refine_loop import refine_loop as _refine_loop  # re-export: historical import path (tests)
from .refine_loop import refine_skip_objective as _refine_skip_objective  # re-export (tests + wiring)
from .tuning import REFINE_SKIP_OBJECTIVE  # noqa: F401 — re-export: test_refine imports it from here

log = logging.getLogger(__name__)


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


async def regenerate_section(st: State, rev, *, gen_agent) -> list[EffectInstruction]:
    """Realize ONE section's instructions from a RevisionBrief via the SAME per-section
    pipeline first-pass generation uses (`generate.realize_section`), with section structure
    pinned. Shared by the automatic refine loop and the manual `xlo regen` command. Callers
    splice the result in with `replace_section` and then run `finalize_effects` over the
    full list (occlusion guard, sub-frame stretch, tail fade are whole-list passes)."""
    instrs = await realize_section(st, rev.section_index, agent=gen_agent, revision=rev)
    feature_prop_contrast(instrs, st.show_plan.sections[rev.section_index])
    return instrs


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
    telemetry.start_run()          # install the run-scoped usage collector (reaches every await below)
    st = State(song_path=song_path)
    key = _song_key(song_path)
    run_id = None                  # set when the refine loop runs with logging (reused in usage.json)

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

    try:    # persist the analysis so `xlo regen` can rehydrate without re-analyzing the audio
        sa_cache = _cache_path(key, "song_analysis")
        sa_cache.parent.mkdir(parents=True, exist_ok=True)
        sa_cache.write_text(st.song_analysis.model_dump_json())
    except Exception as exc:  # noqa: BLE001 — caching is best-effort
        log.info("song_analysis cache skipped: %s", exc)

    st.available_groups = await targetable_groups(client, cache_root=_cache_root())  # only addEffect-able
    st.placeable_types = placeable_effect_types()

    # 2. interpret -> rich SongDescription (panel of analysts + synthesizer; cached).
    #    Cache key bumped from "music_brief" so old flat briefs don't shadow the richer one.
    mb_cache = _cache_path(key, "song_description", models=True)
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
    sp_cache = _cache_path(key, "creative_brief", models=True)
    if use_cache and sp_cache.exists():
        st.show_plan = ShowPlan.model_validate_json(sp_cache.read_text())
    else:
        agent = director or director_mod.director_agent()
        prompt = director_mod.render_input(st.music_brief, st.available_groups, st.placeable_types)
        _dir_res = await agent.run(prompt)
        telemetry.record("director", _dir_res)
        st.show_plan = _dir_res.output
    _emit_editable_brief(st, sp_cache.parent)             # schema-backed, hand-editable brief (+ schema)
    brief_md = render_creative_brief(st.show_plan)         # human-readable creative brief
    (sp_cache.parent / "creative_brief.md").write_text(brief_md)
    if design_checkpoint is not None:                      # hard review gate (attended); --auto passes None
        log.info("creative brief is editable (schema-backed dropdowns) at %s — edit + re-run to apply",
                 sp_cache)
        if not await design_checkpoint(brief_md, st.show_plan):
            return st

    # 3. generate -> EffectInstruction[] (cached) — each section FOLLOWS the brief
    ins_cache = _cache_path(key, "instructions", models=True)
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
    if show_folder:                          # singing faces lip-sync to the vocals (deterministic)
        from .faces import place_faces
        faces = place_faces(st.song_analysis, Path(show_folder) / "xlights_rgbeffects.xml")
        if faces:
            st.instructions = list(st.instructions) + faces
    st.instructions, _dropped = clamp_layer_budget(st.instructions)   # catalog rule #10: ≤4 layers
    if _dropped:
        log.info("layer budget trimmed %d over-stacked placements", _dropped)
    st.applied = await emitter(client, st.instructions, duration_secs=dur)

    # 5. refine (opt-in): test -> decide -> regenerate flagged sections -> rebuild
    if refine:
        mdir = ins_cache.parent                     # the model-namespaced LLM-stage dir for this routing
        real = RealRender(save_as, st.song_analysis.duration_s) if save_as else None
        vc = visual_critique
        if vc is None:
            # visual_review bundles are LLM-stage artifacts → namespace them under the routing
            vc = make_visual_critique(client, save_as=save_as, song_key=str(mdir.name),
                                      cache_root=mdir.parent, real=real)
        revlog, run_id = NullRevisionLog(), "run"
        if log_revisions:                           # the revision log stays SHARED (all arms in one file)
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            base = _cache_root() / key
            revlog = RevisionLog(base / "revision_log.jsonl", base / "revision_log.md")
        sampler = None if qa is not None else make_lit_sampler(save_as=save_as,
                                                                show_folder=show_folder, real=real)
        # Tier 0 rendered-pixel metrics (advisory-first): a per-group series over the current .fseq
        fseq_provider = None if qa is not None else make_fseq_series_provider(
            save_as=save_as, show_folder=show_folder, groups=st.available_groups)
        await _refine_loop(st, client=client, emitter=emitter, generator=generator,
                           duration_secs=dur, max_iterations=max_iterations,
                           judge=judge, qa=qa, regenerate=regenerate, checkpoint=checkpoint,
                           visual_critique=vc, revlog=revlog, run_id=run_id, song_key=key,
                           models=model_snapshot(),
                           clock=lambda: datetime.now(timezone.utc).isoformat(),
                           review_base=mdir / "visual_review",
                           sampler=sampler, save_as=save_as, real_render=real,
                           skip_objective=_refine_skip_objective(),
                           fseq_series_provider=fseq_provider)
        try:    # persist design escalations AND the refined instructions (not the pre-refine cache)
            _emit_editable_brief(st, mdir)          # keep the brief schema-backed after refine
            (mdir / "creative_brief.md").write_text(render_creative_brief(st.show_plan))
            _cache_path(key, "instructions", models=True).write_text(
                json.dumps([i.model_dump() for i in st.instructions], indent=1))
        except Exception as exc:  # noqa: BLE001
            log.warning("could not persist revised design: %s", exc)

    # 6. finalize (with a final human approval when attended)
    if save_as:
        if checkpoint is None and refine and not await _final_approval(st):
            _emit_usage_summary(key, run_id if refine and log_revisions else None)
            return st
        await finalize_sequence(st, client=client, save_as=save_as, media=media,
                                show_folder=show_folder, duration_s=st.song_analysis.duration_s,
                                timing_tracks=timing_tracks)

    # per-run cost telemetry — a log line + a durable usage.json, so NON-refine and unlogged
    # runs are measured too (the revision log only exists during refine).
    _emit_usage_summary(key, run_id if refine and log_revisions else None)
    return st


def _emit_usage_summary(song_key: str, run_id: str | None) -> None:
    """Best-effort per-run cost summary: a `log.info` line + a `usage.json` artifact under
    `cache_root()/<song_key>/` (a list-of-runs keyed by run_id). Convention: cost None ⇒
    unknown ($unknown); 0.0 ⇒ genuinely zero (fully cached, zero-LLM)."""
    try:
        ul = telemetry.current()
        if ul is None:
            return
        totals = ul.snapshot()
        models = model_snapshot()
        cost = estimate_cost(models, totals)
        tin = sum(u.input_tokens + u.cache_read_tokens + u.cache_write_tokens for u in totals.values())
        tout = sum(u.output_tokens for u in totals.values())
        reqs = sum(u.requests for u in totals.values())
        cost_str = f"${cost:.2f}" if cost is not None else "$unknown"
        log.info("run usage: %s tokens in / %s out across %d requests — est. %s",
                 tin, tout, reqs, cost_str)
        base = _cache_root() / song_key
        base.mkdir(parents=True, exist_ok=True)
        path = base / "usage.json"
        runs = []
        if path.exists():
            try:
                runs = json.loads(path.read_text())
                if not isinstance(runs, list):
                    runs = []
            except Exception:  # noqa: BLE001 — a corrupt artifact must not lose this run
                runs = []
        runs.append({
            "run_id": run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "ts": datetime.now(timezone.utc).isoformat(),
            "provider": active_provider(),
            "models": models,
            "usage_total": {r: u.model_dump() for r, u in totals.items()},
            "cost_usd": cost,
        })
        path.write_text(json.dumps(runs, indent=1))
    except Exception as exc:  # noqa: BLE001 — telemetry never breaks a run
        log.debug("usage summary skipped: %s", exc)
