"""Tests for the Tier-0 rendered-pixel QA metrics (qa/fseq_metrics.py) and their threading.

Hermetic: builds a FseqSeries from a synthetic .fseq + layout (reusing test_preview's writer),
then a ShowPlan, and asserts the coverage/motion/sync/rhyme families + neutrality (missing series /
kill switch → no findings, unchanged objective).
"""

from __future__ import annotations

import struct

import zstandard

from xlights_orchestrator import qa
from xlights_orchestrator.qa import fseq_metrics
from xlights_orchestrator.show_plan import SectionPlan, ShowPlan
from xlights_core.audio import Beat, EnergyPoint, Segment, SongAnalysis
from xlights_core.preview.metrics import FseqSeries, group_channel_index


def _write_fseq(path, channels, frames_data: bytes, n_frames, step_ms=50):
    comp = zstandard.ZstdCompressor().compress(frames_data)
    h = bytearray(40)
    h[0:4] = b"PSEQ"
    struct.pack_into("<H", h, 4, 40)
    h[6], h[7] = 2, 2
    struct.pack_into("<I", h, 10, channels)
    struct.pack_into("<I", h, 14, n_frames)
    h[18] = step_ms
    h[20] = 1
    h[21] = 1
    struct.pack_into("<I", h, 32, 0)
    struct.pack_into("<I", h, 36, len(comp))
    path.write_bytes(bytes(h) + comp)


def _layout(tmp_path):
    (tmp_path / "xlights_networks.xml").write_text(
        '<Networks><Controller Id="1" Name="C1" Protocol="E131">'
        '<network MaxChannels="9"/></Controller></Networks>')
    (tmp_path / "xlights_rgbeffects.xml").write_text(
        '<xrgb><models>'
        '<model name="A" DisplayAs="Single Line" StartChannel="!C1:1" parm1="1" parm2="1"/>'
        '<model name="B" DisplayAs="Single Line" StartChannel="!C1:4" parm1="1" parm2="1"/>'
        '<model name="C" DisplayAs="Single Line" StartChannel="!C1:7" parm1="1" parm2="1"/>'
        '</models><modelGroups>'
        '<modelGroup name="GA" models="A"/>'
        '<modelGroup name="GB" models="B"/>'
        '<modelGroup name="GC" models="C"/>'
        '</modelGroups></xrgb>')


def _series(tmp_path, rows: list[list[int]], step_ms=50) -> FseqSeries:
    data = bytes(v for frame in rows for v in frame)
    f = tmp_path / "s.fseq"
    _write_fseq(f, 9, data, len(rows), step_ms=step_ms)
    idx = group_channel_index(tmp_path / "xlights_rgbeffects.xml", tmp_path / "xlights_networks.xml")
    return FseqSeries(f, idx)


def _plan(intensity_a=0.9, intensity_b=0.9):
    # two sections back to back, each 500ms (10 frames total @ 50ms)
    return ShowPlan(sections=[
        SectionPlan(start_ms=0, end_ms=500, target_groups=["GA"], effect_family="On", intensity=intensity_a),
        SectionPlan(start_ms=500, end_ms=1000, target_groups=["GB"], effect_family="On", intensity=intensity_b)])


def _analysis():
    beats = [Beat(time=round(i * 0.1, 3)) for i in range(20)]   # a beat every 100ms
    return SongAnalysis(path="s.mp3", duration_s=2.0, sample_rate=44100, beats=beats,
                        segments=[Segment(start=0, end=1, segment_id="A")],
                        energy_arc=[EnergyPoint(time=0, rms=0.5)])


# -- neutrality ---------------------------------------------------------------

def test_missing_series_is_neutral():
    sub, find = fseq_metrics.evaluate(_plan(), _analysis(), None)
    assert sub == {} and find == []


def test_kill_switch_disables(monkeypatch, tmp_path):
    _layout(tmp_path)
    s = _series(tmp_path, [[255, 255, 255, 0, 0, 0, 0, 0, 0]] * 20)
    monkeypatch.setenv("XLO_FSEQ_METRICS", "0")
    assert fseq_metrics.evaluate(_plan(), _analysis(), s) == ({}, [])


