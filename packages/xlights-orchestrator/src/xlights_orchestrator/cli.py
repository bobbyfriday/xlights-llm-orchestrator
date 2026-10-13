"""`xlo` CLI — the stage commands over a song's cache dir (claude-driven-orchestration D1/D8).

Each stage is file-in, file-out: `--song <mp3>` (the cache dir via the content hash) or
`--cache <dir>` names the song dir; the stage reads its prerequisites from it, writes its real
outputs back into it, prints a short summary to stdout, and exits non-zero naming the missing
prerequisite (exit 2, "missing <file>: run `xlo <stage>` first") or the failure (exit 1). No
stage calls a model API; `groups`, `apply`, and `finalize` talk to the running xLights.

    analyze        audio analysis + lyrics + instrumental subdivision → song_analysis.json, analysis_digest.md
    groups         live targetable-group probe → vocab.json, creative_brief.schema.json, layout.json
    validate-brief creative_brief.json × vocab × analysis → validation.json (exit 1 on errors)
    realize        brief → instructions.json (deterministic; refuses an invalid brief)
    apply          instructions.json → a clean-slate sequence in xLights → applied.json (--render)
    qa             instructions (+ the rendered .fseq when present) → qa.json
    stills         the rendered .fseq → stills/NN-<label>.png (hint when no render exists)
    finalize       save + close + patch the .xsq offline (audio, render order, timing tracks)
    video-plan     --plan-only: brief → media_plan.json (filmed vs procedural, before the story);
                   then video_story.json + media_plan.json → video_script.json + .md
    cache-rename   retrofit hash-named cache dirs to readable names
    init-layout    onboard an xLights layout: classify props → SEM_ groups + manifest
                   (--dry-run writes layout_review.json for the unresolved props)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sys
from pathlib import Path

from xlights_core import XLightsClient

from . import degradations
from .config import load_env
from .pipeline.media import safe_name
from .pipeline.stage_io import MissingInput

log = logging.getLogger(__name__)

EXIT_MISSING = 2      # a prerequisite file is absent (the message names it and its stage)
EXIT_FAILED = 1       # the stage ran and refused / failed (validation errors, xLights refusal)
MEDIA_PLAN_NAME = "media_plan.json"


# =============================================================================================
# stage commands
# =============================================================================================

def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _song_dir(args) -> Path:
    from .pipeline.stage_io import resolve_song_dir
    return resolve_song_dir(getattr(args, "song", None), getattr(args, "cache", None))


def _sequence_name(args, sa) -> str:
    """`--name`, else derived from the song filename (`--song`, else the analysis' path)."""
    from .pipeline.stage_io import song_path_of
    name = getattr(args, "name", None)
    return name or safe_name(song_path_of(getattr(args, "song", None), sa))


def _show_folder(args, layout: dict) -> str | None:
    return getattr(args, "show_folder", None) or (layout.get("show_folder") or None)


def _stage_analyze(args) -> int:
    from .pipeline import analyze_stage
    from .pipeline.digest import write_digest
    from .pipeline.stage_io import load_analysis
    if args.song:
        song_dir, sa, digest = analyze_stage.analyze_song(args.song, use_cache=not args.no_cache)
    else:                                   # --cache only: no audio to (re)analyze → digest only
        song_dir = _song_dir(args)
        sa = load_analysis(song_dir)
        digest = write_digest(song_dir, sa)
    stems = [f.stem for f in (getattr(sa, "stems", None) or [])]
    lines = len((getattr(sa, "lyrics", None) or {}).get("lines") or [])
    print(f"analysis: {sa.duration_s:.1f}s · {sa.tempo_overall or 0:.0f} bpm · "
          f"{len(sa.segments or [])} sections · stems: {', '.join(stems) or 'none'} · "
          f"{lines} timed lyric lines")
    print(f"digest: {digest} ({digest.stat().st_size / 1024:.1f} KB)")
    print(f"song dir: {song_dir}")
    return 0


async def _groups_live(sa) -> tuple[list[str], list[str], str | None]:
    from .pipeline.cache import cache_root
    from .pipeline.groups import targetable_groups
    async with XLightsClient() as client:
        groups = await targetable_groups(client, cache_root=cache_root())
        try:    # real MODEL names (not groups) for matrix-text discovery; best-effort
            models = list(await client.get_model_names())
        except Exception as exc:  # noqa: BLE001 — no model list → matrix text no-ops at realize
            log.info("model-name fetch skipped (matrix text disabled): %s", exc)
            models = []
        try:
            show_folder = await client.get_show_folder()
        except Exception as exc:  # noqa: BLE001 — no show folder → faces / .fseq lookup degrade
            degradations.note("finalize:media", exc, stage="groups")
            show_folder = None
    return groups, models, show_folder


def _stage_groups(args) -> int:
    from xlights_core.knowledge.colors import NAMED_COLORS
    from .pipeline.catalog import placeable_effect_types
    from .pipeline.cookbook import scene_ids
    from .pipeline.effect_meta import DURATION_CELLABLE
    from .pipeline.stage_io import load_analysis, write_layout
    from .pipeline.vocab import build_vocab, write_vocab_and_schema
    song_dir = _song_dir(args)
    sa = load_analysis(song_dir)            # the song's stems feed `follow_stem`
    groups, models, show_folder = asyncio.run(_groups_live(sa))
    vocab = build_vocab(groups=groups, effect_types=placeable_effect_types(),
                        cellable=sorted(DURATION_CELLABLE), scene_ids=scene_ids(),
                        stems=[f.stem for f in (getattr(sa, "stems", None) or [])],
                        colors=list(NAMED_COLORS))
    vocab_path, schema_path = write_vocab_and_schema(song_dir, vocab)
    layout_path = write_layout(song_dir, show_folder=show_folder, models=models)
    print(f"vocab: {len(vocab['groups'])} targetable groups · {len(vocab['effect_types'])} placeable "
          f"types ({len(vocab['cellable'])} cellable) · {len(vocab['scene_ids'])} scenes · "
          f"stems: {', '.join(vocab['stems']) or 'none'} · {len(vocab['colors'])} colors")
    print(f"layout: {len(models)} models · show folder: {show_folder or 'unknown'}")
    print(f"wrote {vocab_path.name}, {schema_path.name}, {layout_path.name} → {song_dir}")
    return 0


def _validate(song_dir: Path):
    """Validate the brief on disk; returns `(raw_brief, vocab, analysis, result)`. Shared by
    `validate-brief` and `realize` (which refuses an invalid brief)."""
    from .pipeline.stage_io import downbeats_ms, duration_ms, load_analysis, load_brief_json, require
    from .pipeline.validate_brief import validate_brief
    from .pipeline.vocab import VOCAB_NAME, load_vocab
    raw = load_brief_json(song_dir)
    require(song_dir / VOCAB_NAME)
    vocab = load_vocab(song_dir)
    sa = load_analysis(song_dir)
    res = validate_brief(raw, vocab, duration_ms=duration_ms(sa), downbeats_ms=downbeats_ms(sa))
    return raw, vocab, sa, res


def _stage_validate_brief(args) -> int:
    from .pipeline.validate_brief import summary_line, write_validation
    song_dir = _song_dir(args)
    _raw, _vocab, _sa, res = _validate(song_dir)
    path = write_validation(song_dir, res)
    print(summary_line(res))
    shown = (res.errors or res.warnings)[:3]
    for issue in shown:
        print(f"  {issue.path}: {issue.message}")
    print(f"wrote {path.name}" + ("" if len(res.errors) + len(res.warnings) <= len(shown)
                                 else f" ({len(res.errors)} errors, {len(res.warnings)} warnings)"))
    return 0 if res.ok else EXIT_FAILED


def _stage_realize(args) -> int:
    from xlights_core.knowledge.layout_manifest import load_manifest
    from .effect_emitter import clamp_layer_budget
    from .pipeline.cache import cache_root
    from .pipeline.generate import generate_instructions_from_brief
    from .pipeline.semantic_groups import derive_vocabulary
    from .pipeline.stage_io import load_layout, song_path_of, write_instructions
    from .pipeline.state import State
    from .pipeline.validate_brief import summary_line, write_validation
    from .show_plan import ShowPlan
    song_dir = _song_dir(args)
    raw, vocab, sa, res = _validate(song_dir)
    write_validation(song_dir, res)
    if not res.ok:                          # an invalid brief realizes nothing
        _err(f"refusing to realize: {summary_line(res)} (see validation.json)")
        return EXIT_FAILED
    layout = load_layout(song_dir)
    show_folder = _show_folder(args, layout)
    st = State(song_path=song_path_of(args.song, sa))
    st.song_analysis = sa
    st.show_plan = ShowPlan.model_validate(raw)
    st.available_groups = list(vocab["groups"])
    st.placeable_types = list(vocab["effect_types"])
    st.model_names = list(layout.get("models") or [])
    st.manifest = load_manifest(show_folder, cache_root=cache_root())
    st.vocab = derive_vocabulary(st.manifest)
    instrs = generate_instructions_from_brief(st)
    faces = []
    rgb = Path(show_folder) / "xlights_rgbeffects.xml" if show_folder else None
    if rgb is not None and rgb.exists():     # singing faces lip-sync to the vocals (deterministic)
        from .pipeline.faces import place_faces
        faces = place_faces(sa, rgb)
        instrs = list(instrs) + faces
    instrs, dropped = clamp_layer_budget(instrs)    # catalog rule #10: ≤4 layers
    path = write_instructions(song_dir, instrs)
    per: dict[int | None, int] = {}
    for i in instrs:
        per[i.section_index] = per.get(i.section_index, 0) + 1
    counts = [per.get(i, 0) for i in range(len(st.show_plan.sections))]
    print(f"realized {len(instrs)} effects over {len(counts)} sections "
          f"({min(counts) if counts else 0}–{max(counts) if counts else 0} per section) · "
          f"{len(faces)} faces · {dropped} trimmed by the layer budget"
          + (f" · {len(res.warnings)} brief warnings" if res.warnings else ""))
    print(f"wrote {path.name} → {song_dir}")
    return 0


async def _apply_live(instrs, *, duration_secs: int, render: bool, name: str) -> dict:
    from .effect_emitter import apply_instructions
    async with XLightsClient() as client:
        rep = await apply_instructions(client, instrs, duration_secs=duration_secs, render=render)
        if render:                          # the .fseq exists only once the sequence is saved
            await client.save_sequence(name)
    rep["saved"] = bool(render)
    return rep


def _stage_apply(args) -> int:
    from xlights_core.editing import CleanSlateRequired
    from .pipeline.stage_io import load_analysis, load_instructions, write_applied
    song_dir = _song_dir(args)
    instrs = load_instructions(song_dir)
    sa = load_analysis(song_dir)
    name = _sequence_name(args, sa)
    dur = max(1, math.ceil(float(sa.duration_s or 0)))
    try:
        rep = asyncio.run(_apply_live(instrs, duration_secs=dur, render=args.render, name=name))
    except CleanSlateRequired as exc:
        _err(f"apply refused: {exc}")
        return EXIT_FAILED
    placed, skipped = rep.get("placed", []), rep.get("skipped", [])
    applied = {
        "sequence": name, "rendered": bool(rep.get("rendered")), "saved": bool(rep.get("saved")),
        "counts": {"instructions": len(instrs), "placed": len(placed), "skipped": len(skipped)},
        "placed": placed, "skipped": skipped, "outcomes": rep.get("outcomes", []),
    }
    path = write_applied(song_dir, applied)
    print(f"placed {len(placed)} · skipped {len(skipped)} of {len(instrs)} instructions"
          + (f" · rendered + saved as '{name}'" if rep.get("saved") else " · not rendered"))
    reasons: dict[str, int] = {}
    for s in skipped:
        key = str(s.get("reason", "")).split(":")[0] or "unknown"
        reasons[key] = reasons.get(key, 0) + 1
    for key, n in sorted(reasons.items(), key=lambda kv: -kv[1])[:3]:
        print(f"  skipped {n}: {key}")
    print(f"wrote {path.name} → {song_dir}")
    return 0


def _stage_qa(args) -> int:
    from xlights_core.knowledge.layout_manifest import load_manifest
    from . import qa as qa_mod
    from .pipeline.cache import cache_root
    from .pipeline.stage_io import (fseq_series, load_analysis, load_applied, load_brief,
                                    load_instructions, load_layout, locate_fseq)
    from .pipeline.vocab import VOCAB_NAME, load_vocab
    from .show_plan import repetition_map_from_labels
    song_dir = _song_dir(args)
    instrs = load_instructions(song_dir)
    sa = load_analysis(song_dir)
    plan = load_brief(song_dir)
    applied = load_applied(song_dir)
    groups = load_vocab(song_dir)["groups"] if (song_dir / VOCAB_NAME).exists() else []
    if not groups:
        groups = sorted({i.target for i in instrs})
    layout = load_layout(song_dir)
    show_folder = _show_folder(args, layout)
    name = _sequence_name(args, sa)
    fseq = locate_fseq(name, show_folder)
    series = fseq_series(fseq, show_folder, groups) if fseq else None
    manifest = load_manifest(show_folder, cache_root=cache_root())
    if applied is None:                     # not applied yet → placement judged on the plan alone
        applied = {"placed": [{"section_index": i.section_index} for i in instrs], "skipped": []}
    report = qa_mod.evaluate(instrs, sa, plan, applied, groups,
                             repetition_map=repetition_map_from_labels(plan.sections) or None,
                             fseq_series=series, manifest=manifest)
    path = qa_mod.write_qa(song_dir, report)
    sev = {"error": 0, "warn": 0, "info": 0}
    for f in report.findings:
        sev[f.severity] = sev.get(f.severity, 0) + 1
    print(f"qa: objective {report.objective_score}/100 · advisory {report.advisory_score}/100 · "
          f"{len(report.findings)} findings ({sev['error']} error, {sev['warn']} warn, {sev['info']} info)"
          f" · rendered series: {'yes' if series is not None else 'no'}")
    order = {"error": 0, "warn": 1, "info": 2}
    for f in sorted(report.findings, key=lambda f: order.get(f.severity, 3))[:3]:
        print(f"  [{f.severity}/{f.metric}] {f.scope}: {f.detail}")
    print(f"wrote {path.name} → {song_dir}")
    return 0


def _stage_stills(args) -> int:
    from ._fmt import mmss
    from .pipeline.stage_io import (STILLS_DIR, fseq_series, load_analysis, load_brief,
                                    load_layout, locate_fseq)
    from .pipeline.stills import render_stills, still_times
    from .pipeline.vocab import VOCAB_NAME, load_vocab
    song_dir = _song_dir(args)
    plan = load_brief(song_dir)
    sa = load_analysis(song_dir)
    layout = load_layout(song_dir)
    show_folder = _show_folder(args, layout)
    name = _sequence_name(args, sa)
    fseq = locate_fseq(name, show_folder)
    if fseq is None:
        print(f"no rendered .fseq for '{name}' — run: xlo apply --render")
        return 0
    if not show_folder:
        _err("no show folder known for the layout files — run `xlo groups` with xLights running, "
             "or pass --show-folder")
        return EXIT_FAILED
    groups = load_vocab(song_dir)["groups"] if (song_dir / VOCAB_NAME).exists() else None
    series = fseq_series(fseq, show_folder, groups)
    out_dir = song_dir / STILLS_DIR
    paths = render_stills(fseq, show_folder, plan.sections, out_dir, series=series)
    times = still_times(plan.sections, series)
    print(f"{len(paths)} stills from {fseq.name} → {out_dir}")
    for p, t in zip(paths, times):
        print(f"  {p.name}  @ {mmss(t)}")
    return 0


async def _finalize_live(st, *, name: str, song_path: str, fallback_show_folder: str | None,
                         timing_tracks: bool):
    from .pipeline.finalize import finalize_sequence
    from .pipeline.media import prepare_media
    async with XLightsClient() as client:
        show_folder: str | None
        try:
            show_folder = await client.get_show_folder()
        except Exception as exc:  # noqa: BLE001 — fall back to what `xlo groups` recorded
            degradations.note("finalize:media", exc, stage="finalize")
            show_folder = fallback_show_folder
        media = prepare_media(song_path, show_folder)
        await finalize_sequence(st, client=client, save_as=name, media=media,
                                show_folder=show_folder,
                                duration_s=st.song_analysis.duration_s, timing_tracks=timing_tracks)
    return media, show_folder


def _stage_finalize(args) -> int:
    from .pipeline.stage_io import load_analysis, load_brief, load_layout, song_path_of
    from .pipeline.state import State
    song_dir = _song_dir(args)
    sa = load_analysis(song_dir)
    plan = load_brief(song_dir)
    song_path = song_path_of(args.song, sa)
    name = _sequence_name(args, sa)
    st = State(song_path=song_path)
    st.song_analysis, st.show_plan = sa, plan
    media, show_folder = asyncio.run(_finalize_live(
        st, name=name, song_path=song_path, fallback_show_folder=_show_folder(args, load_layout(song_dir)),
        timing_tracks=not args.no_timing_tracks))
    print(f"saved '{name}' · audio: {'attached' if media else 'not staged'} · "
          f"timing tracks: {'off' if args.no_timing_tracks else 'on'} · "
          f"show folder: {show_folder or 'unknown'}")
    print(f"Open '{name}' in xLights to play it with audio (File → Open Sequence).")
    return 0


# The Veo clip parameters the media planner budgets with (formerly `video.veo` in the deleted
# models/config.yaml): clip length (s), how far a clip may be stretched, one Gemini project's
# daily clip quota, the timezone that quota resets in, and the per-second price (None = unpriced).
VEO_DEFAULTS = {"clip_s": 8.0, "max_stretch": 1.2, "daily_clips": 10,
                "quota_reset_tz": "America/Los_Angeles", "per_second_usd": None}


def _veo_defaults() -> dict:
    return dict(VEO_DEFAULTS)


def _media_budget(args, veo: dict):
    """The Veo campaign budget from the flags (`--veo-clips`, `--no-veo`, `--filmed-sections`)."""
    from .media_plan import MediaBudget
    pinned = [int(x) for x in args.filmed_sections.split(",") if x.strip()] if args.filmed_sections else []
    campaign = 0 if args.no_veo else (int(veo["daily_clips"]) if args.veo_clips is None else int(args.veo_clips))
    if campaign < 0:
        raise ValueError(f"--veo-clips must be >= 0, got {campaign}")
    return MediaBudget(campaign_clips=campaign, clip_s=float(veo["clip_s"]),
                       max_stretch=float(veo["max_stretch"]), pinned=pinned)


def _load_media_plan(song_dir: Path, n_sections: int):
    """`media_plan.json` from a `--plan-only` pass, when it exists and still fits the brief."""
    from .media_plan import MediaPlan
    p = song_dir / MEDIA_PLAN_NAME
    if not p.exists():
        return None
    try:
        media = MediaPlan.model_validate_json(p.read_text())
    except Exception as exc:  # noqa: BLE001 — a stale/foreign file → recompute
        log.info("%s unreadable, recomputing the media plan: %s", MEDIA_PLAN_NAME, exc)
        return None
    return media if len(media.sections) == n_sections else None


def _stage_video_plan(args) -> int:
    from . import veo_ledger
    from .media_plan import featured_hits
    from .pipeline.stage_io import (STORY_NAME, VIDEO_SCRIPT_NAME, downbeats_ms, load_analysis,
                                    load_brief, load_story_json, song_path_of)
    from .pipeline.video import parse_size, song_title
    from .video_script import (VideographerOut, featured_lines_for, lyric_lines, plan_media_for,
                               plan_story, render_markdown, validate_story)
    if not args.plan_only and not args.matrix_size:
        _err("--matrix-size is required (e.g. 1024x768); the script will not guess the video "
             "matrix's resolution")
        return EXIT_FAILED
    song_dir = _song_dir(args)
    plan = load_brief(song_dir)
    sa = load_analysis(song_dir)
    sections = [(int(s.start_ms), int(s.end_ms)) for s in plan.sections]
    labels = [s.label or "" for s in plan.sections]
    energies = [float(s.intensity or 0.0) for s in plan.sections]
    lyrics = lyric_lines(((sa.lyrics if isinstance(sa.lyrics, dict) else {}) or {}).get("lines") or [])
    featured = featured_hits(featured_lines_for(plan, sa), lyrics, sections)
    veo = _veo_defaults()
    budget = _media_budget(args, veo)
    remaining = veo_ledger.remaining_today(int(veo["daily_clips"]), str(veo["quota_reset_tz"]))

    # 1. the media plan comes FIRST (the story is written per section medium): `--plan-only`
    #    writes it with no story; the full run reuses it when it still fits the brief.
    media = None if args.plan_only else _load_media_plan(song_dir, len(sections))
    if media is None:
        media = plan_media_for(sections=sections, labels=labels, energies=energies, featured=featured,
                               budget=budget, ledger_remaining=remaining,
                               per_second_usd=veo.get("per_second_usd"))
    if args.plan_only:
        (song_dir / MEDIA_PLAN_NAME).write_text(media.model_dump_json(indent=1))
        filmed = [s.index for s in media.sections if s.medium == "filmed"]
        print(f"media plan: {len(filmed)} filmed / {len(media.sections) - len(filmed)} procedural "
              f"sections · {media.clips_planned} Veo clip(s) of {budget.campaign_clips} · "
              f"filmed sections: {', '.join(str(i) for i in filmed) or 'none'}")
        print(f"wrote {MEDIA_PLAN_NAME} → {song_dir}  (now write {STORY_NAME}, then `xlo video-plan`)")
        return 0

    # 2. the written story, validated strictly (one beat per section unless --allow-inherit)
    raw = load_story_json(song_dir)
    problems = validate_story(raw, len(sections), allow_inherit=args.allow_inherit)
    if problems:
        _err(f"{STORY_NAME} can't be planned ({len(problems)} problem{'s' if len(problems) != 1 else ''}):")
        for p in problems:
            _err(f"  - {p}")
        return EXIT_FAILED
    story = VideographerOut.model_validate(raw)
    width, height = parse_size(args.matrix_size)
    palette = list((plan.palette.colors if plan.palette else []) or [])
    title = song_title(json.loads(sa.model_dump_json()), song_path_of(args.song, sa))
    vs, media = plan_story(story, song=title, sections=sections, labels=labels, energies=energies,
                           lyrics=lyrics, downbeats_ms=downbeats_ms(sa), width=width, height=height,
                           frame_ms=args.frame_ms, max_shot_s=args.max_shot_s, media=media,
                           palette=palette, source=f"{STORY_NAME}, {MEDIA_PLAN_NAME}, "
                                                   f"creative_brief.json, song_analysis.json")
    (song_dir / VIDEO_SCRIPT_NAME).write_text(vs.model_dump_json(indent=1))
    (song_dir / MEDIA_PLAN_NAME).write_text(media.model_dump_json(indent=1))
    md = song_dir / "video_script.md"
    md.write_text(render_markdown(vs))
    m = vs.media
    inherited = len({sh.section_index for sh in vs.shots if sh.inherited})
    print(f"video plan: {len(vs.shots)} shots · {m.filmed_sections} filmed / {m.procedural_sections} "
          f"procedural sections · {m.clips_planned} Veo clip(s) of {m.campaign_clips}"
          + (f" · {inherited} inherited beat(s)" if inherited else "")
          if m else f"video plan: {len(vs.shots)} shots")
    print(f"wrote {VIDEO_SCRIPT_NAME}, video_script.md, {MEDIA_PLAN_NAME} → {song_dir}")
    return 0


STAGES = {
    "analyze": _stage_analyze,
    "groups": _stage_groups,
    "validate-brief": _stage_validate_brief,
    "realize": _stage_realize,
    "apply": _stage_apply,
    "qa": _stage_qa,
    "stills": _stage_stills,
    "finalize": _stage_finalize,
    "video-plan": _stage_video_plan,
}


def _run_stage(args) -> None:
    """Run one stage with the degradations collector installed; map the file-contract errors to
    exit codes (2 = missing prerequisite, 1 = refused/failed) with the message on stderr."""
    dl = degradations.start_run()
    try:
        code = STAGES[args.cmd](args)
    except MissingInput as exc:
        _err(str(exc))
        raise SystemExit(EXIT_MISSING) from exc
    except (FileNotFoundError, ValueError) as exc:
        _err(str(exc))
        raise SystemExit(EXIT_FAILED) from exc
    finally:
        if dl.summary():                    # the best-effort losses, after the summary
            _err(degradations.render_summary(dl))
    if code:
        raise SystemExit(code)


# =============================================================================================
# argparse
# =============================================================================================

def _song_args(p: argparse.ArgumentParser, *, song_help: str = "path to the audio file") -> None:
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--song", default=None, help=song_help)
    g.add_argument("--cache", default=None, help="the song's cache dir (instead of --song)")


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="xlo", description="xLights show orchestrator — stage commands")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # -- stages ------------------------------------------------------------------------------
    a = sub.add_parser("analyze", help="audio analysis + lyrics + digest → song_analysis.json, analysis_digest.md")
    _song_args(a, song_help="path to the audio file (--cache alone only regenerates the digest)")
    a.add_argument("--no-cache", action="store_true", help="re-analyze the audio (ignore the cached analysis)")

    g = sub.add_parser("groups", help="probe targetable groups (live xLights) → vocab.json + brief schema")
    _song_args(g)

    v = sub.add_parser("validate-brief", help="check creative_brief.json → validation.json (exit 1 on errors)")
    _song_args(v)

    r = sub.add_parser("realize", help="brief → instructions.json (deterministic, no model)")
    _song_args(r)
    r.add_argument("--show-folder", default=None,
                   help="show folder for singing faces / the layout manifest (default: from layout.json)")

    ap_ = sub.add_parser("apply", help="emit instructions.json into a clean-slate sequence → applied.json")
    _song_args(ap_)
    ap_.add_argument("--name", default=None, help="sequence name (default: derived from the song filename)")
    ap_.add_argument("--render", action="store_true",
                     help="also render the sequence and save it (writes the .fseq for `xlo stills`/`xlo qa`)")

    q = sub.add_parser("qa", help="deterministic QA over instructions (+ the rendered .fseq) → qa.json")
    _song_args(q)
    q.add_argument("--name", default=None, help="sequence name whose .fseq to read (default: from the song)")
    q.add_argument("--show-folder", default=None, help="show folder (default: from layout.json)")

    s = sub.add_parser("stills", help="one preview PNG per section from the rendered .fseq → stills/")
    _song_args(s)
    s.add_argument("--name", default=None, help="sequence name whose .fseq to read (default: from the song)")
    s.add_argument("--show-folder", default=None, help="show folder (default: from layout.json)")

    f = sub.add_parser("finalize", help="save the open sequence, then patch the .xsq offline (audio, timing)")
    _song_args(f)
    f.add_argument("--name", default=None, help="sequence name (default: derived from the song filename)")
    f.add_argument("--no-timing-tracks", action="store_true",
                   help="don't add reference timing tracks (sections/beats/bars/onsets) to the .xsq")

    vp = sub.add_parser("video-plan", help="media-plan the brief (--plan-only), then time the written "
                                           "video_story.json → video_script.json + .md")
    _song_args(vp)
    vp.add_argument("--plan-only", action="store_true",
                    help="write media_plan.json (which sections are filmed vs procedural) from the brief "
                         "and analysis alone — run BEFORE writing video_story.json")
    vp.add_argument("--allow-inherit", action="store_true",
                    help="accept a story missing beats for some sections (they hold the previous beat); "
                         "default: strict, one beat per brief section")
    vp.add_argument("--matrix-size", default=None,
                    help="video matrix resolution, e.g. 1024x768 (required — never guessed)")
    vp.add_argument("--frame-ms", type=int, default=50, help="sequence frame interval (default 50 → 20 fps)")
    vp.add_argument("--max-shot-s", type=float, default=None,
                    help="filmed clip length override: split FILMED shots longer than this on downbeats "
                         "(default: the configured Veo clip length × stretch; procedural shots never split)")
    vp.add_argument("--veo-clips", type=int, default=None, metavar="N",
                    help="campaign clip budget the story may assume will be filmed (default: one day's quota)")
    vp.add_argument("--no-veo", action="store_true", help="plan an all-procedural film (budget 0)")
    vp.add_argument("--filmed-sections", default=None, metavar="I,J",
                    help="section indexes to film first, e.g. 3,6 (then the budget is spent by value)")

    cr = sub.add_parser("cache-rename",
                        help="retrofit hash-named cache dirs to readable <song>--<hash> names")
    cr.add_argument("--songs", action="append", default=None, metavar="DIR",
                    help="extra dir of audio files to match hashes against (repeatable; "
                         "default: . and mp3/)")
    cr.add_argument("--apply", action="store_true", help="do the renames (default: dry run)")

    il = sub.add_parser("init-layout",
                        help="onboard an xLights layout: classify props → SEM_ groups + manifest")
    il.add_argument("--show-folder", default=None, help="show folder (with xlights_rgbeffects.xml)")
    il.add_argument("--dry-run", action="store_true",
                    help="print the diff + manifest and write only layout_review.json (the unresolved "
                         "props to classify into layout_overrides.json); the layout is not touched")
    il.add_argument("--yes", action="store_true", help="accept all review suggestions unattended")
    il.add_argument("--no-validate", action="store_true", help="skip the offline §7 validation")
    il.add_argument("--invert-x", action="store_true", help="flip the x axis (inverted preview)")
    il.add_argument("--review-web", action="store_true", help="(reserved) browser review UX")

    return ap


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    load_env()
    if args.cmd in STAGES:
        _run_stage(args)
        return
    if args.cmd == "cache-rename":      # offline file housekeeping — no xLights
        from .pipeline import cache_rename
        dirs = [Path(d).expanduser() for d in (args.songs or [".", "mp3"])]
        print(cache_rename.run(dirs, do_apply=args.apply))
        return
    if args.cmd == "init-layout":
        # no running-xLights requirement (it needs xLights CLOSED).
        from .pipeline.init_layout import run_init_layout
        raise SystemExit(asyncio.run(run_init_layout(args)))


if __name__ == "__main__":
    main()
