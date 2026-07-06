"""F-G — the cost & quality dashboard over the revision log.

A deterministic, OFFLINE analyzer (no LLM, no xLights, no network) that reads the
append-mode ``revision_log.jsonl`` files from the cache tree and computes cost/quality
metrics into a typed :class:`Report`, rendered three ways — terminal text, self-contained
HTML, and JSON. Deliberately a *sibling* of ``revision_log.py`` (not under ``pipeline/``):
it never touches a live run, so it gets the real ``RevisionLogRecord`` schema, the real
``cache_root()``, and pytest coverage.

Compute once, render twice: ALL arithmetic lives in :func:`summarize_run`/:func:`build_report`;
:func:`render_text`/:func:`render_html` are formatting-only (a divergence between them is a bug
in the split). Prefer each record's run-time ``cost_usd`` (rates as-of-run beat rates
as-of-report); ``--reprice`` recomputes from the current price table.

Graceful degradation on pre-I1 logs is a hard requirement: quality metrics work at full
fidelity, missing cost renders ``—`` (never ``$0.00``), cost metrics are omitted for uncosted
runs, and aggregate cost counts only costed runs with an explicit coverage caveat.
"""

from __future__ import annotations

import html as _html
from collections import Counter, OrderedDict
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .models import registry
from .revision_log import RevisionLogRecord
from .telemetry import RoleUsage

NO_GAIN = "∞ (no gain)"          # cost-per-point rendering for a zero-or-negative objective gain


# -- load layer ---------------------------------------------------------------

def discover_logs(root: Path) -> list[Path]:
    """Every per-song ``revision_log.jsonl`` under ``root`` (one dir per song).

    ``root.glob('*/revision_log.jsonl')`` naturally skips the top-level
    ``targetable_groups_*.json`` files (they're files, not song dirs)."""
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(root.glob("*/revision_log.jsonl"))


def load_records(path: Path) -> tuple[list[RevisionLogRecord], int]:
    """Tolerant per-line parse: ``(records, skipped_count)``. A malformed line is counted and
    skipped — never aborts the file (historical JSONL accreted fields over dozens of changes)."""
    records: list[RevisionLogRecord] = []
    skipped = 0
    try:
        text = Path(path).read_text()
    except OSError:
        return [], 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(RevisionLogRecord.model_validate_json(line))
        except (ValidationError, ValueError):      # ValueError covers JSONDecodeError
            skipped += 1
    return records, skipped


def group_runs(records: list[RevisionLogRecord]) -> "OrderedDict[str, list[RevisionLogRecord]]":
    """Group records by ``run_id`` in first-seen (file) order. One append-mode log holds MANY
    runs; the grouping key is the run id, never the file."""
    out: OrderedDict[str, list[RevisionLogRecord]] = OrderedDict()
    for r in records:
        out.setdefault(r.run_id, []).append(r)
    return out


# -- metrics layer ------------------------------------------------------------

class IterationPoint(BaseModel):
    iteration: int
    objective: int
    advisory: int
    reverted: bool = False


class RunSummary(BaseModel):
    run_id: str
    song_key: str
    provider: str | None = None
    models: dict[str, str] = {}
    iterations: int = 0
    incomplete: bool = False
    skipped_by_gate: bool = False
    stop_reason: str | None = None
    first_objective: int | None = None
    final_objective: int | None = None
    objective_gain: int | None = None
    advisory: int | None = None
    trajectory: list[IterationPoint] = []
    churn: dict[int, int] = {}                 # section_index -> times regenerated
    revisions_by_origin: dict[str, int] = {}   # judge / backstop
    reverts: int = 0
    finding_mix: dict[str, int] = {}           # source -> count (across iterations)
    judge_vs_objective_agree: bool | None = None
    redesigned_sections: list[int] = []
    # -- cost (None ⇒ unknown; absent from the log ⇒ has_cost False) --
    has_cost: bool = False
    role_usage: dict[str, RoleUsage] = {}
    cost_usd: float | None = None
    cost_per_point: float | None = None        # None when not defined (skip-gate / zero-gain / uncosted)
    cost_per_point_render: str | None = None    # "∞ (no gain)" or None

    @property
    def wasted_on_reverts(self) -> bool:
        return self.reverts > 0


