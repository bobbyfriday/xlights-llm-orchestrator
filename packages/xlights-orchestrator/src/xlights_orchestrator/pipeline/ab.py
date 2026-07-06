"""F-H — the provider A/B eval harness (`xlo ab`).

Runs ONE fixture song through two or more provider-routing *arms* under controlled conditions
and produces *data* (per-arm metric distributions), not a pass/fail. Arms run SEQUENTIALLY (the
XLightsClient mutation lock + single live app + process-global env swap forbid concurrency),
always unattended, with repeats INTERLEAVED across arms (A,B,A,B) rather than batched.

Controlled conditions:
  - analyze the song ONCE and inject the same SongAnalysis into every arm (no arm re-pays or
    re-races the audio analysis);
  - warm the targetable-groups probe once before the first arm;
  - each run gets a distinct per-arm `save_as` so arms never overwrite each other;
  - the A/B manifest (`ab_runs.json`) is written INCREMENTALLY after each completed run, so an
    interrupted A/B keeps the data for the runs that finished.

Cache isolation is handled by the model-fingerprinted cache namespacing (see cache.py); the
shared `revision_log.jsonl` accumulates every arm's run, distinguished by `run_id` + `models` —
exactly what F-G's `summarize_run` groups by. Statistical honesty: report medians + min–max
ranges (never single numbers); "indistinguishable when ranges overlap"; no significance tests v1.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

from ..models.registry import _cfg
from ..reporting import RunSummary, summarize_run
from .cache import cache_root, song_key
from .media import safe_name

log = logging.getLogger(__name__)

# provider -> the env var whose presence proves the key is configured
_PROVIDER_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


@dataclass
class ArmSpec:
    """One A/B arm: a base provider plus optional per-role overrides.

    ``label`` is a stable human/file identifier; ``providers()`` yields every distinct provider
    the arm touches (for the multi-key preflight)."""
    label: str
    provider: str
    role_overrides: dict[str, str] = field(default_factory=dict)

    def providers(self) -> set[str]:
        return {self.provider, *self.role_overrides.values()}


def parse_arm(spec: str) -> ArmSpec:
    """Parse ``base_provider *("+" role "=" provider)`` (e.g. ``gemini+judge=anthropic``).

    Validates every role and provider against config.yaml so a typo dies at parse time, before
    any spend. The label is the raw spec (unique per arm)."""
    cfg = _cfg()
    providers = set(cfg.get("providers", {}))
    roles = set(cfg.get("roles", {}))
    parts = spec.split("+")
    base = parts[0].strip()
    if base not in providers:
        raise ValueError(f"unknown provider {base!r} in arm {spec!r} (known: {sorted(providers)})")
    overrides: dict[str, str] = {}
    for token in parts[1:]:
        if "=" not in token:
            raise ValueError(f"bad arm override {token!r} in {spec!r} — expected role=provider")
        role, prov = (t.strip() for t in token.split("=", 1))
        if role not in roles:
            raise ValueError(f"unknown role {role!r} in arm {spec!r} (known: {sorted(roles)})")
        if prov not in providers:
            raise ValueError(f"unknown provider {prov!r} in arm {spec!r}")
        overrides[role] = prov
    return ArmSpec(label=spec, provider=base, role_overrides=overrides)


@contextmanager
def arm_env(arm: ArmSpec):
    """Set ``XLO_PROVIDER`` + per-role ``XLO_PROVIDER_<ROLE>`` for the arm, restoring the prior
    environment on exit — even on an exception (so an arm's routing never leaks into the next)."""
    to_set = {"XLO_PROVIDER": arm.provider}
    for role, prov in arm.role_overrides.items():
        to_set[f"XLO_PROVIDER_{role.upper()}"] = prov
    prior = {k: os.environ.get(k) for k in to_set}
    try:
        os.environ.update(to_set)
        yield
    finally:
        for k, old in prior.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old


def preflight_keys(arms: list[ArmSpec]) -> None:
    """Refuse to start unless every provider named by any arm has its API key. Raises before spend."""
    needed = set().union(*[a.providers() for a in arms]) if arms else set()
    missing = [p for p in sorted(needed)
               if not os.environ.get(_PROVIDER_KEY_ENV.get(p, "___none___"))]
    if missing:
        raise SystemExit(
            "A/B preflight failed — missing API key(s) for: " + ", ".join(missing)
            + " (set " + ", ".join(_PROVIDER_KEY_ENV.get(p, "?") for p in missing) + ")")


async def run_arm(song, arm: ArmSpec, *, client, analysis, save_as, run_pipeline, **kw):
    """Run one arm in-process under its routing. Injects the shared ``analysis`` so the audio is
    analyzed once; the model-fingerprinted cache keeps this arm's LLM artifacts separate."""
    with arm_env(arm):
        return await run_pipeline(str(song), client=client, save_as=save_as,
                                  analyze=lambda _p: analysis, **kw)


async def run_ab(song, arms: list[ArmSpec], *, client, repeat: int = 1, name_prefix: str | None = None,
                 run_pipeline=None, analyze=None, max_iterations: int = 3, manifest_path=None,
                 warm_probe=None, **pipeline_kw) -> list[dict]:
    """Run ``arms`` × ``repeat`` interleaved (A,B,A,B), sequentially, unattended.

    Analyze once (``analyze(song)``), warm the group probe once, then for each repeat run every
    arm. Each run gets ``{name_prefix}_{arm_i}_{repeat_j}`` as ``save_as``. Returns the manifest
    rows; writes ``ab_runs.json`` incrementally so an interruption keeps completed data."""
    from ..pipeline import run_pipeline as _default_run
    from .run import _auto_checkpoint

    run_pipeline = run_pipeline or _default_run
    prefix = name_prefix or safe_name(song)
    key = song_key(str(song))
    manifest_path = Path(manifest_path) if manifest_path else (cache_root() / key / "ab_runs.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # analyze ONCE (deterministic) and inject the SAME object into every arm
    analysis = analyze(str(song)) if analyze is not None else _analyze_once(song, **pipeline_kw)
    if warm_probe is not None:                     # warm the targetable-groups cache once
        await warm_probe(client)

    manifest: list[dict] = []
    for j in range(repeat):
        for i, arm in enumerate(arms):
            save_as = f"{prefix}_{i}_{j}"
            log.info("A/B run: arm %s (%d/%d) repeat %d/%d → %s",
                     arm.label, i + 1, len(arms), j + 1, repeat, save_as)
            try:
                st = await run_arm(song, arm, client=client, analysis=analysis, save_as=save_as,
                                   run_pipeline=run_pipeline, refine=True, use_cache=True,
                                   max_iterations=max_iterations, checkpoint=_auto_checkpoint,
                                   interpret_checkpoint=None, design_checkpoint=None,
                                   log_revisions=True, **pipeline_kw)
                sections = len(st.show_plan.sections) if st.show_plan else 0
                row = {"arm": arm.label, "arm_index": i, "repeat": j, "save_as": save_as,
                       "sections": sections, "ok": True}
            except Exception as exc:  # noqa: BLE001 — one arm's failure is DATA, not a harness abort
                log.warning("A/B run failed (arm %s repeat %d): %s", arm.label, j, exc)
                row = {"arm": arm.label, "arm_index": i, "repeat": j, "save_as": save_as,
                       "ok": False, "error": str(exc)}
            manifest.append(row)
            manifest_path.write_text(json.dumps(manifest, indent=1))    # incremental — survives an abort
    return manifest


def _analyze_once(song, *, stems: bool = False, **_kw):
    from xlights_core.audio import AudioAnalyzer
    return AudioAnalyzer().analyze(str(song), stems=stems)


# -- summary extraction (reuses F-G's summarize_run per run_id) ----------------

@dataclass
class ArmSummary:
    label: str
    runs: list[RunSummary]

    def _metric(self, get) -> list[float]:
        return [v for v in (get(r) for r in self.runs) if v is not None]

    def dist(self, get) -> dict | None:
        vals = self._metric(get)
        if not vals:
            return None
        return {"median": median(vals), "min": min(vals), "max": max(vals), "n": len(vals)}


def summarize_runs(jsonl_lines: list[str], run_ids: set[str] | None = None) -> dict[str, ArmSummary]:
    """Group revision-log lines into per-arm summaries keyed by the arm's ``models`` label.

    Reuses F-G's ``summarize_run`` (same arithmetic) — an arm is identified by its per-role
    ``models`` snapshot (the true routing), so a mixed arm is labeled truthfully."""
    from ..reporting import group_runs
    records = []
    for line in jsonl_lines:
        line = line.strip()
        if not line:
            continue
        try:
            from ..revision_log import RevisionLogRecord
            records.append(RevisionLogRecord.model_validate_json(line))
        except Exception:  # noqa: BLE001 — tolerant, like F-G's loader
            continue
    out: dict[str, ArmSummary] = {}
    for run_id, run_records in group_runs(records).items():
        if run_ids is not None and run_id not in run_ids:
            continue
        s = summarize_run(run_records)
        label = _models_label(s.models)
        out.setdefault(label, ArmSummary(label=label, runs=[])).runs.append(s)
    return out


def summarize_manifest(manifest_path) -> dict[str, ArmSummary]:
    """Load a whole song's shared revision log and summarize per arm (models label)."""
    key = Path(manifest_path).parent.name
    log_path = cache_root() / key / "revision_log.jsonl"
    if not log_path.exists():
        return {}
    return summarize_runs(log_path.read_text().splitlines())


def _models_label(models: dict[str, str]) -> str:
    """A short, truthful arm label from a per-role models snapshot. If every role shares one
    provider, that provider; otherwise the majority (base) provider plus each overriding role.
    Ties on the majority break alphabetically so the label is stable across runs."""
    if not models:
        return "unknown"
    provs = {role: v.split(":", 1)[0] for role, v in models.items() if ":" in v}
    if not provs:
        return "unknown"
    counts = {p: list(provs.values()).count(p) for p in set(provs.values())}
    base = sorted(counts, key=lambda p: (-counts[p], p))[0]      # majority, alpha tie-break
    overrides = sorted(f"{role}={p}" for role, p in provs.items() if p != base)
    return base + ("+" + "+".join(overrides) if overrides else "")


def render_ab_summary(arms: dict[str, ArmSummary]) -> str:
    """Terminal summary: per-arm median + min–max range per metric; overlapping ranges are
    'indistinguishable'. Never a single number, never a significance test."""
    lines = ["A/B results (median [min–max] across repeats)"]
    metrics = [
        ("final objective", lambda r: r.final_objective),
        ("objective gain", lambda r: r.objective_gain),
        ("iterations", lambda r: r.iterations),
        ("reverts", lambda r: float(r.reverts)),
        ("cost $", lambda r: r.cost_usd),
    ]
    for label, arm in sorted(arms.items()):
        lines.append(f"\n  arm {label}  ({len(arm.runs)} run(s))")
        for name, get in metrics:
            d = arm.dist(get)
            if d is None:
                lines.append(f"    {name:<18} —")
            else:
                lines.append(f"    {name:<18} {d['median']:.3g} [{d['min']:.3g}–{d['max']:.3g}]")
    # pairwise indistinguishability on final objective
    labels = sorted(arms)
    if len(labels) == 2:
        a, b = arms[labels[0]], arms[labels[1]]
        da, db = a.dist(lambda r: r.final_objective), b.dist(lambda r: r.final_objective)
        if da and db:
            delta = abs(da["median"] - db["median"])
            span = max(da["max"] - da["min"], db["max"] - db["min"])
            verdict = "INDISTINGUISHABLE (ranges overlap)" if delta <= span else f"delta {delta:.3g}"
            lines.append(f"\n  {labels[0]} vs {labels[1]} on final objective: {verdict}")
    return "\n".join(lines) + "\n"
