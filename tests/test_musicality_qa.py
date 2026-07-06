"""Advisory musicality QA: repetition-rhyme (Phase 1), dynamic-range + focus-budget (Phase 2).

All findings must be objective=False (they inform the Judge, never gate the objective score)."""
from __future__ import annotations

from xlights_orchestrator.qa import musicality
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan, ShowPlan


def _ins(target, etype, sec, *, bright=None, start=0, end=8000):
    e = EffectInstruction(target=target, effect_type=etype, look_id=f"{etype}#0",
                          start_ms=start, end_ms=end, section_index=sec)
    if bright is not None:
        e.extra_settings["C_SLIDER_Brightness"] = str(bright)
    return e


def _plan(intensities):
    return ShowPlan(sections=[
        SectionPlan(start_ms=i * 8000, end_ms=(i + 1) * 8000, target_groups=["G1"],
                    effect_family="On", intensity=v) for i, v in enumerate(intensities)])


# -- repetition-rhyme ---------------------------------------------------------

def test_rhyming_choruses_score_high():
    # two choruses with the SAME (target, effect) sets + same carrier → high rhyme
    instrs = []
    for si in (0, 1):
        instrs += [_ins("SEM_ARCHES", "Bars", si), _ins("SEM_ALL", "On", si),
                   _ins("SEM_FOCAL", "Plasma", si)]
    score, findings = musicality.repetition_rhyme(instrs, {"chorus": [0, 1]})
    assert score is not None and score > 0.9
    assert not [f for f in findings if f.metric == "musicality:rhyme"]


def test_index_rotated_choruses_score_low_and_flag():
    # the PRE-change behavior: each occurrence uses a DIFFERENT carrier + different targets
    instrs = [
        _ins("SEM_ARCHES", "Bars", 0), _ins("SEM_CANES", "Bars", 0),
        _ins("SEM_MINITREES", "Wave", 1), _ins("SEM_SIDE_LEFT", "Garlands", 1),
    ]
    score, findings = musicality.repetition_rhyme(instrs, {"chorus": [0, 1]})
    assert score is not None and score < musicality.RHYME_LOW
    rf = [f for f in findings if f.metric == "musicality:rhyme"]
    assert rf and rf[0].objective is False and "chorus" in rf[0].detail


def test_no_recurring_labels_is_neutral():
    instrs = [_ins("G1", "On", 0)]
    score, findings = musicality.repetition_rhyme(instrs, {})
    assert score is None and findings == []
    score2, _ = musicality.repetition_rhyme(instrs, {"intro": [0]})   # one-off, not recurring
    assert score2 is None


# -- dynamic-range ------------------------------------------------------------

def test_wall_to_wall_brightness_flagged():
    # every section lights the same coverage at the same brightness → no dynamic range
    instrs = []
    for si in range(4):
        instrs += [_ins(f"G{g}", "On", si, bright=180) for g in range(3)]
    spread, findings = musicality.dynamic_range(instrs, _plan([0.5, 0.6, 0.55, 0.5]))
    assert spread is not None and spread < musicality.DYNAMIC_LOW
    df = [f for f in findings if f.metric == "musicality:dynamic-range"]
    assert df and df[0].objective is False


def test_shaped_show_not_flagged():
    # a quiet 1-group dim section vs a full bright peak → real spread
    instrs = [_ins("G0", "On", 0, bright=40)]
    instrs += [_ins(f"G{g}", "On", 1, bright=200) for g in range(4)]
    spread, findings = musicality.dynamic_range(instrs, _plan([0.2, 0.95]))
    assert spread is not None and spread >= musicality.DYNAMIC_LOW
    assert not [f for f in findings if f.metric == "musicality:dynamic-range"]


# -- focus-budget -------------------------------------------------------------

def test_quiet_section_running_many_motion_systems_flagged():
    # a low-energy section stacking 4 distinct MOTION effects exceeds its budget
    instrs = [_ins("G1", "Bars", 0), _ins("G2", "Wave", 0),
              _ins("G3", "Spirals", 0), _ins("G4", "Pinwheel", 0)]
    findings = musicality.focus_budget(instrs, _plan([0.2]))
    ff = [f for f in findings if f.metric == "musicality:focus"]
    assert ff and ff[0].section_index == 0 and ff[0].objective is False


def test_well_shaped_focus_clean():
    instrs = [_ins("G1", "Bars", 0), _ins("G2", "On", 0)]   # one motion system + a static wash
    assert musicality.focus_budget(instrs, _plan([0.2])) == []


# -- aggregate ----------------------------------------------------------------

def test_evaluate_all_advisory():
    instrs = [_ins("SEM_ARCHES", "Bars", si) for si in (0, 1)]
    score, findings = musicality.evaluate(instrs, _plan([0.5, 0.5]), {"chorus": [0, 1]})
    assert 0 <= score <= 100
    assert all(f.objective is False for f in findings)


def test_evaluate_no_map_neutral_score():
    instrs = [_ins("G1", "On", 0, bright=100), _ins("G2", "On", 1, bright=100)]
    score, _ = musicality.evaluate(instrs, _plan([0.5, 0.5]), None)
    assert isinstance(score, int)
