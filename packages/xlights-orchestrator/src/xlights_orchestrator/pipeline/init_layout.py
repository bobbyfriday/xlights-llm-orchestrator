"""F-E slice 4 — the guided `xlo init-layout` flow (design decision 13).

Seven steps: locate → analyze → review → plan+diff → write → validate → finish. Runs fully
deterministically with no LLM key (steps 1–4) and does NOT require xLights running — it requires
xLights CLOSED for the write step (the closed guard), because xLights rewrites rgbeffects.xml from
memory on exit and would clobber an offline edit.

The heavy lifting lives in xlights-core (classify/derive/build/write/manifest) + the orchestrator's
validate/LLM-fallback modules; this is the thin conductor, structured so the whole flow is
hermetically testable by injecting `prompt`/`out` and stubbing the write/validate steps.
"""

from __future__ import annotations

import json
from pathlib import Path

from xlights_core.knowledge.layout_classify import (
    apply_overrides,
    classify,
    derive_spatial,
    parse_props,
)
from xlights_core.knowledge.layout_manifest import (
    build_manifest,
    emit_manifest,
    plan_diff,
    read_sem_groups,
)
from xlights_core.knowledge.layout_semantics import build_sem_groups, layout_modes, write_sem_groups

REVIEW_CONF = 0.8              # props below this go to the review queue (spec §3.5/§7.4)
_OVERRIDES_NAME = "layout_overrides.json"


# ------------------------------------------------------------------------------------------------
# the closed guard (spec §5.5 / design decision 8)
# ------------------------------------------------------------------------------------------------
async def is_xlights_running(*, timeout: float = 1.0) -> bool:
    """A cheap connectivity probe: if the automation port answers a version request, xLights is up."""
    from xlights_core import XLightsClient
    try:
        async with XLightsClient(timeout=timeout) as client:
            await client.get_version()
        return True
    except Exception:  # noqa: BLE001 — any connect/timeout/HTTP error = not reachable = closed
        return False


# ------------------------------------------------------------------------------------------------
# the deterministic analyze step (pure — the hermetic core)
# ------------------------------------------------------------------------------------------------
class LayoutPlan:
    """The result of analyzing a layout: classified props, the SEM_ plan, the manifest, the diff."""

    def __init__(self, props, result, summary, plan, manifest, diff, review):
        self.props = props
        self.result = result
        self.summary = summary
        self.plan = plan
        self.manifest = manifest
        self.diff = diff
        self.review = review


def _load_overrides(show_folder: Path) -> dict:
    p = show_folder / _OVERRIDES_NAME
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (ValueError, OSError):
            return {}
    return {}


def analyze_layout(rgb_path, *, invert_x: bool = False, overrides: dict | None = None) -> LayoutPlan:
    """Steps 1–4 (deterministic): parse → classify → apply overrides → derive spatial → build the
    SEM_ plan + manifest → diff against the file. No LLM, no xLights."""
    props = parse_props(rgb_path)
    result = classify(props)
    if overrides:
        apply_overrides(result, overrides)
    summary = derive_spatial(props, invert_x=invert_x)
    plan = build_sem_groups(props)
    modes = layout_modes(plan)
    manifest = build_manifest(result, summary, plan, modes=modes)
    diff = plan_diff(read_sem_groups(rgb_path), plan)
    review = list(manifest.review)
    return LayoutPlan(props, result, summary, plan, manifest, diff, review)


