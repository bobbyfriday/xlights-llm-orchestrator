"""Unit tests for the per-run degradations collector (I5)."""

from __future__ import annotations

from xlights_orchestrator import degradations as D


class _RaisingDetail:
    def __str__(self):
        raise RuntimeError("detail str() blew up")


def test_note_no_active_log_is_noop_and_never_raises(caplog):
    D._current.set(None)                              # no active run
    with caplog.at_level("WARNING"):
        D.note("visual:critique", "boom")             # must still log, never raise
    assert D.current() is None
    assert any("visual:critique" in r.message for r in caplog.records)


def test_note_swallows_a_raising_detail():
    D.start_run()
    D.note("visual:critique", _RaisingDetail())        # str() raises → swallowed to debug
    # the collector stays usable and empty (nothing recorded from the failed note)
    assert D.current().summary() == []


def test_dedup_counts_and_keeps_first_detail():
    dl = D.start_run()
    D.note("visual:critique", "first failure", stage="refine")
    D.note("visual:critique", "second failure", stage="refine")
    items = dl.summary()
    assert len(items) == 1
    assert items[0].count == 2
    assert items[0].detail == "first failure"          # first occurrence kept (the root cause)
    assert items[0].stage == "refine"


def test_render_summary_empty_vs_non_empty():
    dl = D.start_run()
    assert D.render_summary(dl) == "no degradations"
    D.note("audio:stems", "backends failed", stage="analyze")
    text = D.render_summary(dl)
    assert "degradations (1)" in text and "audio:stems" in text and "analyze" in text


def test_contextvar_isolation_across_runs():
    dl1 = D.start_run()
    D.note("audio:lyrics", "x")
    assert len(dl1.summary()) == 1
    dl2 = D.start_run()                                # a new run starts clean
    assert dl2.summary() == []
    assert D.current() is dl2                          # the active collector is the second one


def test_note_once_logs_first_only(caplog):
    dl = D.start_run()
    with caplog.at_level("WARNING"):
        D.note_once("qa:coverage-blind", "blind 1")
        D.note_once("qa:coverage-blind", "blind 2")
        D.note_once("qa:coverage-blind", "blind 3")
    warnings = [r for r in caplog.records if "qa:coverage-blind" in r.message
                and r.levelname == "WARNING"]
    assert len(warnings) == 1                          # WARNING logged exactly once
    assert dl.summary()[0].count == 3                  # but every occurrence is counted


def test_write_json_roundtrip(tmp_path):
    import json
    dl = D.start_run()
    D.note("visual:real-render", "export unavailable", stage="refine")
    p = tmp_path / "degradations.json"
    D.write_json(dl, p)
    data = json.loads(p.read_text())
    assert data == [{"capability": "visual:real-render", "detail": "export unavailable",
                     "count": 1, "stage": "refine"}]
