"""Unit tests for the refine-loop guards extracted into `pipeline/refine_loop.py` (I3).

Each guard is exercised in isolation — no loop harness — which is the point of the
decomposition. The whole-loop behavior stays pinned by test_refine.py / test_visual.py /
test_design_escalation.py / test_revision_log.py and the byte-identical golden snapshot.
"""
from __future__ import annotations

from types import SimpleNamespace


from xlights_orchestrator.pipeline.refine_loop import (
    BestTracker,
    EscalationLedger,
    design_implicated,
    plateau_signature,
    refine_skip_objective,
    should_skip_refine,
)
from xlights_orchestrator.pipeline.tuning import REFINE_SKIP_OBJECTIVE


# -- import compat (task 6.1): historical paths still resolve -------------------

def test_historical_import_paths_resolve():
    from xlights_orchestrator.pipeline.beats import SPEED_KEYS  # noqa: F401
    from xlights_orchestrator.pipeline.run import (  # noqa: F401
        REFINE_SKIP_OBJECTIVE as _rso,
        _refine_loop,
        _refine_skip_objective,
    )
    from xlights_orchestrator.qa.rules import DURATION_CELLABLE, ENERGY_BAND  # noqa: F401


# -- should_skip_refine --------------------------------------------------------

def test_should_skip_refine_none_disables():
    assert should_skip_refine(100, None) is False


def test_should_skip_refine_equality_skips():
    assert should_skip_refine(88, 88) is True


def test_should_skip_refine_below_cutoff():
    assert should_skip_refine(87, 88) is False


def test_refine_skip_objective_env_override(monkeypatch):
    monkeypatch.setenv("XLO_REFINE_SKIP_OBJECTIVE", "42")
    assert refine_skip_objective() == 42
    monkeypatch.setenv("XLO_REFINE_SKIP_OBJECTIVE", "not-an-int")
    assert refine_skip_objective() == REFINE_SKIP_OBJECTIVE
    monkeypatch.delenv("XLO_REFINE_SKIP_OBJECTIVE", raising=False)
    assert refine_skip_objective() == REFINE_SKIP_OBJECTIVE


# -- plateau_signature ---------------------------------------------------------

def _report(obj, adv):
    return SimpleNamespace(objective_score=obj, advisory_score=adv)


def _verdict(*revs):
    return SimpleNamespace(revisions=[SimpleNamespace(section_index=s, issue=i) for s, i in revs])


def test_plateau_signature_equal_when_same():
    a = plateau_signature(_report(90, 70), _verdict((1, "dark")))
    b = plateau_signature(_report(90, 70), _verdict((1, "dark")))
    assert a == b


def test_plateau_signature_differs_on_score():
    a = plateau_signature(_report(90, 70), _verdict((1, "dark")))
    b = plateau_signature(_report(91, 70), _verdict((1, "dark")))
    assert a != b


def test_plateau_signature_truncates_issue_at_64():
    long = "x" * 200
    sig = plateau_signature(_report(90, 70), _verdict((1, long)))
    # the frozenset holds (section, issue[:64])
    (_, issue) = next(iter(sig[2]))
    assert issue == "x" * 64
    # two issues that differ only past char 64 collapse to the same signature
    other = plateau_signature(_report(90, 70), _verdict((1, "x" * 64 + "DIFFERENT")))
    assert sig == other


# -- design_implicated ---------------------------------------------------------

def _plan(*effect_types_per_section):
    return SimpleNamespace(sections=[SimpleNamespace(effect_types=list(e)) for e in effect_types_per_section])


def _finding(section_index, metric, detail):
    return SimpleNamespace(section_index=section_index, metric=metric, detail=detail)


def test_design_implicated_rules_metric_naming_effect():
    plan = _plan(["Twinkle", "Bars"])
    findings = [_finding(0, "rules", "Twinkle is too sparse for the energy")]
    assert design_implicated(plan, 0, findings) is True


def test_design_implicated_requires_rules_metric():
    plan = _plan(["Twinkle"])
    findings = [_finding(0, "coverage", "Twinkle is too sparse")]
    assert design_implicated(plan, 0, findings) is False


