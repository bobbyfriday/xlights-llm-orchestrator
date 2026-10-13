"""Tests for the advisory visual findings (qa/visual.py): dark mid-energy + static section over the
rendered `.fseq` lit-coverage series, their threading through `qa.evaluate`, and `qa.write_qa`.

Hermetic: a synthetic .fseq + layout (same writer as test_fseq_metrics) → FseqSeries → ShowPlan.
"""

from __future__ import annotations

import json
import struct

import pytest

pytest.importorskip("zstandard")   # the series needs the [preview] extra (numpy/zstandard)
import zstandard

from xlights_orchestrator import qa
from xlights_orchestrator.qa import visual
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


def _series(tmp_path, rows: list[list[int]]) -> FseqSeries:
    _layout(tmp_path)
    data = bytes(v for frame in rows for v in frame)
    f = tmp_path / "s.fseq"
    _write_fseq(f, 9, data, len(rows))
    idx = group_channel_index(tmp_path / "xlights_rgbeffects.xml", tmp_path / "xlights_networks.xml")
    return FseqSeries(f, idx)


def _plan(intensity_a=0.9, intensity_b=0.9, treatment_a=""):
    # two sections back to back, each 500ms (10 frames @ 50ms); section 0 → GA, section 1 → GB
    return ShowPlan(sections=[
        SectionPlan(start_ms=0, end_ms=500, target_groups=["GA"], effect_family="On",
                    intensity=intensity_a, treatment=treatment_a),
        SectionPlan(start_ms=500, end_ms=1000, target_groups=["GB"], effect_family="On",
                    intensity=intensity_b)])


def _analysis():
    return SongAnalysis(path="s.mp3", duration_s=2.0, sample_rate=44100,
                        beats=[Beat(time=round(i * 0.1, 3)) for i in range(20)],
                        segments=[Segment(start=0, end=1, segment_id="A")],
                        energy_arc=[EnergyPoint(time=0, rms=0.5)])


def _rows(a_fn, b_fn, n=20):
    return [[a_fn(i)] * 3 + [b_fn(i)] * 3 + [0, 0, 0] for i in range(n)]


_DARK = lambda i: 0
_LIT = lambda i: 255
_BLINK = lambda i: 255 if i % 2 == 0 else 0


def _by_metric(findings, metric):
    return [f for f in findings if f.metric == metric]


# -- dark ---------------------------------------------------------------------

def test_dark_energetic_section_flagged(tmp_path):
    s = _series(tmp_path, _rows(_DARK, _LIT))             # GA dark all span, GB lit
    find = visual.evaluate(_plan(), s)
    dark = _by_metric(find, "visual:dark")
    assert [f.section_index for f in dark] == [0]
    f = dark[0]
    assert f.severity == "error" and f.objective is False and f.scope == "section 0"
    assert f.fix and "intensity" in f.fix                 # a plain-language brief edit
    assert "dark" in f.detail


def test_dark_quiet_section_not_flagged(tmp_path):
    s = _series(tmp_path, _rows(_DARK, _DARK))            # everything dark...
    find = visual.evaluate(_plan(intensity_a=0.2, intensity_b=0.3), s)   # ...but both sections quiet
    assert not _by_metric(find, "visual:dark") and not _by_metric(find, "visual:static")


def test_dark_needs_most_of_the_span(tmp_path):
    # GA blinks: lit half the frames → below the floor for 50% of the span, NOT > DARK_SPAN (60%)
    s = _series(tmp_path, _rows(_BLINK, _LIT))
    find = visual.evaluate(_plan(), s)
    assert not [f for f in _by_metric(find, "visual:dark") if f.section_index == 0]


def test_rest_treatment_is_deliberate_restraint(tmp_path):
    s = _series(tmp_path, _rows(_DARK, _LIT))
    find = visual.evaluate(_plan(treatment_a="rest"), s)  # energetic but explicitly `rest`
    assert not [f for f in find if f.section_index == 0]


# -- static -------------------------------------------------------------------

def test_static_energetic_section_flagged(tmp_path):
    s = _series(tmp_path, _rows(_LIT, _BLINK))            # GA a constant wash; GB pulses
    find = visual.evaluate(_plan(), s)
    static = _by_metric(find, "visual:static")
    assert [f.section_index for f in static] == [0]       # the pulsing section is not static
    f = static[0]
    assert f.severity == "warn" and f.objective is False and f.fix
    assert not _by_metric(find, "visual:dark")             # neither section is dark


def test_dark_section_is_not_also_static(tmp_path):
    s = _series(tmp_path, _rows(_DARK, _LIT))             # GA dark (flat by definition)
    find = visual.evaluate(_plan(), s)
    assert not [f for f in _by_metric(find, "visual:static") if f.section_index == 0]


def test_static_quiet_section_not_flagged(tmp_path):
    s = _series(tmp_path, _rows(_LIT, _LIT))
    find = visual.evaluate(_plan(intensity_a=0.3, intensity_b=0.3), s)
    assert find == []


# -- neutrality + threading ---------------------------------------------------

def test_no_series_no_findings():
    assert visual.evaluate(_plan(), None) == []
    assert visual.evaluate(None, object()) == []
    rep = qa.evaluate([], _analysis(), _plan(), {"placed": [], "skipped": []}, ["GA", "GB"])
    assert not [f for f in rep.findings if f.metric.startswith("visual:")]


def test_qa_evaluate_threads_visual_findings_without_touching_objective(tmp_path):
    s = _series(tmp_path, _rows(_DARK, _LIT))
    plan = _plan()
    base = qa.evaluate([], _analysis(), plan, {"placed": [], "skipped": []}, ["GA", "GB"])
    withs = qa.evaluate([], _analysis(), plan, {"placed": [], "skipped": []}, ["GA", "GB"],
                        fseq_series=s)
    assert withs.objective_score == base.objective_score
    assert withs.advisory_score == base.advisory_score
    assert withs.subscores.keys() >= base.subscores.keys()
    assert not any(k.startswith("visual:") for k in withs.subscores)     # findings only, no score
    vis = [f for f in withs.findings if f.metric.startswith("visual:")]
    assert {f.metric for f in vis} == {"visual:dark", "visual:static"}  # GA dark, GB a constant wash
    assert all(f.objective is False and f.section_index is not None for f in vis)


# -- qa.json ------------------------------------------------------------------

def test_write_qa_dumps_report_with_summary_and_fix(tmp_path):
    s = _series(tmp_path, _rows(_DARK, _LIT))
    rep = qa.evaluate([], _analysis(), _plan(), {"placed": [], "skipped": []}, ["GA", "GB"],
                      fseq_series=s)
    song_dir = tmp_path / "song"
    path = qa.write_qa(song_dir, rep)
    assert path == song_dir / "qa.json" and path.exists()
    data = json.loads(path.read_text())
    assert data["objective_score"] == rep.objective_score
    assert data["advisory_score"] == rep.advisory_score
    assert data["subscores"] == rep.subscores
    assert len(data["findings"]) == len(rep.findings)
    sev = {"info": 0, "warn": 0, "error": 0}
    for f in rep.findings:
        sev[f.severity] += 1
    assert data["summary"] == {**sev, "total": len(rep.findings)}
    dark = next(f for f in data["findings"] if f["metric"] == "visual:dark")
    assert dark["section_index"] == 0 and dark["severity"] == "error" and dark["objective"] is False
    assert dark["fix"]                                     # the subclass field survives the dump
    assert data["summary"]["error"] >= 1
