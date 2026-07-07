"""Phase 3 — the show-level color script: one anchor color threads every section, chorus
occurrences share a signature pair verbatim, the bridge leads with the anchor's complement,
and every section palette is contrast-floored for LED legibility."""
from __future__ import annotations

from xlights_orchestrator.pipeline.color_script import _floor_section_palette, apply_color_script
from xlights_core.knowledge.colors import NAMED_COLORS, _resolve, hue_spread
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


# -- palette floor (move 4) ----------------------------------------------------

def test_floor_all_warm_gains_cool_anchor():
    # gold + amber are both near-yellow — hue spread < 60°; floor must inject a complement
    plan = _plan([["gold", "amber"]])
    apply_color_script(plan, {})
    pal = plan.sections[0].palette
    assert hue_spread(pal) >= 60.0, f"all-warm section not floored: {pal}"


def test_floor_injected_color_is_named():
    # the injected complement should be snapped to a NAMED_COLORS entry when close enough
    plan = _plan([["gold", "amber"]])
    apply_color_script(plan, {})
    pal = plan.sections[0].palette
    injected = [c for c in pal if c not in ["gold", "amber"]]
    assert injected, "no color was injected"
    # the injected entry should be a known named color (not a raw hex like #00BFFF)
    named_keys = set(NAMED_COLORS.keys())
    assert any(c.lower() in named_keys for c in injected), \
        f"injected color not a named color: {injected}"


def test_floor_white_dominant_unchanged():
    # all-achromatic section: no hue injected
    plan = _plan([["white", "warm white", "cool white"]])
    apply_color_script(plan, {})
    pal = plan.sections[0].palette
    achromatic_names = {"white", "warm white", "cool white"}
    non_achromatic = [c for c in pal if c not in achromatic_names]
    assert not non_achromatic, f"hue injected into white-dominant section: {pal}"


def test_floor_already_contrasting_unchanged():
    plan = _plan([["deep blue", "gold"]])
    original = list(plan.sections[0].palette)
    apply_color_script(plan, {})
    pal = plan.sections[0].palette
    # deep blue + gold span ~180° — no injection needed; only anchor may be added
    assert hue_spread(pal) >= 60.0
    # original colors still present
    assert all(c in pal for c in original)


def test_floor_is_idempotent():
    # idempotent: run floor twice, same result
    pal = ["gold", "amber"]
    once = _floor_section_palette(pal)
    twice = _floor_section_palette(once)
    assert once == twice, f"floor not idempotent: {once} → {twice}"


def test_floor_helper_all_warm_gains_complement():
    pal = _floor_section_palette(["gold", "amber"])
    assert len(pal) == 3
    assert hue_spread(pal) >= 60.0


def test_floor_helper_white_dominant_unchanged():
    pal = _floor_section_palette(["white", "warm white"])
    assert pal == ["white", "warm white"]


def test_floor_helper_already_contrasting_unchanged():
    pal = _floor_section_palette(["deep blue", "gold"])
    assert pal == ["deep blue", "gold"]
