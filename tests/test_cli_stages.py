"""The `xlo` stage commands, in-process (`cli.main([...])`) over a tmp song dir built from the
golden fixture analysis and a hand-written brief (labels + a `fabric` block). Hermetic: a fake
`XLightsClient` for `groups`/`apply`/`finalize`, a fake `AudioAnalyzer` for `analyze`, no model
calls, no API keys, no network.

Asserts the file contract: missing-prerequisite exits (code 2, message naming the file and its
stage), `groups` → vocab + schema + layout, `validate-brief` exit codes, `realize` byte-identical
and covering every section (and refusing an invalid brief), `apply` → `applied.json` with
per-instruction placed/skipped outcomes, `qa` → `qa.json`, `stills` → the hint when no `.fseq`,
`video-plan` with `--plan-only`, a valid story, an invalid one, and `--allow-inherit`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from xlights_core.exceptions import XLightsResponseError, XLightsTargetMissing
from xlights_orchestrator import cli
from xlights_orchestrator.brief_schema import SCHEMA_NAME
from xlights_orchestrator.pipeline import effect_meta
from xlights_orchestrator.pipeline.cache import song_key
from xlights_orchestrator.pipeline.stage_io import (
    APPLIED_NAME, BRIEF_NAME, INSTRUCTIONS_NAME, LAYOUT_NAME, STORY_NAME, VIDEO_SCRIPT_NAME,
)
from xlights_orchestrator.pipeline.vocab import VOCAB_NAME, build_vocab, write_vocab_and_schema
from xlights_orchestrator.show_plan import BLEND_METHODS

FIXTURES = Path(__file__).parent / "fixtures" / "cache_payloads"
ANALYSIS = FIXTURES / "song_analysis.json"          # 24 s, 120 BPM, two segments, a drums stem

GROUPS = ["SEM_ALL", "SEM_BAND_GROUND", "SEM_FOCAL", "SEM_ARCHES", "SEM_CANES", "SEM_MINITREES",
          "SEM_SNOWFLAKES", "SEM_SPINNERS", "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT"]
EFFECTS = ["On", "Twinkle", "Spirals", "Fireworks", "Wave", "SingleStrand", "Bars", "Shockwave",
           "Strobe", "Color Wash"]


def _brief() -> dict:
    """Two sections like the golden plan — a quiet verse and a full chorus whose `fabric`
    directs a Wave ping-pong carrier blended Brightness — with labels."""
    return {
        "$schema": SCHEMA_NAME,
        "concept": "stage fixture",
        "palette": {"name": "test", "colors": ["Red", "Green", "Blue"], "mapping": ""},
        "sections": [
            {"start_ms": 0, "end_ms": 12000, "label": "verse 1",
             "target_groups": ["SEM_ARCHES", "SEM_CANES"], "effect_family": "On",
             "intensity": 0.45, "palette": ["Red", "Green"], "effect_types": ["Twinkle"],
             "pulse_groups": ["SEM_ARCHES"], "pulse_on": "beat"},
            {"start_ms": 12000, "end_ms": 24000, "label": "chorus",
             "target_groups": ["SEM_ALL", "SEM_FOCAL", "SEM_CANES", "SEM_ARCHES"],
             "effect_family": "On", "intensity": 0.92, "palette": ["Blue", "Red"],
             "effect_types": ["Spirals", "Fireworks"],
             "pulse_groups": ["SEM_CANES", "SEM_ARCHES"], "pulse_on": "onset",
             "fabric": {"carrier": "Wave", "alternation": "pingpong", "cell_beats": 2,
                        "blend": "Brightness"}},
        ],
        "key_moments": [{"at_ms": 12000, "kind": "climax", "treatment": "the drop"}],
    }


def _story(*idx: int) -> dict:
    return {"logline": "A vigil kept across generations.", "motifs": ["window", "candle"],
            "beats": [{"section_index": i, "title": f"beat {i}", "imagery": "snow at a window",
                       "action": "flakes drift", "camera": "slow push-in", "lighting": "deep blue",
                       "motifs": ["window"], "procedural_stand_in": "snow and light"} for i in idx]}


# -- harness -----------------------------------------------------------------------------------

@pytest.fixture
def song_dir(tmp_path, monkeypatch) -> Path:
    """A fresh song dir under a tmp cache root with the fixture analysis, vocab + schema, and
    the brief — the state after `analyze` + `groups` + the design conversation."""
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(cli, "load_env", lambda: None)
    d = tmp_path / "cache" / "orchestrator" / "song--0123456789abcdef"
    d.mkdir(parents=True)
    shutil.copy(ANALYSIS, d / "song_analysis.json")
    write_vocab_and_schema(d, build_vocab(groups=GROUPS, effect_types=EFFECTS,
                                          cellable=sorted(effect_meta.DURATION_CELLABLE),
                                          scene_ids=["SC-01"], stems=["drums"],
                                          colors=["Red", "Green", "Blue", "White"]))
    (d / BRIEF_NAME).write_text(json.dumps(_brief(), indent=1))
    return d


def _main(argv, capsys):
    """Run the CLI in-process; returns (exit_code, stdout, stderr). 0 = returned normally."""
    code = 0
    try:
        cli.main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    out = capsys.readouterr()
    return code, out.out, out.err


class _FakeClient:
    """Enough of `XLightsClient` for groups / apply / finalize. The probe in `targetable_groups`
    needs `close_sequence`; raising a plain error there makes it fall back to the full list."""

    instances: list = []

    def __init__(self, *a, **kw):
        self.groups = list(GROUPS)
        self.models = ["Matrix1", "Arch1"]
        self.show_folder = str(_FakeClient.show_folder)
        self.calls: list[tuple] = []
        _FakeClient.instances.append(self)

    show_folder: Path = Path("/nonexistent")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_group_names(self):
        return list(self.groups)

    async def get_model_names(self):
        return list(self.models)

    async def get_models(self):
        return list(self.groups) + list(self.models)

    async def get_show_folder(self):
        return self.show_folder

    async def close_sequence(self, *, force=False, quiet=False):
        self.calls.append(("close",))

    async def new_sequence(self, *, duration_secs, frame_ms, force, view=None):
        self.calls.append(("new", duration_secs, view))

    async def add_effect(self, *a, **kw):
        self.calls.append(("add_effect",))
        return True

    async def render_all(self, *, highdef=False):
        self.calls.append(("render",))

    async def save_sequence(self, name=None):
        self.calls.append(("save", name))


@pytest.fixture
def fake_client(monkeypatch, tmp_path):
    _FakeClient.instances = []
    _FakeClient.show_folder = tmp_path / "show"
    _FakeClient.show_folder.mkdir(exist_ok=True)
    monkeypatch.setattr(cli, "XLightsClient", _FakeClient)
    return _FakeClient


# -- missing prerequisites ---------------------------------------------------------------------

@pytest.mark.parametrize("argv, missing, hint", [
    (["realize"], BRIEF_NAME, "write it"),
    (["qa"], INSTRUCTIONS_NAME, "run `xlo realize` first"),
    (["apply"], INSTRUCTIONS_NAME, "run `xlo realize` first"),
    (["groups"], "song_analysis.json", "run `xlo analyze` first"),
    (["video-plan", "--matrix-size", "64x32"], BRIEF_NAME, "write it"),
])
def test_missing_prerequisite_exits_2_naming_the_file(tmp_path, monkeypatch, capsys, argv, missing, hint):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    empty = tmp_path / "empty"; empty.mkdir()
    code, out, err = _main(argv + ["--cache", str(empty)], capsys)
    assert code == 2
    assert f"missing {missing}: {hint}" in err
    assert not any(empty.iterdir())                            # nothing written


def test_validate_brief_without_vocab_names_groups(song_dir, capsys):
    (song_dir / VOCAB_NAME).unlink()
    code, _out, err = _main(["validate-brief", "--cache", str(song_dir)], capsys)
    assert code == 2 and "missing vocab.json: run `xlo groups` first" in err
    assert not (song_dir / "validation.json").exists()


def test_song_or_cache_is_required(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    code, _out, _err = _main(["realize"], capsys)
    assert code == 2                                           # argparse: one of --song/--cache


# -- analyze -----------------------------------------------------------------------------------

class _FakeAnalyzer:
    def __init__(self, *a, **kw):
        pass

    def analyze(self, path, *, use_cache=True, stems=False):
        from xlights_core.audio import SongAnalysis
        _FakeAnalyzer.last = {"path": path, "use_cache": use_cache, "stems": stems}
        return SongAnalysis.model_validate_json(ANALYSIS.read_text())

    def attach_lyrics(self, *a, **kw):
        return False

    def refine_instrumental(self, sa, path):
        return False


def test_analyze_song_writes_analysis_and_digest(tmp_path, monkeypatch, capsys):
    from xlights_orchestrator.pipeline import analyze_stage
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(analyze_stage, "AudioAnalyzer", _FakeAnalyzer)
    monkeypatch.setattr(analyze_stage, "fetch_lyrics", lambda p: None)
    song = tmp_path / "my song.mp3"; song.write_bytes(b"fake-audio")
    code, out, _err = _main(["analyze", "--song", str(song)], capsys)
    assert code == 0
    d = tmp_path / "cache" / "orchestrator" / song_key(str(song))
    assert (d / "song_analysis.json").exists() and (d / "analysis_digest.md").exists()
    assert "24.0s" in out and "digest:" in out and "song dir:" in out
    assert _FakeAnalyzer.last["use_cache"] is True and _FakeAnalyzer.last["stems"] is True
    # --no-cache re-analyzes; --cache alone regenerates only the digest (no analyzer at all)
    _main(["analyze", "--song", str(song), "--no-cache"], capsys)
    assert _FakeAnalyzer.last["use_cache"] is False
    monkeypatch.setattr(analyze_stage, "AudioAnalyzer", None)
    (d / "analysis_digest.md").unlink()
    code, out, _err = _main(["analyze", "--cache", str(d)], capsys)
    assert code == 0 and (d / "analysis_digest.md").exists()


# -- groups ------------------------------------------------------------------------------------

def test_groups_writes_vocab_schema_and_layout(song_dir, fake_client, capsys):
    (song_dir / VOCAB_NAME).unlink(); (song_dir / SCHEMA_NAME).unlink()
    code, out, _err = _main(["groups", "--cache", str(song_dir)], capsys)
    assert code == 0
    vocab = json.loads((song_dir / VOCAB_NAME).read_text())
    schema = json.loads((song_dir / SCHEMA_NAME).read_text())
    assert vocab["groups"] == GROUPS                            # the probe fell back to the full list
    assert vocab["stems"] == ["drums"] and vocab["blends"] == list(BLEND_METHODS)
    assert vocab["cellable"] and set(vocab["cellable"]) <= set(vocab["effect_types"])
    sp = schema["$defs"]["SectionPlan"]["properties"]
    assert sp["target_groups"]["items"]["enum"] == vocab["groups"]
    assert schema["$defs"]["SectionFabric"]["properties"]["blend"]["enum"] == [""] + vocab["blends"]
    layout = json.loads((song_dir / LAYOUT_NAME).read_text())
    assert layout["models"] == ["Matrix1", "Arch1"] and layout["show_folder"] == str(fake_client.show_folder)
    assert "targetable groups" in out and "wrote vocab.json" in out


# -- validate-brief ----------------------------------------------------------------------------

def test_validate_brief_ok_exits_0_and_writes_validation(song_dir, capsys):
    code, out, _err = _main(["validate-brief", "--cache", str(song_dir)], capsys)
    assert code == 0 and out.startswith("brief ok")
    v = json.loads((song_dir / "validation.json").read_text())
    assert v["ok"] is True and v["errors"] == []


def test_validate_brief_errors_exit_1(song_dir, capsys):
    b = _brief(); b["sections"][0]["target_groups"] = ["SEM_NOPE"]
    (song_dir / BRIEF_NAME).write_text(json.dumps(b))
    code, out, _err = _main(["validate-brief", "--cache", str(song_dir)], capsys)
    assert code == 1 and "brief has 1 error" in out
    v = json.loads((song_dir / "validation.json").read_text())
    assert v["ok"] is False
    assert v["errors"][0]["path"] == "sections[0].target_groups[0]"
    assert "SEM_ALL" in v["errors"][0]["allowed"]


# -- realize -----------------------------------------------------------------------------------

def test_realize_is_byte_identical_and_covers_every_section(song_dir, capsys):
    code, out, _err = _main(["realize", "--cache", str(song_dir)], capsys)
    assert code == 0 and "realized" in out and "wrote instructions.json" in out
    first = (song_dir / INSTRUCTIONS_NAME).read_bytes()
    instrs = json.loads(first)
    assert len(instrs) > 10
    # every section produced rows (show-level rows such as flashes may carry no section)
    assert {i["section_index"] for i in instrs} >= {0, 1}
    assert {i["section_index"] for i in instrs} <= {0, 1, None}
    # the fabric block landed: Wave cells on the chorus, 2 beats each, blended Brightness
    waves = [i for i in instrs if i["effect_type"] == "Wave" and i["section_index"] == 1]
    assert waves and {i["end_ms"] - i["start_ms"] for i in waves} == {1000}
    assert all(i["extra_settings"].get("T_CHOICE_LayerMethod") == "Brightness" for i in waves)
    # every row names a targetable group and a placeable type with a look
    assert all(i["target"] in GROUPS for i in instrs)
    assert all(i["look_id"] for i in instrs)
    code, _out, _err = _main(["realize", "--cache", str(song_dir)], capsys)
    assert code == 0 and (song_dir / INSTRUCTIONS_NAME).read_bytes() == first
    assert json.loads((song_dir / "validation.json").read_text())["ok"] is True


def test_realize_refuses_an_invalid_brief(song_dir, capsys):
    b = _brief(); b["sections"][1]["fabric"]["blend"] = "Multiply"
    (song_dir / BRIEF_NAME).write_text(json.dumps(b))
    code, _out, err = _main(["realize", "--cache", str(song_dir)], capsys)
    assert code == 1 and "refusing to realize" in err and "fabric.blend" in err
    assert not (song_dir / INSTRUCTIONS_NAME).exists()
    assert json.loads((song_dir / "validation.json").read_text())["ok"] is False


# -- apply -------------------------------------------------------------------------------------

@pytest.fixture
def realized(song_dir, capsys):
    assert _main(["realize", "--cache", str(song_dir)], capsys)[0] == 0
    return song_dir


def test_apply_writes_applied_with_placed_and_skipped(realized, fake_client, monkeypatch, capsys):
    from xlights_orchestrator import effect_emitter

    async def fake_place(client, target, effect_type, look_id, **kw):
        if target == "SEM_CANES":
            raise XLightsTargetMissing(status_code=503, message="Unknown model.", command="addEffect")
        if effect_type == "Fireworks":
            raise XLightsResponseError(status_code=500, message="boom", command="addEffect")
        return "settings"
    monkeypatch.setattr(effect_emitter, "place_preset", fake_place)
    code, out, _err = _main(["apply", "--cache", str(realized)], capsys)
    assert code == 0
    instrs = json.loads((realized / INSTRUCTIONS_NAME).read_text())
    applied = json.loads((realized / APPLIED_NAME).read_text())
    assert applied["sequence"] == "song" and applied["rendered"] is False and applied["saved"] is False
    outcomes = applied["outcomes"]
    assert [o["index"] for o in outcomes] == list(range(len(instrs)))      # one per instruction
    assert all(set(o) >= {"index", "placed", "reason", "layer", "target", "effect",
                          "section_index", "start_ms", "end_ms"} for o in outcomes)
    skipped = [o for o in outcomes if not o["placed"]]
    placed = [o for o in outcomes if o["placed"]]
    assert placed and skipped
    assert all(o["target"] == "SEM_CANES" or o["effect"] == "Fireworks" for o in skipped)
    assert all(o["reason"].startswith(("XLightsTargetMissing:", "XLightsResponseError:")) for o in skipped)
    assert all(o["reason"] == "" and o["layer"] is not None for o in placed)
    assert applied["counts"] == {"instructions": len(instrs), "placed": len(placed), "skipped": len(skipped)}
    assert len(applied["placed"]) == len(placed) and len(applied["skipped"]) == len(skipped)
    assert f"placed {len(placed)} · skipped {len(skipped)} of {len(instrs)}" in out
    assert "skipped" in out and "XLightsTargetMissing" in out
    client = fake_client.instances[-1]
    assert ("render",) not in client.calls and not any(c[0] == "save" for c in client.calls)


def test_apply_render_renders_and_saves(realized, fake_client, monkeypatch, capsys):
    from xlights_orchestrator import effect_emitter

    async def ok(client, target, effect_type, look_id, **kw):
        return "settings"
    monkeypatch.setattr(effect_emitter, "place_preset", ok)
    code, out, _err = _main(["apply", "--cache", str(realized), "--render", "--name", "Show1"], capsys)
    assert code == 0
    applied = json.loads((realized / APPLIED_NAME).read_text())
    assert applied["rendered"] is True and applied["saved"] is True and applied["sequence"] == "Show1"
    assert applied["counts"]["skipped"] == 0
    client = fake_client.instances[-1]
    assert ("render",) in client.calls and ("save", "Show1") in client.calls
    assert "rendered + saved as 'Show1'" in out


# -- qa ----------------------------------------------------------------------------------------

def test_qa_writes_qa_json(realized, capsys):
    code, out, _err = _main(["qa", "--cache", str(realized)], capsys)
    assert code == 0 and out.startswith("qa: objective") and "rendered series: no" in out
    qa = json.loads((realized / "qa.json").read_text())
    assert {"objective_score", "advisory_score", "findings", "subscores", "summary"} <= set(qa)
    assert qa["summary"]["total"] == len(qa["findings"])
    assert all({"scope", "severity", "metric", "detail"} <= set(f) for f in qa["findings"])
    assert "sync" in qa["subscores"] and "placement" in qa["subscores"]


# -- stills ------------------------------------------------------------------------------------

def test_stills_without_fseq_prints_hint_and_exits_0(realized, capsys):
    code, out, _err = _main(["stills", "--cache", str(realized), "--name", "NoSuchSeq"], capsys)
    assert code == 0 and "run: xlo apply --render" in out
    assert not (realized / "stills").exists()


# -- finalize ----------------------------------------------------------------------------------

def test_finalize_saves_under_name(song_dir, fake_client, capsys):
    code, out, _err = _main(["finalize", "--cache", str(song_dir), "--name", "Final1"], capsys)
    assert code == 0 and "saved 'Final1'" in out
    client = fake_client.instances[-1]
    assert ("save", "Final1") in client.calls


# -- video-plan --------------------------------------------------------------------------------

def test_video_plan_requires_matrix_size(song_dir, capsys):
    (song_dir / STORY_NAME).write_text(json.dumps(_story(0, 1)))
    code, _out, err = _main(["video-plan", "--cache", str(song_dir)], capsys)
    assert code == 1 and "--matrix-size is required" in err
    assert not (song_dir / VIDEO_SCRIPT_NAME).exists()


def test_video_plan_plan_only_writes_media_plan_without_a_story(song_dir, capsys):
    code, out, _err = _main(["video-plan", "--cache", str(song_dir), "--plan-only", "--no-veo"], capsys)
    assert code == 0 and "media plan:" in out and "wrote media_plan.json" in out
    mp = json.loads((song_dir / "media_plan.json").read_text())
    assert [s["index"] for s in mp["sections"]] == [0, 1]
    assert [s["label"] for s in mp["sections"]] == ["verse 1", "chorus"]
    assert all(s["medium"] == "procedural" for s in mp["sections"])      # --no-veo: budget 0
    assert all(s["asset"] for s in mp["sections"]) and mp["clips_planned"] == 0
    assert not (song_dir / VIDEO_SCRIPT_NAME).exists()


def test_video_plan_valid_story_writes_script_and_reuses_the_plan(song_dir, capsys):
    _main(["video-plan", "--cache", str(song_dir), "--plan-only", "--veo-clips", "3"], capsys)
    mp_before = json.loads((song_dir / "media_plan.json").read_text())
    (song_dir / STORY_NAME).write_text(json.dumps(_story(0, 1)))
    code, out, _err = _main(["video-plan", "--cache", str(song_dir), "--matrix-size", "64x32",
                             "--veo-clips", "3", "--max-shot-s", "30"], capsys)     # no clip splits
    assert code == 0 and out.startswith("video plan: 2 shots")
    vs = json.loads((song_dir / VIDEO_SCRIPT_NAME).read_text())
    assert [(s["start_ms"], s["end_ms"]) for s in vs["shots"]] == [(0, 12000), (12000, 24000)]
    assert [s["label"] for s in vs["shots"]] == ["verse 1", "chorus"]
    assert not any(s["inherited"] for s in vs["shots"])
    assert vs["constraints"]["width"] == 64 and vs["constraints"]["height"] == 32
    mp_after = json.loads((song_dir / "media_plan.json").read_text())
    assert [(s["index"], s["medium"], s["asset"]) for s in mp_after["sections"]] == \
           [(s["index"], s["medium"], s["asset"]) for s in mp_before["sections"]]
    assert [s["medium"] for s in vs["shots"]] == [s["medium"] for s in mp_after["sections"]]
    md = (song_dir / "video_script.md").read_text()
    assert "video script" in md and "beat 0" in md and "beat 1" in md


def test_video_plan_invalid_story_names_the_section_and_writes_nothing(song_dir, capsys):
    (song_dir / STORY_NAME).write_text(json.dumps(_story(0)))             # no beat for section 1
    code, _out, err = _main(["video-plan", "--cache", str(song_dir), "--matrix-size", "64x32"], capsys)
    assert code == 1 and "no beat for section 1" in err
    assert not (song_dir / VIDEO_SCRIPT_NAME).exists() and not (song_dir / "video_script.md").exists()
    story = _story(0, 1); story["beats"][1]["start_ms"] = 12000             # a time field
    (song_dir / STORY_NAME).write_text(json.dumps(story))
    code, _out, err = _main(["video-plan", "--cache", str(song_dir), "--matrix-size", "64x32"], capsys)
    assert code == 1 and "beats[1] carries a time field 'start_ms'" in err


def test_video_plan_refuses_a_person_in_a_procedural_beat(song_dir, capsys):
    story = _story(0, 1)
    story["beats"][0]["action"] = "a child runs to the window"
    (song_dir / STORY_NAME).write_text(json.dumps(story))
    code, _out, err = _main(["video-plan", "--cache", str(song_dir), "--matrix-size", "64x32",
                             "--no-veo"], capsys)                     # all procedural
    assert code == 1 and "medium contract" in err and "section 0" in err and "'child'" in err
    assert not (song_dir / VIDEO_SCRIPT_NAME).exists()


def test_video_plan_allow_inherit_holds_the_previous_beat(song_dir, capsys):
    (song_dir / STORY_NAME).write_text(json.dumps(_story(0)))
    code, out, _err = _main(["video-plan", "--cache", str(song_dir), "--matrix-size", "64x32",
                             "--allow-inherit"], capsys)
    assert code == 0 and "1 inherited beat" in out
    vs = json.loads((song_dir / VIDEO_SCRIPT_NAME).read_text())
    held = [s for s in vs["shots"] if s["section_index"] == 1]
    assert held and all(s["inherited"] and s["beat"]["title"] == "beat 0" for s in held)
    assert not any(s["inherited"] for s in vs["shots"] if s["section_index"] == 0)


# -- the whole offline chain over --song -------------------------------------------------------

def test_stages_resolve_the_song_dir_from_the_audio_path(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(cli, "load_env", lambda: None)
    # a name no real xLights sandbox holds a rendered .fseq for (the lookup is global)
    song = tmp_path / "Zz Stage Fixture Song.mp3"; song.write_bytes(b"audio!")
    d = tmp_path / "cache" / "orchestrator" / song_key(str(song))
    d.mkdir(parents=True)
    shutil.copy(ANALYSIS, d / "song_analysis.json")
    write_vocab_and_schema(d, build_vocab(groups=GROUPS, effect_types=EFFECTS,
                                          cellable=sorted(effect_meta.DURATION_CELLABLE),
                                          scene_ids=[], stems=["drums"], colors=["Red", "Green", "Blue"]))
    (d / BRIEF_NAME).write_text(json.dumps(_brief()))
    assert _main(["validate-brief", "--song", str(song)], capsys)[0] == 0
    assert _main(["realize", "--song", str(song)], capsys)[0] == 0
    assert (d / INSTRUCTIONS_NAME).exists()
    code, out, _err = _main(["stills", "--song", str(song)], capsys)
    assert code == 0 and "'Zz_Stage_Fixture_Song'" in out               # the name derives from the file