def test_design_implicated_requires_effect_mention():
    plan = _plan(["Twinkle"])
    findings = [_finding(0, "rules", "the section is too busy")]
    assert design_implicated(plan, 0, findings) is False


def test_design_implicated_wrong_section():
    plan = _plan(["Twinkle"], ["Bars"])
    findings = [_finding(0, "rules", "Twinkle too sparse")]
    assert design_implicated(plan, 1, findings) is False


def test_design_implicated_out_of_range():
    plan = _plan(["Twinkle"])
    assert design_implicated(plan, 5, [_finding(5, "rules", "Twinkle")]) is False
    assert design_implicated(None, 0, []) is False


# -- BestTracker: boundary arithmetic (margin defaults to REGRESS_MARGIN=1) -----

def test_best_tracker_revert_below_margin():
    t = BestTracker(["a"], {"applied": 0}, obj=90)
    # obj strictly below best-margin (90-1=89) reverts
    assert t.assess(88).reverted is True
    # obj == best - margin (89) does NOT revert (keeps)
    assert t.assess(89).reverted is False


def test_best_tracker_gain_above_margin():
    t = BestTracker(["a"], {"applied": 0}, obj=90)
    assert t.assess(92).gained is True          # 92 > 90+1
    assert t.assess(91).gained is False         # obj == best + margin keeps-without-gain
    assert t.assess(91).reverted is False


def test_best_tracker_keep_updates_best_and_resets_stall_only_on_gain():
    t = BestTracker(["a"], {"applied": 0}, obj=90)
    t.stall = 1
    t.keep(["b"], {"applied": 1}, 91, gained=False)   # held objective: stall unchanged
    assert t.stall == 1
    assert t.best == ["b"] and t.best_obj == 91       # best_obj = max(90, 91)
    t.stall = 2
    t.keep(["c"], {"applied": 2}, 95, gained=True)    # gain resets stall
    assert t.stall == 0 and t.best_obj == 95


def test_best_tracker_keep_best_obj_is_max():
    t = BestTracker(["a"], {"applied": 0}, obj=90)
    t.keep(["b"], {"applied": 1}, 85, gained=False)   # a held-but-lower obj still keeps instrs
    assert t.best_obj == 90                            # but best_obj never decreases


def test_best_tracker_revert_and_on_reverted():
    t = BestTracker(["best"], {"applied": "B"}, obj=90)
    instr, applied = t.revert()
    assert instr == ["best"] and applied == {"applied": "B"}
    t.on_reverted({"applied": "reemit"})
    assert t.best_applied == {"applied": "reemit"}     # best_applied tracks the re-emit
    assert t.best == ["best"]                           # best instructions unchanged
    assert t.open_is_best is True
    assert t.stall == 1                                 # a revert bumps the stall counter


def test_best_tracker_stalled_property():
    t = BestTracker(["a"], {}, obj=90, stall_limit=2)
    assert t.stalled is False
    t.stall = 2
    assert t.stalled is True


# -- EscalationLedger ----------------------------------------------------------

def test_escalation_once_per_run():
    led = EscalationLedger()
    plan = _plan(["Twinkle"])
    findings = [_finding(0, "rules", "Twinkle too sparse")]
    # implicated path escalates the first time
    assert led.should_escalate(0, plan, findings, prior=set()) is True
    led.mark_redesigned(0)
    # already redesigned → never again
    assert led.should_escalate(0, plan, findings, prior={0}) is False


def test_escalation_repeat_offender_path():
    led = EscalationLedger()
    plan = _plan(["Bars"])
    # no rules-implication, but section is a repeat offender (in prior) → escalate
    assert led.should_escalate(0, plan, [], prior={0}) is True
    # not a repeat offender and not implicated → no escalation
    assert led.should_escalate(0, plan, [], prior=set()) is False


def test_escalation_ledger_record_and_prior():
    led = EscalationLedger()
    led.record(SimpleNamespace(section_index=2))
    led.record(SimpleNamespace(section_index=5))
    assert led.prior_sections() == {2, 5}
