"""Schema-drift guard: frozen agent payloads must keep validating against the CURRENT models.

Each fixture in tests/fixtures/agent_payloads/ is a real, frozen artifact (see _harvest_payloads.py)
representing one agent output_type or a persisted cache file. This test proves two things:

  1. Every frozen payload still `model_validate_json`s — a field renamed or made required-without-
     default breaks deserialization of already-cached runs, and fails here.
  2. Each model's REQUIRED field set matches required_fields.json — so an *additive* required field
     fails even though the payload happens to include it (the payload alone can't catch that).

FAILURE PROTOCOL (when this test goes red):
  * If you renamed/removed/retyped a field: this would break every cached run. Prefer keeping the
    old field as a backward-compatible field-with-a-default (additive, optional).
  * If a new required field is genuinely necessary: it is a breaking cache change. Regenerate the
    fixtures (`XLO_REGEN_PAYLOADS=1 python tests/_harvest_payloads.py`) AND the manifest (this test
    rewrites it under XLO_REGEN_PAYLOADS=1), AND bump the cache key so stale caches don't shadow the
    new shape — the run.py:390 precedent (`creative_brief` key bumped from `show_plan`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from xlights_core.audio import SongAnalysis
from xlights_orchestrator.agents.visual_critic import VisualFindings
from xlights_orchestrator.music_brief import (
    HarmonyOut, LyricOut, MusicBrief, RhythmOut, StructureOut,
)
from xlights_orchestrator.refine import JudgeVerdict
from xlights_orchestrator.revision_log import RevisionLogRecord
from xlights_orchestrator.show_plan import (
    EffectInstruction, SectionEffects, SectionPlan, ShowPlan,
)

PAYLOADS = Path(__file__).parent / "fixtures" / "agent_payloads"
MANIFEST = PAYLOADS / "required_fields.json"

# fixture file (stem) -> its model. `instructions` is validated item-wise separately.
CASES = {
    "song_analysis": SongAnalysis,
    "music_brief": MusicBrief,
    "show_plan": ShowPlan,
    "section_plan": SectionPlan,
    "section_effects": SectionEffects,
    "structure_out": StructureOut,
    "rhythm_out": RhythmOut,
    "harmony_out": HarmonyOut,
    "lyric_out": LyricOut,
    "judge_verdict": JudgeVerdict,
    "visual_findings": VisualFindings,
    "revision_log_record": RevisionLogRecord,
}

# for the required-fields manifest, `instructions` maps to the per-item model
MANIFEST_MODELS = {**CASES, "instructions_item": EffectInstruction}


@pytest.mark.parametrize("stem, model", list(CASES.items()))
def test_frozen_payload_validates(stem, model):
    payload = (PAYLOADS / f"{stem}.json").read_text()
    model.model_validate_json(payload)      # raises on any incompatible schema drift


def test_instructions_cache_shape():
    """The instructions cache is a list; every item must validate as an EffectInstruction."""
    items = json.loads((PAYLOADS / "instructions.json").read_text())
    assert isinstance(items, list) and items
    for it in items:
        EffectInstruction.model_validate(it)


def test_required_fields_match_manifest():
    """An additive REQUIRED field (even one the payload happens to include) is a breaking cache
    change — compare each model's required set against the frozen manifest."""
    current = {name: sorted(m.model_json_schema().get("required", []))
               for name, m in MANIFEST_MODELS.items()}
    if os.environ.get("XLO_REGEN_PAYLOADS"):
        MANIFEST.write_text(json.dumps(current, indent=1) + "\n")
        return
    frozen = json.loads(MANIFEST.read_text())
    assert current == frozen, (
        "model required-fields changed vs the manifest. If intentional and additive-required, "
        "regenerate: XLO_REGEN_PAYLOADS=1 python tests/_harvest_payloads.py (and bump the cache key)."
    )


def test_all_output_types_have_a_payload():
    """Guard the guard: every agent output_type / cache model in the manifest has a fixture."""
    have = {p.stem for p in PAYLOADS.glob("*.json")} - {"required_fields"}
    expected = set(CASES) | {"instructions"}
    missing = expected - have
    assert not missing, f"missing frozen payloads: {sorted(missing)}"
