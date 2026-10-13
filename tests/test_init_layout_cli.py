"""F-E slice 4 — the guided `xlo init-layout` flow + CLI wiring."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from xlights_orchestrator.pipeline.init_layout import (
    REVIEW_NAME,
    analyze_layout,
    format_diff,
    review_queue,
    run_init_layout,
    write_and_emit,
)

FIX = Path(__file__).parent / "fixtures"


def _args(**kw):
    base = dict(show_folder=None, dry_run=False, yes=False, no_validate=False,
                invert_x=False, review_web=False)
    base.update(kw)
    return SimpleNamespace(**base)


def _real_show(tmp_path):
    """A show folder holding the sanitized real layout + its overrides."""
    show = tmp_path / "show"
    show.mkdir()
    shutil.copy(FIX / "layout_real.xml", show / "xlights_rgbeffects.xml")
    shutil.copy(FIX / "layout_real_overrides.json", show / "layout_overrides.json")
    return show


# -- analyze + diff -----------------------------------------------------------------------------
def test_analyze_real_layout_converges_role_groups(tmp_path):
    show = _real_show(tmp_path)
    overrides = json.loads((show / "layout_overrides.json").read_text())
    plan = analyze_layout(show / "xlights_rgbeffects.xml", overrides=overrides)
    # only geometric groups may differ (see the manifest convergence test)
    GEOM = {"SEM_BAND_ROOF", "SEM_BAND_MID", "SEM_BAND_GROUND",
            "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT", "SEM_YARD"}
    assert set(plan.diff) <= GEOM


def test_format_diff_empty_is_converged():
    assert "converged" in format_diff({})


# -- review queue -------------------------------------------------------------------------------
def test_review_queue_forces_role_and_rebuilds_plan(tmp_path):
    show = _real_show(tmp_path)
    plan = analyze_layout(show / "xlights_rgbeffects.xml", overrides={})
    # answer: force any reviewed prop's role to CUSTOM_PROP-adjacent → 'STAR' just to exercise
    answers = iter([])

    def ask(name, cur, choices):
        return "SPINNER"          # force every reviewed prop to SPINNER
    before = {p.name: p.role for p in plan.props}
    review_queue(plan, ask=ask, yes=False)
    after = {p.name: p.role for p in plan.props}
    assert after != before        # at least one reviewed prop changed role
    _ = answers


def test_review_queue_yes_keeps_suggestion_but_stays_in_review(tmp_path):
    show = _real_show(tmp_path)
    plan = analyze_layout(show / "xlights_rgbeffects.xml", overrides={})
    n_review = len(plan.review)
    called = []
    review_queue(plan, ask=lambda *a: called.append(a) or "accept", yes=True)
    assert called == []                  # --yes asks nothing
    assert len(plan.review) == n_review  # still recorded for the warning


# -- write + emit -------------------------------------------------------------------------------
def test_write_and_emit_produces_groups_view_and_manifest(tmp_path):
    show = _real_show(tmp_path)
    rgb = show / "xlights_rgbeffects.xml"
    overrides = json.loads((show / "layout_overrides.json").read_text())
    plan = analyze_layout(rgb, overrides=overrides)
    report, manifest_path = write_and_emit(rgb, plan, show, cache_root=tmp_path / "cache")
    assert report.changed
    assert manifest_path.exists() and manifest_path.name == "layout_semantics.json"
    # the "SEM Master" view was authored
    import xml.etree.ElementTree as ET
    root = ET.parse(rgb).getroot()
    views_el = root.find("views")
    views = [v.get("name") for v in views_el.findall("view")] if views_el is not None else []
    assert "SEM Master" in views
    # a re-run is a byte-level no-op write
    before = rgb.read_bytes()
    plan2 = analyze_layout(rgb, overrides=overrides)
    r2, _ = write_and_emit(rgb, plan2, show, cache_root=tmp_path / "cache")
    assert not r2.changed and rgb.read_bytes() == before


# -- full flow through run_init_layout (dry-run, no write) --------------------------------------
def test_dry_run_writes_only_the_review_file(tmp_path):
    show = _real_show(tmp_path)
    rgb = show / "xlights_rgbeffects.xml"
    before = rgb.read_bytes()
    code = asyncio.run(run_init_layout(_args(show_folder=str(show), dry_run=True)))
    assert code == 0
    assert rgb.read_bytes() == before                    # the layout is never touched
    assert not (show / "layout_semantics.json").exists()
    review = json.loads((show / REVIEW_NAME).read_text())
    assert review["overrides_file"].endswith("layout_overrides.json")
    expected = analyze_layout(rgb, overrides=json.loads((show / "layout_overrides.json").read_text()))
    assert [p["name"] for p in review["props"]] == list(expected.review)


def test_dry_run_review_lists_props_with_features_and_overrides_resolve_them(tmp_path, capsys):
    show = _real_show(tmp_path)
    (show / "layout_overrides.json").unlink()            # no human decisions yet
    code = asyncio.run(run_init_layout(_args(show_folder=str(show), dry_run=True)))
    assert code == 0                                     # props needing review is the job, not a failure
    assert "props still need review" in capsys.readouterr().out
    props = json.loads((show / REVIEW_NAME).read_text())["props"]
    assert props
    rec = next(p for p in props if "display_as" in p)
    assert {"name", "display_as", "nodes", "pos", "groups", "role", "confidence",
            "candidate_roles"} <= set(rec)
    assert len(rec["pos"]) == 2 and isinstance(rec["nodes"], int) and isinstance(rec["groups"], list)
    assert "CUSTOM_PROP" in rec["candidate_roles"] and "SNOWFLAKE" in rec["candidate_roles"]
    # an override is a human decision: the classified prop leaves the review list on the next run
    (show / "layout_overrides.json").write_text(json.dumps({rec["name"]: {"role": "CUSTOM_PROP"}}))
    asyncio.run(run_init_layout(_args(show_folder=str(show), dry_run=True)))
    after = {p["name"] for p in json.loads((show / REVIEW_NAME).read_text())["props"]}
    assert rec["name"] not in after and len(after) == len(props) - 1


def test_missing_show_folder_returns_error():
    code = asyncio.run(run_init_layout(_args(show_folder="/nonexistent/path")))
    assert code == 1


# -- CLI wiring ---------------------------------------------------------------------------------
def test_cli_init_layout_needs_no_key_and_no_xlights(tmp_path, monkeypatch):
    """init-layout needs no API key and does NOT require xLights running."""
    from xlights_orchestrator import cli
    show = _real_show(tmp_path)
    # ensure no key is set — and stub load_env so the repo .env doesn't re-inject one.
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        cli.main(["init-layout", "--show-folder", str(show), "--dry-run"])
    assert exc.value.code == 0                            # ran to completion without a key
