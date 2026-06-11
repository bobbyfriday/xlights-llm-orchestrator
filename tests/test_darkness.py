"""Tests for energy-gated coverage (intentional darkness)."""
from types import SimpleNamespace
from xlights_orchestrator.pipeline.beats import coverage_cap, trim_coverage, MIN_LIT_GROUPS


def _ins(targets):
    return [SimpleNamespace(target=t) for t in targets]


def test_coverage_cap_scales():
    assert coverage_cap(0.0, 10) < coverage_cap(1.0, 10)
    assert coverage_cap(1.0, 10) == 10
    assert coverage_cap(0.0, 10) >= MIN_LIT_GROUPS


def test_trim_quiet_drops_groups_loud_keeps():
    ins = _ins([f"G{i}" for i in range(8)])
    quiet = {i.target for i in trim_coverage(ins, 0.1)}
    loud = {i.target for i in trim_coverage(ins, 1.0)}
    assert len(quiet) < len(loud) == 8
    assert len(quiet) >= MIN_LIT_GROUPS
    assert quiet <= {f"G{i}" for i in range(len(quiet))}     # keeps first-seen (Director order)


def test_trim_never_below_floor():
    assert len({i.target for i in trim_coverage(_ins(["A", "B", "C"]), 0.0)}) >= MIN_LIT_GROUPS
