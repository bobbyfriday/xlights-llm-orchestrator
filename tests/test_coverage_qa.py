"""Tests for the rendered lit-coverage QA metric."""
from types import SimpleNamespace

from xlights_orchestrator import qa
from xlights_orchestrator.qa.coverage import evaluate


def _plan(intensities, span=10000):
    secs = [SimpleNamespace(start_ms=i * span, end_ms=(i + 1) * span, intensity=x)
            for i, x in enumerate(intensities)]
    return SimpleNamespace(sections=secs)


def _sampler(lit_by_section, span=10000):
    return lambda t_ms: lit_by_section[min(t_ms // span, len(lit_by_section) - 1)]


def test_dark_loud_section_gates_with_finding():
    plan = _plan([0.2, 0.9, 0.9])                      # quiet, loud, loud
    score, findings = evaluate(plan, _sampler([100, 5000, 200]))   # sec 2 loud but near-dark
    assert score < 80
    dark = [f for f in findings if f.section_index == 2]
    assert dark and dark[0].severity == "error" and dark[0].metric == "coverage"


def test_lit_loud_sections_score_high_quiet_dark_exempt():
    plan = _plan([0.1, 0.9])                           # quiet+dark is intentional restraint
    score, findings = evaluate(plan, _sampler([50, 5000]))
    assert score == 100 and findings == []


def test_neutral_without_eyes():
    assert evaluate(_plan([0.9]), None) == (100, [])
    def boom(t): raise FileNotFoundError("no fseq")
    assert evaluate(_plan([0.9]), boom) == (100, [])   # sampling failure → never gate blind


def test_entirely_dark_show_is_zero():
    score, findings = evaluate(_plan([0.9, 0.8]), lambda t: 0)
    assert score == 0 and findings[0].severity == "error"


def test_qa_evaluate_folds_coverage_into_objective():
    plan = _plan([0.9])
    args = ([], SimpleNamespace(beats=[]), plan, {"placed": [{"section_index": 0}], "skipped": []}, [])
    base = qa.evaluate(*args)                                       # no sampler → legacy
    assert "coverage" not in base.subscores
    dark = qa.evaluate(*args, sampler=lambda t: 0)                  # dark show drags objective
    assert dark.subscores["coverage"] == 0
    assert dark.objective_score < base.objective_score