def _derive_provider(models: dict[str, str]) -> str | None:
    """Provider from a per-role models snapshot (``anthropic:...`` -> ``anthropic``)."""
    if not models:
        return None
    provs = {v.split(":", 1)[0] for v in models.values() if ":" in v}
    if len(provs) == 1:
        return next(iter(provs))
    return "mixed" if provs else None


def summarize_run(records: list[RevisionLogRecord], *, reprice: bool = False) -> RunSummary:
    """Reduce one run's records to a :class:`RunSummary`. Pure arithmetic; renderers format it.

    Cost-per-point = whole-run cost / objective gain, defined ``NO_GAIN`` for gain ≤ 0 and
    left undefined for skip-gate runs (excluded from the aggregate by construction)."""
    iters = [r for r in records if r.kind == "iteration"]
    finalize = next((r for r in records if r.kind == "finalize"), None)
    last = finalize or (records[-1] if records else None)
    incomplete = finalize is None

    song_key = records[0].song_key if records else ""
    models = last.models if last else {}
    summary = RunSummary(run_id=records[0].run_id if records else "?", song_key=song_key,
                         models=models, provider=_derive_provider(models), incomplete=incomplete)

    # skip-gate: a lone finalize with the skip decision (accepted at iteration 0)
    summary.skipped_by_gate = bool(
        finalize and not iters
        and (finalize.human_decision == "skip-high-objective" or finalize.stop_reason == "skip-gate"))

    # trajectory + churn + finding mix + reverts (from iteration records)
    traj: list[IterationPoint] = []
    churn: Counter[int] = Counter()
    origins: Counter[str] = Counter()
    findings: Counter[str] = Counter()
    reverts = 0
    for r in iters:
        traj.append(IterationPoint(iteration=r.iteration, objective=r.objective_score,
                                   advisory=r.advisory_score, reverted=r.reverted))
        for si in r.regenerated_sections:
            churn[si] += 1
        for rev in r.revisions:
            origins[rev.origin] += 1
        for f in r.findings:
            findings[f.source] += 1
        if r.reverted:
            reverts += 1
    summary.trajectory = traj
    summary.churn = dict(churn)
    summary.revisions_by_origin = dict(origins)
    summary.finding_mix = dict(findings)
    summary.reverts = reverts
    summary.iterations = len(iters)

    # objective trajectory (first from the earliest obj_before/objective; final from finalize)
    first_obj = None
    for r in iters:
        if r.obj_before is not None:
            first_obj = r.obj_before
            break
    if first_obj is None and iters:
        first_obj = iters[0].objective_score
    if first_obj is None and finalize is not None:
        first_obj = finalize.objective_score
    final_obj = (finalize.obj_after if finalize and finalize.obj_after is not None
                 else (finalize.objective_score if finalize else (iters[-1].objective_score if iters else None)))
    summary.first_objective = first_obj
    summary.final_objective = final_obj
    if first_obj is not None and final_obj is not None:
        summary.objective_gain = final_obj - first_obj
    summary.advisory = last.advisory_score if last else None
    summary.stop_reason = (finalize.stop_reason if finalize and finalize.stop_reason
                           else ("skip-gate" if summary.skipped_by_gate else None))
    summary.redesigned_sections = list(finalize.redesigned_sections) if finalize else []

    # judge-vs-objective agreement: the judge's final verdict (accept) vs objective gain > 0
    judge_scores = [s for r in iters if r.judge and (s := r.judge.get("score")) is not None]
    if judge_scores and summary.objective_gain is not None:
        summary.judge_vs_objective_agree = (
            (judge_scores[-1] >= judge_scores[0]) == (summary.objective_gain >= 0))

    # cost: prefer the record's run-time cost; recompute under --reprice or when the total exists
    total_usage: dict[str, RoleUsage] = {}
    if finalize and finalize.usage_total:
        total_usage = dict(finalize.usage_total)
    else:                                          # sum the per-iteration deltas for an incomplete run
        acc: dict[str, RoleUsage] = {}
        for r in records:
            for role, u in (r.usage or {}).items():
                acc.setdefault(role, RoleUsage()).incr(u)
        total_usage = acc
    summary.role_usage = total_usage
    has_cost = bool(total_usage) and any(u.total_tokens for u in total_usage.values())
    summary.has_cost = has_cost
    if has_cost:
        if reprice or (finalize is None) or finalize.cost_usd is None:
            summary.cost_usd = registry.estimate_cost(models, total_usage)
        else:
            summary.cost_usd = finalize.cost_usd
        if reprice and finalize is not None and finalize.cost_usd is not None:
            summary.cost_usd = registry.estimate_cost(models, total_usage)

    # cost per objective point gained (skip-gate excluded by construction)
    if not summary.skipped_by_gate and summary.cost_usd is not None and summary.objective_gain is not None:
        if summary.objective_gain > 0:
            summary.cost_per_point = summary.cost_usd / summary.objective_gain
        else:
            summary.cost_per_point_render = NO_GAIN
    return summary


