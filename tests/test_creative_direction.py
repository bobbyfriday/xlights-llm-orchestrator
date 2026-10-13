"""The creative brief schema (ShowPlan) stays additive / back-compatible."""

from __future__ import annotations

from xlights_orchestrator.show_plan import SectionPlan, ShowPlan


def test_showplan_back_compat():
    # an old-shape plan (only original fields) still validates; new fields default
    p = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=1000, target_groups=["G"],
                                       effect_family="On", intensity=0.5)])
    assert p.experience == "" and p.group_motifs == {} and p.sections[0].look == ""
    assert p.sections[0].scene_id == "" and p.sections[0].scene_adaptation == ""
