"""`xlo` CLI — drive the orchestration pipeline."""

from __future__ import annotations

import argparse
import asyncio

from xlights_core import XLightsClient

from .config import has_llm_key, load_env
from .pipeline import run_pipeline
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


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="xlo", description="xLights LLM orchestrator")
    sub = ap.add_subparsers(dest="cmd", required=True)
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
    args = ap.parse_args(argv)

    load_env()
    if args.cmd == "run":
        if not has_llm_key():
            raise SystemExit(
                "No LLM key found. Set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env"
            )
        asyncio.run(_run(args))


if __name__ == "__main__":
    main()
