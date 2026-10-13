"""`validate_brief`: one error class per test, the gap check, the warning path, and a clean brief.

Briefs are built as plain dicts (never via `SectionPlan(...)`) so these tests hold whether or not
the model already declares the optional `fabric` field.
"""

from __future__ import annotations

import copy
import json

from xlights_orchestrator.pipeline.validate_brief import (
    ALLOWED_CAP,
    ValidationResult,
    summary_line,
    validate_brief,
    write_validation,
)

VOCAB = {
    "groups": ["SEM_ALL", "SEM_ROOF", "SEM_BEAT_ARCHES"],
    "effect_types": ["On", "Twinkle", "SingleStrand", "Spirals", "Ripple"],
    "cellable": ["SingleStrand", "Spirals", "Ripple"],
    "scene_ids": ["SC-01", "SC-09"],
    "stems": ["drums", "vocals"],
    "colors": ["red", "warm white", "deep blue"],
}
DURATION = 30_000
DOWNBEATS = [0, 2_000, 4_000, 6_000, 8_000, 10_000, 12_000, 14_000, 16_000, 18_000,
             20_000, 22_000, 24_000, 26_000, 28_000, 30_000]


def _section(start, end, **over):
    s = {"start_ms": start, "end_ms": end, "target_groups": ["SEM_ALL"], "effect_family": "On",
         "intensity": 0.5, "palette": ["red"], "effect_types": ["Twinkle"], "pulse_groups": [],
         "scene_id": "", "follow_stem": "", "accent_effect": "", "pulse_on": ""}
    s.update(over)
    return s


def _clean():
    return {
        "$schema": "creative_brief.schema.json",
        "sections": [_section(0, 10_000, effect_family="On"),
                     _section(10_000, 20_000, effect_family="Twinkle"),
                     _section(20_000, 30_000, effect_family="Spirals")],
        "palette": {"name": "x", "colors": ["red", "deep blue"], "mapping": ""},
    }


def _run(brief, **kw):
    kw.setdefault("duration_ms", DURATION)
    return validate_brief(brief, VOCAB, **kw)


def _paths(result: ValidationResult, kind="errors"):
    return [i.path for i in getattr(result, kind)]


# ---------------------------------------------------------------- clean + I/O

def test_clean_brief_is_ok_with_no_findings():
    r = _run(_clean(), downbeats_ms=DOWNBEATS)
    assert r.ok and r.errors == [] and r.warnings == []
    assert summary_line(r) == "brief ok"


def test_accepts_json_text_and_rejects_bad_json():
    assert _run(json.dumps(_clean())).ok
    r = _run("{not json")
    assert not r.ok and r.errors[0].path == "$" and "JSON" in r.errors[0].message


def test_write_validation_shape(tmp_path):
    b = _clean()
    b["sections"][0]["target_groups"] = ["NOPE"]
    r = _run(b)
    path = write_validation(tmp_path, r)
    data = json.loads(path.read_text())
    assert path.name == "validation.json"
    assert set(data) == {"ok", "errors", "warnings"}
    assert data["ok"] is False
    assert set(data["errors"][0]) == {"path", "message", "allowed"}
    assert data["errors"][0]["path"] == "sections[0].target_groups[0]"
    assert "error" in summary_line(r)


# ---------------------------------------------------------------- pydantic

def test_pydantic_errors_map_to_path_and_message():
    b = _clean()
    b["sections"][1]["intensity"] = 1.7
    del b["sections"][2]["effect_family"]
    r = _run(b)
    assert not r.ok
    assert "sections[1].intensity" in _paths(r)
    assert "sections[2].effect_family" in _paths(r)


# ---------------------------------------------------------------- coverage

def test_gap_between_sections_names_both_and_the_gap():
    b = _clean()
    b["sections"][1]["start_ms"] = 11_000          # 1.0 s hole after sections[0]
    r = _run(b)
    assert not r.ok
    e = next(i for i in r.errors if i.path == "sections[1].start_ms")
    assert "sections[0]" in e.message and "sections[1]" in e.message and "1.00s" in e.message


def test_gap_within_tolerance_is_fine():
    b = _clean()
    b["sections"][1]["start_ms"] = 10_300
    assert _run(b).ok