# ------------------------------------------------------------------------------------------------
# the terminal review queue (spec §7.4)
# ------------------------------------------------------------------------------------------------
def review_queue(plan: LayoutPlan, *, ask, yes: bool = False) -> None:
    """Present every prop below REVIEW_CONF (and each excluded outlier) for resolution. `ask` is an
    input callable (name, current_role, choices) -> chosen str; `--yes` accepts the suggestion.
    Unresolved items stay in the manifest's `review` array (never silently written into a group)."""
    from xlights_core.knowledge.layout_classify import capability
    by_name = {p.name: p for p in plan.props}
    resolved: set[str] = set()
    for name in list(plan.review):
        if yes:                                          # --yes keeps the suggestion; still in review
            continue
        p = by_name.get(name)
        cur = p.role if p is not None else "CUSTOM_PROP"
        choice = ask(name, cur, ("accept", "exclude"))
        if not choice or choice == "accept" or choice == "exclude":
            continue                                     # accept keeps the current role; exclude skips
        if p is not None:                                # a forced role from the enum
            p.role = choice
            p.confidence = 1.0
            p.res = capability(p.role, p.nodes, p.string_type)
            resolved.add(name)
    # rebuild plan/manifest if a review changed roles
    if resolved:
        plan.plan = build_sem_groups(plan.props)
        plan.manifest = build_manifest(plan.result, plan.summary, plan.plan,
                                       modes=layout_modes(plan.plan))
        plan.review = [n for n in plan.manifest.review]


# ------------------------------------------------------------------------------------------------
# the write + finish steps
# ------------------------------------------------------------------------------------------------
def format_diff(diff) -> str:
    """Human-readable three-way diff (empty when converged)."""
    if not diff:
        return "  (no membership differences — converged)"
    lines = []
    for name, gd in sorted(diff.items()):
        lines.append(f"  {name}:")
        if gd.only_in_file:
            lines.append(f"    - only in file: {', '.join(gd.only_in_file)}")
        if gd.only_in_plan:
            lines.append(f"    + only in plan: {', '.join(gd.only_in_plan)}")
        if gd.order_changed:
            lines.append("    ~ member order changed")
    return "\n".join(lines)


def write_and_emit(rgb_path, plan: LayoutPlan, show_folder, *, cache_root=None, backup=True):
    """Write the SEM_ groups + the canonical view, then emit the manifest. Returns (WriteReport,
    manifest_path). The caller enforces the closed guard BEFORE calling this."""
    from xlights_core.knowledge.layout_semantics import patch_view
    report = write_sem_groups(rgb_path, plan.plan, modes=layout_modes(plan.plan), backup=backup)
    patch_view(rgb_path)                                  # the canonical-order "SEM Master" view
    manifest_path = emit_manifest(plan.manifest, show_folder, cache_root=cache_root)
    return report, manifest_path


# ------------------------------------------------------------------------------------------------
# the top-level conductor
# ------------------------------------------------------------------------------------------------
def _locate_show_folder(args, *, prompt=input) -> Path | None:
    if getattr(args, "show_folder", None):
        return Path(args.show_folder)
    # try a running xLights (best-effort, non-blocking to the guard)
    import asyncio

    from xlights_core import XLightsClient

    async def _ask():
        try:
            async with XLightsClient(timeout=1.0) as c:
                folder = await c.get_show_folder()
            return folder or None
        except Exception:  # noqa: BLE001
            return None
    folder = asyncio.run(_ask())
    if folder:
        return Path(folder)
    entered = prompt("Show folder path (containing xlights_rgbeffects.xml): ").strip()
    return Path(entered) if entered else None


def _terminal_ask(name, cur, choices):
    """Default terminal review prompt: accept the suggestion, exclude, or type a role."""
    resp = input(f"  [{name}] classified {cur} — [Enter]=accept / 'exclude' / a role name: ").strip()
    return resp or "accept"


