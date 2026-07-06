"""F-E slice 6a — the Director manifest traits block (design decision 10a)."""

from __future__ import annotations

from pathlib import Path

from xlights_orchestrator.agents import director
from xlights_orchestrator.music_brief import MusicBrief

FIX = Path(__file__).parent / "fixtures"


def _real_manifest():
    import json

    from xlights_core.knowledge.layout_classify import (
        apply_overrides,
        classify,
        derive_spatial,
        parse_props,
    )
    from xlights_core.knowledge.layout_manifest import build_manifest
    from xlights_core.knowledge.layout_semantics import build_sem_groups, layout_modes
    props = parse_props(FIX / "layout_real.xml")
    res = classify(props)
    apply_overrides(res, json.loads((FIX / "layout_real_overrides.json").read_text()))
    summary = derive_spatial(props)
    plan = build_sem_groups(props)
    return build_manifest(res, summary, plan, modes=layout_modes(plan)), plan


def test_no_manifest_prompt_is_byte_identical():
    brief = MusicBrief(sections=[])
    groups = ["SEM_ARCHES", "SEM_ALL", "SEM_FOCAL"]
    without = director.render_input(brief, groups, ["On"])
    explicit_none = director.render_input(brief, groups, ["On"], manifest=None)
    assert without == explicit_none                       # additive: None === today
    assert "LAYOUT TRAITS" not in without


def test_manifest_prompt_appends_traits_block():
    manifest, plan = _real_manifest()
    groups = ["SEM_ARCHES", "SEM_CANES", "SEM_ALL"]
    txt = director.render_input(MusicBrief(sections=[]), groups, ["On"], manifest=manifest)
    assert "LAYOUT TRAITS" in txt
    assert "SEM_ARCHES: arch" in txt                      # role + count line
    assert "display:" in txt                              # the one display summary line
    # the flat AVAILABLE GROUPS list is unchanged (authoritative constraint)
    assert '"SEM_ARCHES"' in txt


def test_layout_block_size_budget():
    """The traits block stays compact (~1 KB target) so it fits the Director prompt."""
    manifest, plan = _real_manifest()
    groups = list(plan.keys())
    block = director.render_layout_block(manifest, groups)
    assert len(block) < 2048, f"layout block {len(block)} bytes is not compact"


def test_ordered_group_marked():
    manifest, plan = _real_manifest()
    block = director.render_layout_block(manifest, ["SEM_ARCHES_LTR"])
    assert "ordered" in block