def test_overlap_beyond_tolerance_is_an_error():
    b = _clean()
    b["sections"][1]["start_ms"] = 9_000
    r = _run(b)
    e = next(i for i in r.errors if i.path == "sections[1].start_ms")
    assert "overlaps" in e.message


def test_out_of_order_sections_are_an_error():
    b = _clean()
    b["sections"][0], b["sections"][1] = b["sections"][1], b["sections"][0]
    r = _run(b)
    assert any("ordered by start_ms" in i.message for i in r.errors)


def test_coverage_must_reach_zero_and_duration():
    b = _clean()
    b["sections"][0]["start_ms"] = 1_000
    b["sections"][-1]["end_ms"] = 28_000
    r = _run(b)
    assert "sections[0].start_ms" in _paths(r)
    assert "sections[2].end_ms" in _paths(r)
    assert any("before sections[0]" in i.message for i in r.errors)
    assert any("after sections[2]" in i.message for i in r.errors)


def test_end_before_start_is_an_error():
    b = _clean()
    b["sections"][0]["end_ms"] = 0
    r = _run(b)
    assert any(i.path == "sections[0].end_ms" and "after start_ms" in i.message for i in r.errors)


def test_empty_sections_is_an_error():
    r = _run({"sections": []})
    assert not r.ok and any(i.path == "sections" for i in r.errors)


# ---------------------------------------------------------------- membership

def test_unknown_target_group_with_allowed():
    b = _clean()
    b["sections"][2]["target_groups"] = ["SEM_ALL", "SEM_NOPE"]
    r = _run(b)
    e = next(i for i in r.errors if i.path == "sections[2].target_groups[1]")
    assert e.allowed == VOCAB["groups"]


def test_unknown_pulse_group():
    b = _clean()
    b["sections"][0]["pulse_groups"] = ["ARCHES"]
    r = _run(b)
    assert "sections[0].pulse_groups[0]" in _paths(r)


def test_unknown_effect_family_types_and_accent():
    b = _clean()
    b["sections"][0]["effect_family"] = "Fireworks"
    b["sections"][1]["effect_types"] = ["Twinkle", "Lasers"]
    b["sections"][2]["accent_effect"] = "Glitter"
    r = _run(b)
    assert {"sections[0].effect_family", "sections[1].effect_types[1]", "sections[2].accent_effect"} <= set(_paths(r))
    e = next(i for i in r.errors if i.path == "sections[0].effect_family")
    assert e.allowed == VOCAB["effect_types"]


def test_effect_display_names_are_accepted_space_squeezed():
    b = _clean()
    b["sections"][0]["effect_family"] = "Single Strand"     # guides' display name
    assert _run(b).ok


def test_unknown_scene_id_and_blank_allowed():
    b = _clean()
    b["sections"][0]["scene_id"] = "SC-99"
    r = _run(b)
    e = next(i for i in r.errors if i.path == "sections[0].scene_id")
    assert e.allowed == ["SC-01", "SC-09"]
    b["sections"][0]["scene_id"] = ""
    assert _run(b).ok


def test_unknown_follow_stem():
    b = _clean()
    b["sections"][1]["follow_stem"] = "bass"
    r = _run(b)
    e = next(i for i in r.errors if i.path == "sections[1].follow_stem")
    assert e.allowed == ["drums", "vocals"]


def test_pulse_on_must_be_blank_beat_or_onset():
    b = _clean()
    b["sections"][1]["pulse_on"] = "bar"
    r = _run(b)
    e = next(i for i in r.errors if i.path == "sections[1].pulse_on")
    assert e.allowed == ["", "beat", "onset"]
    for ok in ("", "beat", "onset"):
        b["sections"][1]["pulse_on"] = ok
        assert _run(b).ok


def test_palette_colors_named_or_hex_section_and_show():
    b = _clean()
    b["sections"][0]["palette"] = ["red", "Warm-White", "#1A2B3C", "chartreuse"]
    b["palette"]["colors"] = ["deep blue", "#zzzzzz"]
    r = _run(b)
    paths = _paths(r)
    assert "sections[0].palette[3]" in paths
    assert "palette.colors[1]" in paths
    assert "sections[0].palette[1]" not in paths and "sections[0].palette[2]" not in paths