class FleetRollup(BaseModel):
    total_runs: int = 0
    costed_runs: int = 0
    incomplete_runs: int = 0
    skip_gate_runs: int = 0
    total_cost_usd: float = 0.0            # sums COSTED runs only
    mean_objective_gain: float | None = None
    reverts: int = 0
    stop_reason_mix: dict[str, int] = {}
    provider_cost: dict[str, float] = {}   # provider -> summed cost across its costed runs
    finding_mix: dict[str, int] = {}
    cost_coverage_caveat: str = ""


class Report(BaseModel):
    root: str
    runs: list[RunSummary] = []
    skipped_lines: int = 0
    fleet: FleetRollup = FleetRollup()


def build_report(root: Path, *, song: str | None = None, reprice: bool = False) -> Report:
    """discover → load → group → summarize → aggregate. ``song`` filters to one song dir."""
    root = Path(root)
    logs = discover_logs(root)
    if song is not None:
        logs = [p for p in logs if p.parent.name == song]
    all_summaries: list[RunSummary] = []
    skipped = 0
    for log_path in logs:
        records, sk = load_records(log_path)
        skipped += sk
        for _run_id, run_records in group_runs(records).items():
            all_summaries.append(summarize_run(run_records, reprice=reprice))

    fleet = FleetRollup(total_runs=len(all_summaries))
    gains: list[int] = []
    for s in all_summaries:
        if s.incomplete:
            fleet.incomplete_runs += 1
        if s.skipped_by_gate:
            fleet.skip_gate_runs += 1
        fleet.reverts += s.reverts
        if s.stop_reason:
            fleet.stop_reason_mix[s.stop_reason] = fleet.stop_reason_mix.get(s.stop_reason, 0) + 1
        for src, n in s.finding_mix.items():
            fleet.finding_mix[src] = fleet.finding_mix.get(src, 0) + n
        if s.objective_gain is not None:
            gains.append(s.objective_gain)
        if s.has_cost and s.cost_usd is not None:
            fleet.costed_runs += 1
            fleet.total_cost_usd += s.cost_usd
            if s.provider:
                fleet.provider_cost[s.provider] = fleet.provider_cost.get(s.provider, 0.0) + s.cost_usd
    if gains:
        fleet.mean_objective_gain = sum(gains) / len(gains)
    fleet.cost_coverage_caveat = (
        f"{fleet.costed_runs} of {fleet.total_runs} runs have cost data"
        if fleet.total_runs else "no runs")
    return Report(root=str(root), runs=all_summaries, skipped_lines=skipped, fleet=fleet)


# -- renderers (formatting ONLY — no arithmetic) ------------------------------

def _cost_cell(c: float | None, has_cost: bool) -> str:
    if not has_cost or c is None:
        return "—"                      # unknown, never $0.00
    return f"${c:.2f}"


def _cpp_cell(s: RunSummary) -> str:
    if s.skipped_by_gate:
        return "—"
    if s.cost_per_point_render:
        return s.cost_per_point_render
    if s.cost_per_point is None:
        return "—"
    return f"${s.cost_per_point:.3f}"


