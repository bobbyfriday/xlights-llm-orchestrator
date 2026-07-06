"""CLI argparse-wiring tests (I6).

Hermetic: no xLights, no LLM, no network. We monkeypatch `cli.run_pipeline` (and the
`XLightsClient` async-context) to CAPTURE the exact kwargs the CLI passes, so a silent
regression in flag→kwarg wiring (the checkpoint matrix especially) fails here.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from xlights_orchestrator import cli
from xlights_orchestrator.pipeline.media import safe_name


# -- harness ------------------------------------------------------------------

class _FakeClient:
    """Async-context stub standing in for XLightsClient (never touches the network)."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _fake_state():
    return SimpleNamespace(
        applied={"placed": [], "skipped": []},
        show_plan=SimpleNamespace(sections=[]),
        instructions=[],
    )


@pytest.fixture
def captured(monkeypatch):
    """Run `cli.main(argv)` with run_pipeline captured; returns the kwargs dict (or None)."""
    box: dict = {}

    async def _fake_run_pipeline(song, **kwargs):
        box["song"] = song
        box.update(kwargs)
        return _fake_state()

    monkeypatch.setattr(cli, "run_pipeline", _fake_run_pipeline)
    monkeypatch.setattr(cli, "XLightsClient", _FakeClient)
    monkeypatch.setattr(cli, "has_llm_key", lambda: True)
    monkeypatch.setattr(cli, "load_env", lambda: None)
    return box


# -- run: defaults + save_as --------------------------------------------------

def test_run_defaults(captured):
    cli.main(["run", "--song", "s.mp3", "--no-browser"])
    assert captured["use_cache"] is True
    assert captured["refine"] is False
    assert captured["max_iterations"] == 3
    assert captured["log_revisions"] is True
    assert captured["timing_tracks"] is True
    assert captured["save_as"] == safe_name("s.mp3")


def test_run_no_save_and_name(captured):
    cli.main(["run", "--song", "s.mp3", "--no-save", "--no-browser"])
    assert captured["save_as"] is None


def test_run_name_override(captured):
    cli.main(["run", "--song", "s.mp3", "--name", "Custom", "--no-browser"])
    assert captured["save_as"] == "Custom"


def test_run_boolean_flags_flip(captured):
    cli.main(["run", "--song", "s.mp3", "--no-cache", "--no-log",
              "--no-timing-tracks", "--max-iterations", "7", "--no-browser"])
    assert captured["use_cache"] is False
    assert captured["log_revisions"] is False
    assert captured["timing_tracks"] is False
    assert captured["max_iterations"] == 7
    assert isinstance(captured["max_iterations"], int)


# -- the checkpoint matrix (the likeliest silent-regression site) -------------

def test_checkpoints_attended_terminal(captured):
    """`--no-browser` (attended, no --auto): interpret/design gates are the terminal reviews;
    no refine → no auto-checkpoint."""
    cli.main(["run", "--song", "s.mp3", "--no-browser"])
    assert captured["interpret_checkpoint"] is cli._interpret_review
    assert captured["design_checkpoint"] is cli._design_review
    assert captured["checkpoint"] is None


def test_checkpoints_auto_both_gates_none(captured):
    cli.main(["run", "--song", "s.mp3", "--auto"])
    assert captured["interpret_checkpoint"] is None
    assert captured["design_checkpoint"] is None
    assert captured["checkpoint"] is None


def test_checkpoints_refine_auto_installs_auto_checkpoint(captured):
    cli.main(["run", "--song", "s.mp3", "--refine", "--auto"])
    assert captured["checkpoint"] is cli._auto_checkpoint
    assert captured["interpret_checkpoint"] is None
    assert captured["design_checkpoint"] is None


def test_checkpoints_refine_alone_no_auto_checkpoint(captured):
    """`--refine` without `--auto` (attended terminal): the auto-checkpoint stays None; the loop
    uses the attended gates."""
    cli.main(["run", "--song", "s.mp3", "--refine", "--no-browser"])
    assert captured["refine"] is True
    assert captured["checkpoint"] is None
    assert captured["interpret_checkpoint"] is cli._interpret_review


# -- guard exits --------------------------------------------------------------

def test_run_missing_llm_key_exits(monkeypatch):
    monkeypatch.setattr(cli, "has_llm_key", lambda: False)
    monkeypatch.setattr(cli, "load_env", lambda: None)
    with pytest.raises(SystemExit) as ei:
        cli.main(["run", "--song", "s.mp3", "--no-browser"])
    assert "No LLM key found" in str(ei.value)


def test_edit_brief_needs_song_or_brief(monkeypatch):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    with pytest.raises(SystemExit) as ei:
        cli.main(["edit-brief"])
    assert "--song or --brief" in str(ei.value)


def test_edit_brief_nonexistent_path_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    missing = tmp_path / "nope.json"
    with pytest.raises(SystemExit) as ei:
        cli.main(["edit-brief", "--brief", str(missing)])
    assert "run `xlo run`" in str(ei.value)


def test_bad_subcommand_argparse_exit_code_2(monkeypatch):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    with pytest.raises(SystemExit) as ei:
        cli.main(["frobnicate"])
    assert ei.value.code == 2


# -- regen: list / no key needed; error translation ---------------------------

def test_regen_list_prints_no_key_needed(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "has_llm_key", lambda: False)   # --list must NOT require a key
    monkeypatch.setattr(cli, "format_sections", lambda song: "0  0-1000ms  wash")
    cli.main(["regen", "--song", "s.mp3", "--list"])
    assert "wash" in capsys.readouterr().out


def test_regen_omitted_section_lists(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "has_llm_key", lambda: False)
    monkeypatch.setattr(cli, "format_sections", lambda song: "SECTIONS-HERE")
    cli.main(["regen", "--song", "s.mp3"])                    # no --section, no --list
    assert "SECTIONS-HERE" in capsys.readouterr().out


def test_regen_index_error_becomes_systemexit(monkeypatch):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "has_llm_key", lambda: True)

    async def _boom(args):
        raise IndexError("section 9 out of range (show has 3 sections)")

    monkeypatch.setattr(cli, "_regen", _boom)
    with pytest.raises(SystemExit) as ei:
        cli.main(["regen", "--song", "s.mp3", "--section", "9"])
    assert "out of range" in str(ei.value)