async def run_init_layout(args) -> int:
    """The guided flow. Returns a process exit code (0 ok; 1 needs re-run / warning)."""
    from .cache import cache_root as _cache_root

    out = print
    show_folder = _locate_show_folder(args)
    if show_folder is None:
        out("No show folder given. Re-run with --show-folder PATH.")
        return 1
    rgb = show_folder / "xlights_rgbeffects.xml"
    if not rgb.exists():
        out(f"No xlights_rgbeffects.xml in {show_folder}.")
        return 1

    # 2. analyze (deterministic) + overrides
    overrides = _load_overrides(show_folder)
    plan = analyze_layout(rgb, invert_x=getattr(args, "invert_x", False), overrides=overrides)
    out(f"Classified {len(plan.props)} props into {len(plan.plan)} SEM_ groups "
        f"({len(plan.review)} to review).")

    # 2b. optional LLM fallback for the unresolved tail (skipped in --dry-run — deterministic only)
    from ..config import has_llm_key
    if (not getattr(args, "dry_run", False) and not getattr(args, "no_llm", False)
            and has_llm_key() and plan.result.unresolved):
        try:
            from ..agents.layout_classifier import classify_tail
            await classify_tail(plan.result.unresolved)
            plan = analyze_layout(rgb, invert_x=getattr(args, "invert_x", False),
                                  overrides=overrides)   # re-derive with resolved roles
        except Exception as exc:  # noqa: BLE001 — the fallback is optional
            out(f"LLM fallback skipped: {exc}")

    # 3. review
    if plan.review and not getattr(args, "dry_run", False):
        review_queue(plan, ask=_terminal_ask, yes=getattr(args, "yes", False))

    # 4. plan + diff
    out("Membership diff vs the current file:\n" + format_diff(plan.diff))

    # 5. dry-run stops here
    if getattr(args, "dry_run", False):
        out("(dry-run) no files written.")
        if plan.review:
            out(f"WARNING: {len(plan.review)} props still need review.")
        return 0

    # 5b. closed guard
    if await is_xlights_running():
        out("xLights is running — close it and re-run (it would clobber the offline edit on exit).")
        return 1

    # 6. write + manifest
    report, manifest_path = write_and_emit(rgb, plan, show_folder, cache_root=_cache_root())
    if report.changed:
        out(f"Wrote {len(report.created) + len(report.replaced)} SEM_ groups; backup {report.backup}.")
    else:
        out("SEM_ groups already up to date (no write).")
    out(f"Manifest: {manifest_path}")

    # 6b. validate (offline §7) — best-effort; needs networks.xml + the [preview] extra.
    if not getattr(args, "no_validate", False):
        try:
            _run_validation(rgb, show_folder, plan, out=out)
        except Exception as exc:  # noqa: BLE001 — validation is advisory here, not a hard gate
            out(f"validation skipped: {exc}")

    # 7. finish
    if plan.review:
        out(f"WARNING: manifest ships with {len(plan.review)} unreviewed props.")
    out("Restart xLights to load the groups; the first `xlo run` will re-probe targetability.")
    return 1 if plan.review else 0


def _run_validation(rgb_path, show_folder, plan, *, out=print) -> None:
    """Deterministic structural + sweep validation (spec §7). Requires networks.xml (for channel
    resolution) and the [preview] extra; degrades to structural-only when the renderer is absent."""
    from .layout_validate import structural_checks

    model_names = [p.name for p in plan.props]
    problems = structural_checks(plan.manifest, set(model_names))
    if problems:
        out("STRUCTURAL ISSUES:\n" + "\n".join(f"  - {p}" for p in problems))

    networks = Path(show_folder) / "xlights_networks.xml"
    if not networks.exists():
        out("(sweep validation skipped: no xlights_networks.xml)")
        return
    try:
        from xlights_core.preview.layout import parse_controllers, parse_models
        from xlights_core.preview.render import PreviewRenderer

        from .layout_validate import check_sweep, sweep_frames, write_fseq_v2_uncompressed
    except ImportError:
        out("(sweep validation skipped: install the [preview] extra)")
        return
    ctl = parse_controllers(networks)
    models = parse_models(rgb_path, ctl)
    import tempfile
    for gname, gr in plan.manifest.groups.items():
        if not gname.endswith("_LTR"):
            continue
        frames, members = sweep_frames(gr.members, models)
        if len(members) < 2:
            continue
        with tempfile.TemporaryDirectory() as td:
            fseq = Path(td) / "sweep.fseq"
            write_fseq_v2_uncompressed(fseq, frames)
            renderer = PreviewRenderer(fseq, rgb_path, networks)
            result = check_sweep(frames, renderer)
        if not result.ok:
            out(f"SWEEP FAIL {gname}: {result.detail}")
