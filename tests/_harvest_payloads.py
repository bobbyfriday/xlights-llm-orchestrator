"""Regenerate the frozen agent-payload fixtures for tests/test_schema_drift.py.

DELIBERATE regeneration only — run with `XLO_REGEN_PAYLOADS=1 python tests/_harvest_payloads.py`
(never an automatic rewrite). Seeds each payload from a REAL pipeline/agent artifact:

  * song_analysis / music_brief / show_plan / instructions   → the actual cached files the golden
    pipeline writes to disk (trimmed to 1-2 sections by the golden fixture itself).
  * structure/rhythm/harmony/lyric_out, judge_verdict,
    visual_findings, section_plan, section_effects           → the real agent output objects the
    panel / director / generator / judge / visual-critic emit, dumped via model_dump_json.
  * revision_log_record                                       → an existing on-disk revision_log.jsonl
    line (tests/fixtures/revision_logs/), the canonical flight-recorder record.

The payloads are frozen; test_schema_drift.py validates them against the CURRENT models so an
incompatible schema change fails CI.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
PAYLOADS = HERE / "fixtures" / "agent_payloads"


def _write(name: str, obj_json: str) -> None:
    PAYLOADS.mkdir(parents=True, exist_ok=True)
    # round-trip through json so every fixture is pretty-printed and diff-friendly
    (PAYLOADS / name).write_text(json.dumps(json.loads(obj_json), indent=1) + "\n")
    print(f"  wrote {name}")


def harvest() -> None:
    import test_golden_pipeline as gp   # reuse the golden fixtures (real deterministic run)
    from xlights_orchestrator.music_brief import (
        HarmonyOut, LabeledSection, LyricOut, RhythmOut, StructureOut,
    )
    from xlights_orchestrator.refine import JudgeVerdict, RevisionBrief
    from xlights_orchestrator.agents.visual_critic import VisualFinding, VisualFindings

    # 1) Cached pipeline artifacts (real files written to disk by run_pipeline) -----------
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        os.environ["XLO_CACHE_DIR"] = str(tmp / "cache")
        song = tmp / "song.mp3"
        song.write_bytes(b"fake-audio-bytes")

        async def fake_emitter(client, instructions, *, duration_secs, **kw):
            return {"placed": [], "skipped": [], "rendered": True}

        st = gp._run(gp.run_pipeline(
            str(song), client=gp._FakeClient(gp.GROUPS),
            director=gp._test_agent(gp._show_plan()),
            generator=gp._test_agent(gp._section_effects()),
            analyze=lambda p: gp._analysis(), interpret=lambda p, sa: gp._noop_brief(),
            emitter=fake_emitter, use_cache=True, stems=False, timing_tracks=False,
        ))
        # the on-disk caches are the real artifacts (song_analysis / song_description / creative_brief)
        from xlights_orchestrator.pipeline.cache import cache_path, song_key
        key = song_key(str(song))
        _write("song_analysis.json", cache_path(key, "song_analysis").read_text())
        _write("music_brief.json", cache_path(key, "song_description", models=True).read_text())
        _write("show_plan.json", cache_path(key, "creative_brief", models=True).read_text())
        # instructions: the whole realized list (a real EffectInstruction[] cache)
        _write("instructions.json", json.dumps([i.model_dump() for i in st.instructions]))

    # 2) section_plan / section_effects (director + generator sub-outputs) ----------------
    plan = gp._show_plan()
    _write("section_plan.json", plan.sections[0].model_dump_json())
    _write("section_effects.json", gp._section_effects().model_dump_json())

    # 3) per-analyst outputs (the panel's structured agent outputs) -----------------------
    _write("structure_out.json", StructureOut(
        sections=[LabeledSection(start_ms=0, end_ms=12000, label="intro", intensity=0.4,
                                 musical_description="soft pad swells, sparse kick"),
                  LabeledSection(start_ms=12000, end_ms=24000, label="drop", intensity=0.95,
                                 musical_description="full kit + bass, wide synths")],
        repetition_map={"drop": [1]}, candidate_themes=["winter", "wonder"]).model_dump_json())
    _write("rhythm_out.json", RhythmOut(
        groove="driving four-on-the-floor", energy_arc=[0.3, 0.5, 0.9],
        climax_ms=12000, accents_ms=[4000, 12000], builds_ms=[10000], drops_ms=[12000],
        range_note="wide build into the drop").model_dump_json())
    _write("harmony_out.json", HarmonyOut(
        emotional_arc="hopeful, rising", key_mood="C major, bright",
        palette_hint="cool blues into warm gold", harmony_summary="I-V-vi-IV loop",
        transition_cues_ms=[12000]).model_dump_json())
    _write("lyric_out.json", LyricOut(
        narrative_summary="a journey home for the holidays", sentiment="warm, nostalgic",
        featured_lines=["all is calm", "all is bright"],
        lyric_themes=["home", "warmth"]).model_dump_json())

    # 4) judge + visual outputs -----------------------------------------------------------
    _write("judge_verdict.json", JudgeVerdict(
        score=78, verdict="iterate",
        revisions=[RevisionBrief(section_index=1, groups=["SEM_ALL"], issue="drop reads flat",
                                 suggested_fix="add a hero sweep", do_not_repeat="")]).model_dump_json())
    _write("visual_findings.json", VisualFindings(
        summary="coverage good; the drop is under-lit",
        findings=[VisualFinding(section_index=1, severity="warn", aspect="energy",
                                detail="peak section dimmer than the build")]).model_dump_json())

    # 5) revision_log_record: seed from a REAL on-disk jsonl line -------------------------
    jsonl = HERE / "fixtures" / "revision_logs" / "postI1_song" / "revision_log.jsonl"
    first = jsonl.read_text().splitlines()[0]
    _write("revision_log_record.json", first)


if __name__ == "__main__":
    if not os.environ.get("XLO_REGEN_PAYLOADS"):
        sys.exit("refusing to regenerate: set XLO_REGEN_PAYLOADS=1 to rewrite the frozen fixtures")
    sys.path.insert(0, str(HERE))
    print("harvesting agent payloads ->", PAYLOADS)
    harvest()
    print("done.")
