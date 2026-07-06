"""F-E slice 2 — manifest emit/load + convergence against the sanitized real layout (spec §6)."""

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
    MANIFEST_NAME,
    MANIFEST_VERSION,
    LayoutManifest,
    build_manifest,
    emit_manifest,
    load_manifest,
    plan_diff,
    read_sem_groups,
)
from xlights_core.knowledge.layout_semantics import build_sem_groups, layout_modes

FIX = Path(__file__).parent / "fixtures"

# Role/ensemble groups the classifier + overrides must reproduce exactly on the real layout.
# Band/side/yard groups are GEOMETRIC (fixed 0.33/0.66/0.45/0.55 cuts, spec §4) and legitimately
# differ from the author's hand-adjusted cuts — an "explained-only" diff (design migration plan).
ROLE_GROUPS = (
    "SEM_OUTLINE", "SEM_WINDOWS", "SEM_ARCHES", "SEM_MINITREES", "SEM_CANES",
    "SEM_SNOWFLAKES", "SEM_SPINNERS", "SEM_ARCHES_LTR", "SEM_MINITREES_LTR", "SEM_CANES_LTR",
    "SEM_FOCAL", "SEM_ALL", "SEM_ALL_LESS_FOCAL", "SEM_ALL_LESS_FOCAL_RHYTHM", "SEM_ACCENTS",
    "SEM_HOUSE",
)
GEOMETRIC_GROUPS = (
    "SEM_BAND_ROOF", "SEM_BAND_MID", "SEM_BAND_GROUND",
    "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT", "SEM_YARD",
)


def _classify_real():
    props = parse_props(FIX / "layout_real.xml")
    res = classify(props)
    apply_overrides(res, json.loads((FIX / "layout_real_overrides.json").read_text()))
    summary = derive_spatial(props)
    plan = build_sem_groups(props)
    return res, summary, plan


# -- manifest schema + emit/load ----------------------------------------------------------------
def test_manifest_roundtrip(tmp_path):
    m = LayoutManifest(props=[], groups={})
    dumped = m.model_dump_json()
    back = LayoutManifest.model_validate_json(dumped)
    assert back.version == MANIFEST_VERSION


def test_emit_and_load(tmp_path):
    res, summary, plan = _classify_real()
    m = build_manifest(res, summary, plan, modes=layout_modes(plan))
    cache = tmp_path / "cache"
    path = emit_manifest(m, tmp_path / "show", cache_root=cache)
    assert path.name == MANIFEST_NAME and path.exists()
    assert (cache / "layout" / MANIFEST_NAME).exists()          # cache copy
    # loads from show dir
    loaded = load_manifest(tmp_path / "show")
    assert loaded is not None and len(loaded.props) == len(m.props)
    # loads from cache when show dir absent
    from_cache = load_manifest(tmp_path / "nope", cache_root=cache)
    assert from_cache is not None


def test_load_tolerant_absent_and_version_mismatch(tmp_path):
    assert load_manifest(tmp_path / "missing") is None          # absent
    bad = tmp_path / MANIFEST_NAME
    bad.write_text(json.dumps({"version": 999, "props": [], "groups": {}}))
    assert load_manifest(bad) is None                           # version mismatch → None


def test_manifest_records_low_confidence_in_review():
    res, summary, plan = _classify_real()
    m = build_manifest(res, summary, plan)
    # every prop below 0.8 confidence is in review (spec §7.4)
    low = {p.name for p in res.props if p.confidence < 0.8}
    assert low.issubset(set(m.review))


def test_manifest_size_budget():
    """Spec §6 wants a compact manifest. 10 KB flat is only achievable on a small/typical layout;
    the real fixture has 81 verbose-named models, so we bound the *density* (bytes/prop) which is
    what keeps the LLM payload compact regardless of layout scale."""
    res, summary, plan = _classify_real()
    m = build_manifest(res, summary, plan, modes=layout_modes(plan))
    size = len(m.model_dump_json(exclude_defaults=True))
    per_prop = size / max(len(m.props), 1)
    assert per_prop < 380, f"manifest density {per_prop:.0f} B/prop is not compact"
    # a small/typical layout (the basic fixture, ~15 props) must clear the flat 10 KB budget
    small = parse_props(FIX / "layout_basic.xml")
    sres = classify(small)
    ssum = derive_spatial(small)
    splan = build_sem_groups(small)
    sm = build_manifest(sres, ssum, splan, modes=layout_modes(splan))
    assert len(sm.model_dump_json(exclude_defaults=True)) < 10_240


# -- convergence against the real layout --------------------------------------------------------
def test_role_groups_converge_on_real_layout():
    _res, _summary, plan = _classify_real()
    file_groups = read_sem_groups(FIX / "layout_real.xml")
    diff = plan_diff(file_groups, plan)
    # every role/ensemble group must diff empty
    role_divergences = {n: diff[n] for n in ROLE_GROUPS if n in diff}
    assert role_divergences == {}, f"role groups diverged: {list(role_divergences)}"


def test_geometric_groups_are_the_only_explained_diffs():
    _res, _summary, plan = _classify_real()
    file_groups = read_sem_groups(FIX / "layout_real.xml")
    diff = plan_diff(file_groups, plan)
    # the ONLY groups allowed to differ are the geometric band/side/yard groups
    unexpected = [n for n in diff if n not in GEOMETRIC_GROUPS]
    assert unexpected == [], f"unexpected non-geometric divergences: {unexpected}"


def test_ltr_order_matches_the_hand_built_layout():
    _res, _summary, plan = _classify_real()
    file_groups = read_sem_groups(FIX / "layout_real.xml")
    diff = plan_diff(file_groups, plan)
    for ltr in ("SEM_ARCHES_LTR", "SEM_CANES_LTR", "SEM_MINITREES_LTR"):
        assert ltr not in diff or not diff[ltr].order_changed


GOLDEN_MANIFEST = FIX / "layout_real_manifest.golden.json"


def test_real_manifest_matches_golden():
    """Snapshot the full derived manifest for the real layout (classifier/spatial regression net).
    Regenerate intentionally with the script in the change if the derivation legitimately changes."""
    res, summary, plan = _classify_real()
    m = build_manifest(res, summary, plan, modes=layout_modes(plan), generated="")
    data = m.model_dump(exclude_defaults=True)
    data["version"] = m.version
    produced = json.loads(json.dumps(data, sort_keys=True))
    expected = json.loads(GOLDEN_MANIFEST.read_text())
    assert produced == expected, (
        "derived manifest changed vs the golden — if intentional, regenerate "
        "tests/fixtures/layout_real_manifest.golden.json"
    )
