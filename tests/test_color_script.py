"""Phase 3 — the show-level color script: one anchor color threads every section, chorus
occurrences share a signature pair verbatim, and the bridge leads with the anchor's complement."""
from __future__ import annotations

from xlights_orchestrator.pipeline.color_script import apply_color_script
from xlights_core.knowledge.colors import _resolve
from xlights_orchestrator.show_plan import SectionPlan, ShowPlan


def _plan(palettes):
    return ShowPlan(concept="c", sections=[
        SectionPlan(start_ms=i * 1000, end_ms=(i + 1) * 1000, target_groups=["G1"],
                    effect_family="On", intensity=0.6, palette=list(p))
        for i, p in enumerate(palettes)])


def _has(colors, target):
    return any(_resolve(c) == _resolve(target) for c in colors)


def test_anchor_present_in_every_section():
    # blue is the most frequent color → it must thread every section
    plan = _plan([["Blue", "Red"], ["Blue", "Green"], ["Gold", "White"]])
    apply_color_script(plan, {})
    for sec in plan.sections:
        assert _has(sec.palette, "Blue"), sec.palette


def test_chorus_occurrences_share_the_signature_pair():
    plan = _plan([["Red", "Blue"],          # 0 intro
                  ["Red", "Green"],          # 1 chorus
                  ["Gold", "White"],         # 2 verse
                  ["Blue", "Amber"]])        # 3 chorus
    apply_color_script(plan, {"chorus": [1, 3]})
    # both chorus sections LEAD with the same signature pair (verbatim, shared)
    assert plan.sections[1].palette[:2] == plan.sections[3].palette[:2]


def test_bridge_leads_with_the_complement():
    # 6 sections; the mid-song near-unique section is the bridge and leads with a hue departure
    plan = _plan([["Blue"], ["Blue"], ["Blue"], ["Blue"], ["Blue"], ["Blue"]])
    apply_color_script(plan, {"chorus": [1, 5], "verse": [0, 4]})
    bridge_first = plan.sections[2].palette[0] if plan.sections[2].palette else None
    # the bridge's first color is NOT the anchor (blue) — a deliberate contrast
    assert bridge_first is not None and _resolve(bridge_first) != _resolve("Blue")


def test_idempotent():
    plan = _plan([["Blue", "Red"], ["Blue", "Green"]])
    apply_color_script(plan, {})
    once = [list(s.palette) for s in plan.sections]
    apply_color_script(plan, {})
    twice = [list(s.palette) for s in plan.sections]
    assert once == twice


def test_empty_plan_safe():
    assert apply_color_script(ShowPlan(concept="c", sections=[]), {}) is not None
