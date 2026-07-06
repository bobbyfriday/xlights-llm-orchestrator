"""`xlo` CLI — drive the orchestration pipeline."""

from __future__ import annotations

import argparse
import asyncio

from xlights_core import XLightsClient

from .config import has_llm_key, load_env
from .pipeline import format_sections, regen_section, run_pipeline
from .pipeline.media import safe_name
from .pipeline.run import _auto_checkpoint, _design_review, _interpret_review


async def _run(args) -> None:
    async with XLightsClient() as client:
        st = await run_pipeline(
            args.song,
            client=client,
            save_as=None if args.no_save else (args.name or safe_name(args.song)),
            use_cache=not args.no_cache,
            refine=args.refine,
            max_iterations=args.max_iterations,
            log_revisions=not args.no_log,
            timing_tracks=not args.no_timing_tracks,
            interpret_checkpoint=None if args.auto else _interpret_review,
            design_checkpoint=None if args.auto else _design_review,
            checkpoint=_auto_checkpoint if (args.refine and args.auto) else None,
        )
    rep = st.applied or {}
    print(f"\nShowPlan: {len(st.show_plan.sections)} sections")
    print(f"placed: {len(rep.get('placed', []))}   skipped: {len(rep.get('skipped', []))}")
    for p in rep.get("placed", [])[:25]:
        print(f"  + {p['effect']:<14} → {p['target']}  ({p['start_ms']}-{p['end_ms']}ms, L{p['layer']})")
    name = args.name or safe_name(args.song)
    print(f"\nOpen '{name}' in xLights to play it with audio (File → Open Sequence).")


async def _regen(args) -> None:
    async with XLightsClient() as client:
        st = await regen_section(
            args.song, client=client, section_index=args.section, note=args.note or "",
            save_as=None if args.no_save else (args.name or safe_name(args.song)),
        )
    n = sum(1 for i in st.instructions if i.section_index == args.section)
    print(f"\nRegenerated section {args.section}: {n} effects (other sections unchanged).")
    name = args.name or safe_name(args.song)
    print(f"Open '{name}' in xLights to play it with audio (File → Open Sequence).")


def _report(args) -> None:
    """Deterministic offline cost/quality dashboard over the revision logs. No LLM, no xLights,
    no network — and NO has_llm_key() gate."""
    from pathlib import Path

    from . import reporting
    from .pipeline.cache import cache_root, song_key

    root = Path(args.cache_dir) / "orchestrator" if args.cache_dir else cache_root()
    song = song_key(args.song) if args.song else None
    if not reporting.discover_logs(root) and (song is None):
        print(f"no revision logs found under {root}")
        return
    rep = reporting.build_report(root, song=song, reprice=args.reprice)
    if not rep.runs:
        print(f"no revision logs found under {root}")
        return
    if args.json:
        print(rep.model_dump_json(indent=1))
        return
    if args.html is not None:
        out = Path(args.html) if args.html else (root / "report.html")
        out.write_text(reporting.render_html(rep))
        print(f"wrote {out}")
        return
    print(reporting.render_text(rep), end="")


def _edit_brief(args) -> None:
    from pathlib import Path
    from .brief_editor import serve
    from .pipeline.run import _cache_path, _song_key
    if args.brief:
        brief = Path(args.brief)
    elif args.song:
        brief = _cache_path(_song_key(args.song), "creative_brief")
    else:
        raise SystemExit("edit-brief needs --song or --brief")
    if not brief.exists():
        raise SystemExit(f"no creative brief at {brief} — run `xlo run` for this song first")
    serve(brief, open_browser=not args.no_open)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="xlo", description="xLights LLM orchestrator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("edit-brief", help="open the creative brief in a browser form (dropdowns/colors)")
    e.add_argument("--song", default=None, help="song whose cached brief to edit")
    e.add_argument("--brief", default=None, help="path to a creative_brief.json (overrides --song)")
    e.add_argument("--no-open", action="store_true", help="don't auto-open the browser")
    r = sub.add_parser("run", help="generate a sequence for a song")
    r.add_argument("--song", required=True, help="path to an audio file")
    r.add_argument("--name", default=None, help="sequence name (default: derived from the song filename)")
    r.add_argument("--no-save", action="store_true", help="don't save (leave unsaved/open)")
    r.add_argument("--no-cache", action="store_true", help="ignore cached plan/instructions")
    r.add_argument("--refine", action="store_true", help="run the test→judge→refine loop")
    r.add_argument("--auto", action="store_true", help="unattended refine (no human checkpoints)")
    r.add_argument("--max-iterations", type=int, default=3, help="hard cap on refine iterations")
    r.add_argument("--no-log", action="store_true", help="disable the per-iteration revision log")
    r.add_argument("--no-timing-tracks", action="store_true",
                   help="don't add reference timing tracks (sections/beats/bars/onsets) to the .xsq")
    g = sub.add_parser("regen", help="regenerate ONE section of a generated show, leaving the rest intact")
    g.add_argument("--song", required=True, help="path to the audio file (must have been `xlo run` first)")
    g.add_argument("--section", type=int, default=None, help="section index to regenerate (see --list)")
    g.add_argument("--list", action="store_true", help="list the show's sections (index, time, look) and exit")
    g.add_argument("--note", default=None, help="free-text fix to steer the regen (e.g. 'too busy, calm it down')")
    g.add_argument("--name", default=None, help="sequence name (default: derived from the song filename)")
    g.add_argument("--no-save", action="store_true", help="don't save (re-emit only, leave unsaved/open)")
    rp = sub.add_parser("report", help="offline cost & quality dashboard over the revision logs")
    rp.add_argument("--song", default=None, help="limit to one song (path); default: all songs")
    rp.add_argument("--cache-dir", default=None, help="cache dir (default: $XLO_CACHE_DIR or ./data)")
    rp.add_argument("--html", nargs="?", const="", default=None,
                    help="write a self-contained HTML page (optional PATH; default: <root>/report.html)")
    rp.add_argument("--json", action="store_true", help="emit the Report as JSON")
    rp.add_argument("--reprice", action="store_true", help="recompute cost from the current price table")
    args = ap.parse_args(argv)

    load_env()
    if args.cmd == "report":            # offline, deterministic — NO has_llm_key() gate
        _report(args)
        return
    if args.cmd == "edit-brief":
        _edit_brief(args)
        return
    if args.cmd == "run":
        if not has_llm_key():
            raise SystemExit(
                "No LLM key found. Set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env"
            )
        asyncio.run(_run(args))
    if args.cmd == "regen":
        if args.list or args.section is None:
            try:
                print(f"Sections for {args.song}:\n{format_sections(args.song)}")
            except FileNotFoundError as exc:
                raise SystemExit(str(exc))
            return
        if not has_llm_key():
            raise SystemExit("No LLM key found. Set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env")
        try:
            asyncio.run(_regen(args))
        except (FileNotFoundError, IndexError) as exc:
            raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
