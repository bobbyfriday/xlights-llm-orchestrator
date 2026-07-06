"""Tests for F-G — the offline cost & quality dashboard (reporting.py).

Hermetic (no LLM, no xLights, no network). Two fixture styles:
  - programmatic fixtures written by the REAL RevisionLog writer into tmp_path;
  - checked-in raw pre-I1 and post-I1 JSONL under tests/fixtures/revision_logs/ that freeze
    backward compatibility (the pre-I1 shape has no usage/cost fields at all).
"""

from __future__ import annotations

from pathlib import Path

from xlights_orchestrator import reporting
from xlights_orchestrator.reporting import Report, NO_GAIN
from xlights_orchestrator.revision_log import RevisionLog, RevisionLogRecord
from xlights_orchestrator.telemetry import RoleUsage

FIXTURES = Path(__file__).parent / "fixtures" / "revision_logs"


# -- helpers ------------------------------------------------------------------

def _write(root: Path, song: str, records: list[RevisionLogRecord]) -> Path:
    d = root / song
    w = RevisionLog(d / "revision_log.jsonl", d / "revision_log.md")
    for r in records:
        w.write(r)
    return d / "revision_log.jsonl"


def _iter(run, it, **kw):
    base = dict(run_id=run, iteration=it, song_key="song", ts="t",
                objective_score=kw.pop("obj", 80), advisory_score=kw.pop("adv", 60))
    base.update(kw)
    return RevisionLogRecord(**base)


def _fin(run, it, **kw):
    return _iter(run, it, kind="finalize", **kw)


# -- load layer ---------------------------------------------------------------

def test_discover_skips_decoy_group_files(tmp_path):
    root = tmp_path / "orchestrator"
    _write(root, "song_a", [_fin("a", 0, obj=90)])
    _write(root, "song_b", [_fin("b", 0, obj=85)])
    (root / "targetable_groups_x.json").parent.mkdir(parents=True, exist_ok=True)
    (root / "targetable_groups_x.json").write_text("{}")     # a decoy top-level file
    logs = reporting.discover_logs(root)
    assert len(logs) == 2 and all(p.name == "revision_log.jsonl" for p in logs)


def test_malformed_line_skipped_and_counted(tmp_path):
    root = tmp_path / "orchestrator"
    path = _write(root, "song", [_iter("r", 0, obj=70), _fin("r", 1, obj=80)])
    with open(path, "a") as f:
        f.write("{not valid json}\n")
    records, skipped = reporting.load_records(path)
    assert skipped == 1 and len(records) == 2                # every good line still parses


def test_group_runs_orders_by_first_seen(tmp_path):
    root = tmp_path / "orchestrator"
    path = _write(root, "song", [_iter("r1", 0), _iter("r2", 0), _fin("r1", 1), _fin("r2", 1)])
    records, _ = reporting.load_records(path)
    groups = reporting.group_runs(records)
    assert list(groups.keys()) == ["r1", "r2"]               # file order, not sorted


# -- metrics golden values ----------------------------------------------------

def test_trajectory_revert_gain_and_cost_per_point(tmp_path):
    """71→78→76(revert)→90 ⇒ revert count 1, gain 19, cost/point = Σcost / 19."""
    root = tmp_path / "orchestrator"
    models = {"judge": "anthropic:claude-opus-4-8"}
    u = {"judge": RoleUsage(input_tokens=1000, output_tokens=100)}
    total = {"judge": RoleUsage(input_tokens=4000, output_tokens=400)}
    cost = (4000 * 5.0 + 400 * 25.0) / 1_000_000
    recs = [
        _iter("r", 0, obj=78, obj_before=71, obj_after=78, obj_delta=7, regenerated_sections=[1],
              usage=u, models=models),
        _iter("r", 1, obj=76, obj_before=78, obj_after=76, obj_delta=-2, reverted=True,
              regenerated_sections=[2], usage=u, models=models),
        _iter("r", 2, obj=90, obj_before=78, obj_after=90, obj_delta=12, regenerated_sections=[1],
              usage=u, models=models),
        _fin("r", 3, obj=90, obj_after=90, stop_reason="cap", usage=u, usage_total=total,
             cost_usd=cost, models=models),
    ]
    _write(root, "song", recs)
    rep = reporting.build_report(root)
    s = rep.runs[0]
    assert s.objective_gain == 19 and s.reverts == 1
    assert s.first_objective == 71 and s.final_objective == 90
    assert s.churn == {1: 2, 2: 1}
    assert abs(s.cost_per_point - cost / 19) < 1e-12
    assert s.stop_reason == "cap"


def test_zero_gain_renders_infinity(tmp_path):
    root = tmp_path / "orchestrator"
    total = {"judge": RoleUsage(input_tokens=1000, output_tokens=100)}
    recs = [
        _iter("r", 0, obj=80, obj_before=80, obj_after=80, obj_delta=0,
              usage={"judge": RoleUsage(input_tokens=1000, output_tokens=100)},
              models={"judge": "anthropic:claude-opus-4-8"}),
        _fin("r", 1, obj=80, obj_after=80, stop_reason="plateau", usage_total=total, cost_usd=0.01,
             models={"judge": "anthropic:claude-opus-4-8"}),
    ]
    _write(root, "song", recs)
    rep = reporting.build_report(root)
    s = rep.runs[0]
    assert s.objective_gain == 0
    assert s.cost_per_point is None and s.cost_per_point_render == NO_GAIN
    assert NO_GAIN in reporting.render_text(rep)


