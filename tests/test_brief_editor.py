"""Tests for the browser brief editor (save round-trip + page render). No real browser/server."""

from __future__ import annotations

import json

import pytest

from xlights_orchestrator.brief_editor import _color_hex_map, render_page, save_brief

SCHEMA = {"$defs": {"SectionPlan": {"properties": {
    "scene_id": {"enum": ["", "SC-01"]},
    "target_groups": {"type": "array", "items": {"enum": ["SEM_ALL", "SEM_SNOWFLAKES"]}},
    "palette": {"type": "array", "items": {"enum": ["red", "white"]}},
    "intensity": {"type": "number", "minimum": 0, "maximum": 1},
    "look": {"type": "string"},
}}}}


def _brief():
    return {
        "$schema": "./creative_brief.schema.json",
        "experience": "opens calm",
        "sections": [{"start_ms": 0, "end_ms": 1000, "target_groups": ["SEM_ALL"],
                      "effect_family": "On", "intensity": 0.5, "palette": ["red"], "look": "calm"}],
        "group_motifs": {"SEM_ALL": {"role": "bed"}},   # NOT rendered by the form — must survive
    }


def test_save_preserves_schema_and_unrendered_fields(tmp_path):
    p = tmp_path / "creative_brief.json"
    edited = _brief()
    edited["sections"][0]["palette"] = ["red", "white"]   # an edit
    save_brief(p, edited)
    out = json.loads(p.read_text())
    assert out["$schema"] == "./creative_brief.schema.json"      # ref kept
    assert out["group_motifs"] == {"SEM_ALL": {"role": "bed"}}   # unrendered field preserved
    assert out["sections"][0]["palette"] == ["red", "white"]     # the edit landed


def test_save_injects_schema_if_missing(tmp_path):
    p = tmp_path / "creative_brief.json"
    b = _brief(); del b["$schema"]
    save_brief(p, b)
    assert json.loads(p.read_text())["$schema"].endswith("creative_brief.schema.json")


def test_save_rejects_invalid_brief(tmp_path):
    p = tmp_path / "creative_brief.json"
    with pytest.raises(Exception):                              # a section missing required fields
        save_brief(p, {"sections": [{"look": "no times or groups"}]})
    assert not p.exists()                                       # nothing written on failure


def test_render_page_embeds_brief_schema_colors():
    html = render_page(_brief(), SCHEMA, {"red": "#ff0000", "white": "#ffffff"})
    assert "opens calm" in html and "SectionPlan" in html and "#ff0000" in html
    assert "__BRIEF__" not in html and "__SCHEMA__" not in html  # placeholders replaced


def test_color_map_resolves_named_colors():
    cm = _color_hex_map()
    assert cm["red"].startswith("#") and len(cm) > 20
