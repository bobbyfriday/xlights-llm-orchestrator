"""CLI argparse-wiring tests (I6). Hermetic: no xLights, no model, no network.

The stage commands' behavior is covered in tests/test_cli_stages.py; this pins the command set
itself — the stages that remain, and the agent-era commands that must stay gone."""

from __future__ import annotations

import pytest

from xlights_orchestrator import cli

STAGES = {"analyze", "groups", "validate-brief", "realize", "apply", "qa", "stills", "finalize",
          "video-plan", "cache-rename", "init-layout"}


def _subcommands() -> set[str]:
    ap = cli._build_parser()
    sub = next(a for a in ap._actions if a.dest == "cmd")
    return set(sub.choices)


def test_the_command_set_is_the_stage_set():
    assert _subcommands() == STAGES


@pytest.mark.parametrize("cmd", ["run", "regen", "report", "ab", "edit-brief", "video-script"])
def test_agent_era_commands_are_gone(monkeypatch, cmd):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    with pytest.raises(SystemExit) as ei:
        cli.main([cmd, "--song", "s.mp3"])
    assert ei.value.code == 2                          # argparse: invalid choice


def test_init_layout_has_no_llm_flag(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    with pytest.raises(SystemExit) as ei:
        cli.main(["init-layout", "--no-llm"])
    assert ei.value.code == 2
    assert "--no-llm" in capsys.readouterr().err       # "unrecognized arguments: --no-llm"


@pytest.mark.parametrize("cmd", sorted(STAGES))
def test_every_command_has_help(cmd, capsys):
    with pytest.raises(SystemExit) as ei:
        cli.main([cmd, "--help"])
    assert ei.value.code == 0 and "usage: xlo " + cmd in capsys.readouterr().out


def test_bad_subcommand_argparse_exit_code_2(monkeypatch):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    with pytest.raises(SystemExit) as ei:
        cli.main(["frobnicate"])
    assert ei.value.code == 2