def test_skip_gate_counts_but_no_cost_per_point(tmp_path):
    root = tmp_path / "orchestrator"
    _write(root, "song", [_fin("r", 0, obj=92, obj_after=92,
                                human_decision="skip-high-objective", stop_reason="skip-gate")])
    rep = reporting.build_report(root)
    s = rep.runs[0]
    assert s.skipped_by_gate is True
    assert s.cost_per_point is None and s.cost_per_point_render is None    # excluded by construction
    assert rep.fleet.skip_gate_runs == 1


# -- pre/post-I1 backward compat ----------------------------------------------

def test_pre_i1_fixture_full_quality_no_cost():
    rep = reporting.build_report(FIXTURES, song=None)          # reads both checked-in fixtures
    # find the pre-I1 run
    pre = next(s for s in rep.runs if s.run_id == "pre1")
    assert pre.has_cost is False and pre.cost_usd is None      # no cost fields at all
    assert pre.final_objective == 78                           # quality still computed
    # a post-I1 run in the same corpus is costed
    post = next(s for s in rep.runs if s.run_id == "post1")
    assert post.has_cost is True and abs(post.cost_usd - 0.665) < 1e-9


def test_mixed_corpus_reports_honest_coverage(tmp_path):
    """Uncosted runs show — in every cost cell; aggregate counts only costed runs + a caveat."""
    root = tmp_path / "orchestrator"
    # one costed run
    _write(root, "s1", [
        _iter("costed", 0, obj=70, obj_before=70, obj_after=80, obj_delta=10,
              usage={"g": RoleUsage(input_tokens=1000)}, models={"g": "anthropic:claude-sonnet-4-6"}),
        _fin("costed", 1, obj=80, obj_after=80, usage_total={"g": RoleUsage(input_tokens=1000)},
             cost_usd=0.003, models={"g": "anthropic:claude-sonnet-4-6"})])
    # one pre-I1-style run (no usage anywhere)
    _write(root, "s2", [_iter("bare", 0, obj=60, obj_before=60, obj_after=70, obj_delta=10),
                        _fin("bare", 1, obj=70, obj_after=70)])
    rep = reporting.build_report(root)
    txt = reporting.render_text(rep)
    assert "1 of 2 runs have cost data" in txt
    assert rep.fleet.costed_runs == 1 and rep.fleet.total_runs == 2
    bare = next(s for s in rep.runs if s.run_id == "bare")
    assert bare.has_cost is False
    # the bare run's cost cell renders — (never $0.00)
    assert "—" in txt


def test_reprice_recomputes(tmp_path):
    root = tmp_path / "orchestrator"
    # record a stale cost that disagrees with the price table
    total = {"g": RoleUsage(input_tokens=1_000_000)}
    _write(root, "s", [
        _iter("r", 0, obj=70, obj_before=70, obj_after=80, obj_delta=10,
              usage={"g": RoleUsage(input_tokens=1_000_000)}, models={"g": "anthropic:claude-sonnet-4-6"}),
        _fin("r", 1, obj=80, obj_after=80, usage_total=total, cost_usd=99.0,
             models={"g": "anthropic:claude-sonnet-4-6"})])
    rep = reporting.build_report(root)
    assert rep.runs[0].cost_usd == 99.0                        # trusts the run-time cost
    rep2 = reporting.build_report(root, reprice=True)
    assert rep2.runs[0].cost_usd == 3.0                        # 1M input × $3/1M = $3.00


def test_incomplete_run_flagged(tmp_path):
    root = tmp_path / "orchestrator"
    _write(root, "s", [_iter("r", 0, obj=70, obj_before=70, obj_after=75, obj_delta=5)])  # no finalize
    rep = reporting.build_report(root)
    s = rep.runs[0]
    assert s.incomplete is True and rep.fleet.incomplete_runs == 1


# -- renderers ----------------------------------------------------------------

def test_html_is_self_contained_and_escapes(tmp_path):
    root = tmp_path / "orchestrator"
    _write(root, "s", [_iter("r<b>&", 0, obj=70, obj_before=70, obj_after=80, obj_delta=10),
                       _fin("r<b>&", 1, obj=80, obj_after=80)])
    rep = reporting.build_report(root)
    html = reporting.render_html(rep)
    assert "http://" not in html and "https://" not in html and "<script" not in html
    assert "r&lt;b&gt;&amp;" in html                          # detail strings are escaped
    assert "prefers-color-scheme" in html                     # light/dark


def test_json_round_trips(tmp_path):
    root = tmp_path / "orchestrator"
    _write(root, "s", [_fin("r", 0, obj=90, obj_after=90, stop_reason="skip-gate",
                            human_decision="skip-high-objective")])
    rep = reporting.build_report(root)
    back = Report.model_validate_json(rep.model_dump_json())
    assert back.runs[0].run_id == "r" and back.fleet.total_runs == 1


# -- CLI end-to-end -----------------------------------------------------------

def test_cli_report_empty_cache(tmp_path, monkeypatch, capsys):
    from xlights_orchestrator.cli import main
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    main(["report"])
    out = capsys.readouterr().out
    assert "no revision logs found" in out


def test_cli_report_text_and_json(tmp_path, monkeypatch, capsys):
    from xlights_orchestrator.cli import main
    root = tmp_path / "orchestrator"
    _write(root, "s", [_iter("r", 0, obj=70, obj_before=70, obj_after=80, obj_delta=10,
                             usage={"g": RoleUsage(input_tokens=1000)},
                             models={"g": "anthropic:claude-sonnet-4-6"}),
                       _fin("r", 1, obj=80, obj_after=80, usage_total={"g": RoleUsage(input_tokens=1000)},
                            cost_usd=0.003, models={"g": "anthropic:claude-sonnet-4-6"})])
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path))
    main(["report"])
    assert "Cost & quality report" in capsys.readouterr().out
    main(["report", "--json"])
    out = capsys.readouterr().out
    Report.model_validate_json(out)                           # --json round-trips through the model