def test_palette_unchecked_when_vocab_has_no_colors():
    b = _clean()
    b["sections"][0]["palette"] = ["chartreuse"]
    vocab = dict(VOCAB, colors=[])
    assert validate_brief(b, vocab, duration_ms=DURATION).ok


# ---------------------------------------------------------------- fabric (raw dict; model-agnostic)

def test_fabric_carrier_must_be_cellable():
    b = _clean()
    b["sections"][0]["fabric"] = {"carrier": "Twinkle"}       # placeable but not cellable
    r = _run(b)
    e = next(i for i in r.errors if i.path == "sections[0].fabric.carrier")
    assert e.allowed == VOCAB["cellable"]


def test_fabric_alternation_and_cell_beats():
    b = _clean()
    b["sections"][0]["fabric"] = {"carrier": "SingleStrand", "alternation": "zigzag", "cell_beats": 9}
    r = _run(b)
    paths = _paths(r)
    assert "sections[0].fabric.alternation" in paths
    assert "sections[0].fabric.cell_beats" in paths
    e = next(i for i in r.errors if i.path == "sections[0].fabric.alternation")
    assert e.allowed == ["chase", "pingpong", "all", "sparse"]


def test_fabric_valid_and_empty_forms_pass():
    b = _clean()
    b["sections"][0]["fabric"] = {"carrier": "SingleStrand", "alternation": "pingpong", "cell_beats": 2, "blend": "Max"}
    b["sections"][1]["fabric"] = {"carrier": "", "alternation": "", "cell_beats": None, "blend": ""}
    b["sections"][2]["fabric"] = None
    assert _run(b).ok


def test_fabric_must_be_an_object():
    b = _clean()
    b["sections"][0]["fabric"] = "pingpong"
    r = _run(b)
    assert any(i.path == "sections[0].fabric" for i in r.errors)


# ---------------------------------------------------------------- warnings

def test_off_downbeat_boundary_is_a_warning_not_an_error():
    b = _clean()
    b["sections"][1]["start_ms"] = 10_900          # 0.9 s past the 10.0 s downbeat (tolerance 0.5 s)
    b["sections"][0]["end_ms"] = 10_900
    r = _run(b, downbeats_ms=DOWNBEATS)
    assert r.ok and r.errors == []
    w = next(i for i in r.warnings if i.path == "sections[1].start_ms")
    assert "downbeat" in w.message
    assert "warning" in summary_line(r)


def test_no_downbeats_means_no_boundary_warnings():
    b = _clean()
    b["sections"][1]["start_ms"] = 10_400
    b["sections"][0]["end_ms"] = 10_400
    assert _run(b).warnings == []


def test_long_section_warns():
    b = {"sections": [_section(0, 40_000)]}
    r = validate_brief(b, VOCAB, duration_ms=40_000)
    assert r.ok
    assert any(i.path == "sections[0].end_ms" and "32 s" in i.message for i in r.warnings)


def test_duplicate_adjacent_effect_family_warns():
    b = _clean()
    b["sections"][1]["effect_family"] = "On"
    r = _run(b)
    assert r.ok
    assert any(i.path == "sections[1].effect_family" and "repeats" in i.message for i in r.warnings)
    assert not any(i.path == "sections[2].effect_family" for i in r.warnings)


# ---------------------------------------------------------------- bounded allowed lists

def test_allowed_lists_are_capped_with_a_more_marker():
    vocab = copy.deepcopy(VOCAB)
    vocab["groups"] = [f"G{n:03d}" for n in range(ALLOWED_CAP + 25)]
    b = _clean()
    for s in b["sections"]:
        s["target_groups"] = ["G000"]
    b["sections"][0]["target_groups"] = ["nope"]
    r = validate_brief(b, vocab, duration_ms=DURATION)
    e = r.errors[0]
    assert len(e.allowed) == ALLOWED_CAP + 1
    assert e.allowed[-1] == "+25 more"


def test_membership_errors_still_reported_when_pydantic_fails():
    b = _clean()
    b["sections"][0]["intensity"] = 5           # pydantic error
    b["sections"][1]["target_groups"] = ["X"]   # membership error — must still surface
    r = _run(b)
    assert {"sections[0].intensity", "sections[1].target_groups[0]"} <= set(_paths(r))
