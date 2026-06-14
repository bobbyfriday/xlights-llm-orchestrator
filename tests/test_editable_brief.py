"""Tests for the schema-backed, hand-editable creative brief (Option 1: JSON + $schema in editor)."""

from __future__ import annotations

import json

from xlights_orchestrator.brief_schema import SCHEMA_NAME, build_brief_schema, write_editable_brief
from xlights_orchestrator.show_plan import ShowPlan, SectionPlan

VOCAB = dict(groups=["SEM_ALL", "SEM_SNOWFLAKES"], effect_types=["On", "Twinkle", "Snowflakes"],
             scene_ids=["SC-01", "SC-09"], stems=["drums", "piano"], colors=["red", "green", "white"])


def _sp_props(schema):
    return schema["$defs"]["SectionPlan"]["properties"]


def test_schema_enums_use_the_runs_vocab():
    s = build_brief_schema(**VOCAB)
    p = _sp_props(s)
    assert p["target_groups"]["items"]["enum"] == ["SEM_ALL", "SEM_SNOWFLAKES"]
    assert p["effect_family"]["enum"] == ["On", "Twinkle", "Snowflakes"]
    assert p["effect_types"]["items"]["enum"] == ["On", "Twinkle", "Snowflakes"]
    assert p["scene_id"]["enum"] == ["", "SC-01", "SC-09"]          # "" = freeform allowed
    assert p["follow_stem"]["enum"] == ["", "drums", "piano"]
    assert p["pulse_on"]["enum"] == ["", "beat", "onset"]
    assert p["palette"]["items"]["enum"] == ["red", "green", "white"]


def test_intensity_keeps_0_1_bounds():
    p = _sp_props(build_brief_schema(**VOCAB))
    assert p["intensity"]["minimum"] == 0 and p["intensity"]["maximum"] == 1


def test_write_editable_brief_emits_schema_and_relative_ref(tmp_path):
    plan = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=1000, target_groups=["SEM_ALL"],
                                          effect_family="On", intensity=0.5)])
    path = write_editable_brief(plan, tmp_path, **VOCAB)
    assert (tmp_path / SCHEMA_NAME).exists()
    brief = json.loads(path.read_text())
    assert brief["$schema"] == SCHEMA_NAME                          # relative — VS Code resolves sibling


def test_edited_brief_with_schema_key_round_trips(tmp_path):
    plan = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=1000, target_groups=["SEM_ALL"],
                                          effect_family="On", intensity=0.5, palette=["red"])])
    path = write_editable_brief(plan, tmp_path, **VOCAB)
    # the pipeline reads it back exactly this way — the $schema key must be ignored
    loaded = ShowPlan.model_validate_json(path.read_text())
    assert loaded.sections[0].target_groups == ["SEM_ALL"]
    assert loaded.sections[0].palette == ["red"]
    assert not hasattr(loaded, "$schema")