def test_qa_evaluate_series_does_not_gate_objective(monkeypatch, tmp_path):
    """Advisory-first: adding fseq_series must not change objective_score vs no series."""
    _layout(tmp_path)
    s = _series(tmp_path, [[0, 0, 0, 0, 0, 0, 0, 0, 0]] * 20)   # all dark → would flag coverage
    plan = _plan()
    base = qa.evaluate([], _analysis(), plan, {"placed": [], "skipped": []}, ["GA", "GB"])
    withs = qa.evaluate([], _analysis(), plan, {"placed": [], "skipped": []}, ["GA", "GB"],
                        fseq_series=s)
    assert withs.objective_score == base.objective_score        # unchanged (advisory-first)
    assert any(f.metric.startswith("fseq:") for f in withs.findings)   # but findings surfaced
    assert all(not f.objective for f in withs.findings if f.metric.startswith("fseq:"))


# -- coverage -----------------------------------------------------------------

def test_coverage_flags_dark_high_energy_section(tmp_path):
    _layout(tmp_path)
    # section 0 (GA) fully dark; section 1 (GB) fully lit
    rows = [[0, 0, 0, 255, 255, 255, 0, 0, 0]] * 20
    s = _series(tmp_path, rows)
    sub, find = fseq_metrics.evaluate(_plan(), _analysis(), s)
    assert "fseq:coverage" in sub
    cov = [f for f in find if f.metric == "fseq:coverage"]
    assert any(f.section_index == 0 for f in cov)               # dark section 0 flagged
    assert not any(f.section_index == 1 for f in cov)           # lit section 1 not flagged


def test_low_intensity_section_exempt_from_coverage(tmp_path):
    _layout(tmp_path)
    rows = [[0, 0, 0, 0, 0, 0, 0, 0, 0]] * 20                   # all dark
    s = _series(tmp_path, rows)
    # both sections quiet (intensity 0.2 < MIN_INTENSITY) → coverage exempt, no findings
    plan = _plan(intensity_a=0.2, intensity_b=0.2)
    sub, find = fseq_metrics.evaluate(plan, _analysis(), s)
    assert not [f for f in find if f.metric == "fseq:coverage"]


# -- motion -------------------------------------------------------------------

def test_motion_flags_static_but_not_moving(tmp_path):
    _layout(tmp_path)
    # section 0 (GA) blinks (high motion); section 1 (GB) constant lit (static)
    rows = []
    for i in range(20):
        a = 255 if i % 2 == 0 else 0
        rows.append([a, a, a, 200, 200, 200, 0, 0, 0])
    s = _series(tmp_path, rows)
    _sub, find = fseq_metrics.evaluate(_plan(), _analysis(), s)
    mot = [f for f in find if f.metric == "fseq:motion"]
    assert any(f.section_index == 1 for f in mot)               # static lit section flagged
    assert not any(f.section_index == 0 for f in mot)           # blinking section not flagged


# -- sync ---------------------------------------------------------------------

def test_sync_scores_beat_aligned_brightness(tmp_path):
    _layout(tmp_path)
    # GA pulses exactly on the 100ms beat grid (frames 0,2,4,6,8) → should correlate
    rows = []
    for i in range(20):
        a = 255 if i % 2 == 0 else 0
        rows.append([a, a, a, 0, 0, 0, 0, 0, 0])
    s = _series(tmp_path, rows)
    sub, _find = fseq_metrics.evaluate(_plan(intensity_a=0.9, intensity_b=0.9), _analysis(), s)
    assert "fseq:sync" in sub                                   # a sync subscore was produced


# -- rhyme / range ------------------------------------------------------------

def test_rhyme_similarity_for_repeated_sections(tmp_path):
    _layout(tmp_path)
    # two identical sections → their brightness signatures rhyme (cosine ≈ 1)
    rows = [[200, 200, 200, 100, 100, 100, 0, 0, 0]] * 20
    s = _series(tmp_path, rows)
    sub, find = fseq_metrics.evaluate(_plan(), _analysis(), s, repetition_map={"chorus": [0, 1]})
    # identical signatures per group → high rhyme, no rhyme failure
    assert sub.get("fseq:rhyme", 0) >= 75
    assert not [f for f in find if f.metric == "fseq:rhyme"]


def test_range_reflects_brightness_spread(tmp_path):
    _layout(tmp_path)
    # section 0 bright, section 1 dim → nonzero dynamic range
    rows = ([[255, 255, 255, 0, 0, 0, 0, 0, 0]] * 10
            + [[0, 0, 0, 20, 20, 20, 0, 0, 0]] * 10)
    s = _series(tmp_path, rows)
    sub, _find = fseq_metrics.evaluate(_plan(), _analysis(), s)
    assert sub.get("fseq:range", 0) > 0