def render_text(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"Cost & quality report — {report.root}")
    if not report.runs:
        return f"no revision logs found under {report.root}\n"
    lines.append("")
    hdr = f"{'run_id':<18} {'song':<10} {'it':>3} {'obj':>10} {'adv':>4} {'cost':>8} {'$/pt':>9} {'rev':>3} {'stop':<11}"
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for s in report.runs:
        obj = (f"{s.first_objective}→{s.final_objective}"
               if s.first_objective is not None and s.final_objective is not None else "—")
        flag = "*" if s.incomplete else " "
        lines.append(
            f"{s.run_id:<18} {s.song_key[:10]:<10} {s.iterations:>3} {obj:>10} "
            f"{(s.advisory if s.advisory is not None else '—'):>4} "
            f"{_cost_cell(s.cost_usd, s.has_cost):>8} {_cpp_cell(s):>9} {s.reverts:>3} "
            f"{(s.stop_reason or 'unknown'):<11}{flag}")
    f = report.fleet
    lines.append("")
    lines.append("Fleet")
    lines.append(f"  runs: {f.total_runs}  (incomplete {f.incomplete_runs}, skip-gate {f.skip_gate_runs})")
    lines.append(f"  total cost: ${f.total_cost_usd:.2f}   [{f.cost_coverage_caveat}]")
    if f.mean_objective_gain is not None:
        lines.append(f"  mean objective gain: {f.mean_objective_gain:+.1f}   reverts: {f.reverts}")
    if f.stop_reason_mix:
        mix = ", ".join(f"{k}={v}" for k, v in sorted(f.stop_reason_mix.items()))
        lines.append(f"  stop reasons: {mix}")
    if f.provider_cost:
        pc = ", ".join(f"{k} ${v:.2f}" for k, v in sorted(f.provider_cost.items()))
        lines.append(f"  cost by provider: {pc}")
    if f.finding_mix:
        fm = ", ".join(f"{k}={v}" for k, v in sorted(f.finding_mix.items()))
        lines.append(f"  finding mix: {fm}")
    if report.skipped_lines:
        lines.append(f"  skipped malformed log lines: {report.skipped_lines}")
    return "\n".join(lines) + "\n"


_CSS = """
:root { color-scheme: light dark; --fg:#111; --bg:#fff; --mut:#666; --line:#ddd; }
@media (prefers-color-scheme: dark) { :root { --fg:#e6e6e6; --bg:#161616; --mut:#999; --line:#333; } }
body { font: 14px/1.5 system-ui, sans-serif; color: var(--fg); background: var(--bg); margin: 2rem; }
h1 { font-size: 1.3rem; } table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: .3rem .6rem; border-bottom: 1px solid var(--line); }
th { color: var(--mut); font-weight: 600; } .num { text-align: right; font-variant-numeric: tabular-nums; }
.caveat { color: var(--mut); font-size: .85rem; } .spark { vertical-align: middle; }
"""


def _sparkline(points: list[IterationPoint]) -> str:
    """A tiny inline SVG score trajectory (no JS, no external refs)."""
    if len(points) < 2:
        return ""
    vals = [p.objective for p in points]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    w, h = 60, 16
    step = w / (len(vals) - 1)
    pts = " ".join(f"{i * step:.1f},{h - (v - lo) / span * (h - 2) - 1:.1f}" for i, v in enumerate(vals))
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline fill="none" stroke="currentColor" stroke-width="1.2" points="{pts}"/></svg>')


def render_html(report: Report) -> str:
    def esc(x) -> str:
        return _html.escape(str(x))

    f = report.fleet
    rows = []
    for s in report.runs:
        obj = (f"{s.first_objective}&rarr;{s.final_objective}"
               if s.first_objective is not None and s.final_objective is not None else "&mdash;")
        rows.append(
            "<tr>"
            f"<td>{esc(s.run_id)}</td><td>{esc(s.song_key[:10])}</td>"
            f"<td class='num'>{s.iterations}</td>"
            f"<td>{obj} {_sparkline(s.trajectory)}</td>"
            f"<td class='num'>{esc(_cost_cell(s.cost_usd, s.has_cost))}</td>"
            f"<td class='num'>{esc(_cpp_cell(s))}</td>"
            f"<td class='num'>{s.reverts}</td>"
            f"<td>{esc(s.stop_reason or 'unknown')}</td>"
            "</tr>")
    body = "\n".join(rows) or "<tr><td colspan='7'>no runs</td></tr>"
    caveat = esc(f.cost_coverage_caveat)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Cost &amp; quality report</title><style>{_CSS}</style></head><body>"
        "<h1>Cost &amp; quality report</h1>"
        f"<p class='caveat'>{esc(report.root)} &middot; {caveat} &middot; "
        f"total ${f.total_cost_usd:.2f} &middot; reverts {f.reverts}</p>"
        "<table><thead><tr><th>run</th><th>song</th><th class='num'>it</th><th>objective</th>"
        "<th class='num'>cost</th><th class='num'>$/pt</th><th class='num'>rev</th><th>stop</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
        + (f"<p class='caveat'>skipped {report.skipped_lines} malformed log lines</p>"
           if report.skipped_lines else "")
        + "</body></html>")
