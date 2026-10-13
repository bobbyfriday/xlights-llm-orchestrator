"""`pipeline.vocab`: vocab.json's shape and that the written schema's enums match it."""

from __future__ import annotations

import json

from xlights_orchestrator.brief_schema import SCHEMA_NAME
from xlights_orchestrator.pipeline.vocab import (
    VOCAB_KEYS,
    VOCAB_NAME,
    build_vocab,
    load_vocab,
    schema_from_vocab,
    write_brief_schema,
    write_vocab,
    write_vocab_and_schema,
)

ARGS = dict(groups=["SEM_ALL", "SEM_ROOF", "SEM_ALL", ""],   # dup + blank dropped, order kept
            effect_types=["Twinkle", "On", "SingleStrand"],
            cellable=["SingleStrand", "Spirals"],            # Spirals not placeable → dropped
            scene_ids=["SC-09", "SC-01"],
            stems=["drums", "vocals"],
            colors=["red", "warm white"])


def test_build_vocab_keys_and_normalization():
    v = build_vocab(**ARGS)
    assert tuple(v) == VOCAB_KEYS == ("groups", "effect_types", "cellable", "scene_ids", "stems", "colors")
    assert v["groups"] == ["SEM_ALL", "SEM_ROOF"]
    assert v["effect_types"] == ["On", "SingleStrand", "Twinkle"]
    assert v["cellable"] == ["SingleStrand"]
    assert v["scene_ids"] == ["SC-01", "SC-09"]
    assert v["stems"] == ["drums", "vocals"]
    assert v["colors"] == ["red", "warm white"]


def test_write_and_load_round_trip(tmp_path):
    v = build_vocab(**ARGS)
    path = write_vocab(tmp_path, v)
    assert path.name == VOCAB_NAME
    assert json.loads(path.read_text()) == v
    assert load_vocab(tmp_path) == v


def test_load_vocab_tolerates_missing_keys(tmp_path):
    (tmp_path / VOCAB_NAME).write_text(json.dumps({"groups": ["A"]}))
    v = load_vocab(tmp_path)
    assert v["groups"] == ["A"] and v["cellable"] == [] and v["colors"] == []


def test_written_schema_enums_match_vocab_json(tmp_path):
    vocab_path, schema_path = write_vocab_and_schema(tmp_path, build_vocab(**ARGS))
    assert schema_path.name == SCHEMA_NAME and vocab_path.name == VOCAB_NAME
    vocab = json.loads(vocab_path.read_text())
    schema = json.loads(schema_path.read_text())
    sp = schema["$defs"]["SectionPlan"]["properties"]
    assert sp["target_groups"]["items"]["enum"] == vocab["groups"]
    assert sp["pulse_groups"]["items"]["enum"] == vocab["groups"]
    assert sp["effect_family"]["enum"] == vocab["effect_types"]
    assert sp["effect_types"]["items"]["enum"] == vocab["effect_types"]
    assert sp["accent_effect"]["enum"] == [""] + vocab["effect_types"]
    assert sp["scene_id"]["enum"] == [""] + vocab["scene_ids"]
    assert sp["follow_stem"]["enum"] == [""] + vocab["stems"]
    assert sp["palette"]["items"]["enum"] == vocab["colors"]
    assert schema["$defs"]["ShowPalette"]["properties"]["colors"]["items"]["enum"] == vocab["colors"]


def test_schema_from_vocab_works_with_or_without_cellable_kwarg():
    # Whether or not `build_brief_schema` has grown a `cellable=` kwarg (lane A), this must not raise
    # and must carry the group enum.
    s = schema_from_vocab(build_vocab(**ARGS))
    assert s["$defs"]["SectionPlan"]["properties"]["target_groups"]["items"]["enum"] == ["SEM_ALL", "SEM_ROOF"]


def test_write_brief_schema_alone(tmp_path):
    p = write_brief_schema(tmp_path, build_vocab(**ARGS))
    assert p.exists() and p.name == SCHEMA_NAME
