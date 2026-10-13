"""Shared file I/O for the `xlo` stage commands (claude-driven-orchestration D1/D6).

Every stage is file-in, file-out over the song's flat cache dir. This module owns the file
names, the loaders, and the one error the CLI maps to a non-zero exit naming the missing
prerequisite: `MissingInput` ("missing <file>: run `xlo <stage>` first"). Keeping the contract
here means the CLI, the tests, and the skills all read the same names.

Files (all directly under `<song-slug>--<hash>/`):

    song_analysis.json         xlo analyze     (SongAnalysis; shared by every later stage)
    analysis_digest.md         xlo analyze
    vocab.json                 xlo groups      (+ creative_brief.schema.json)
    layout.json                xlo groups      (show folder + real model names; optional input)
    creative_brief.json        written by Claude / the user (never by a stage)
    validation.json            xlo validate-brief
    instructions.json          xlo realize
    applied.json               xlo apply
    qa.json                    xlo qa
    stills/NN-<label>.png      xlo stills
    video_story.json           written by Claude → video_script.json + .md (xlo video-plan)
"""

from __future__ import annotations

import json
from pathlib import Path

from xlights_core.audio import SongAnalysis

from ..show_plan import EffectInstruction, ShowPlan
from .cache import cache_root, song_key

ANALYSIS_NAME = "song_analysis.json"
BRIEF_NAME = "creative_brief.json"
INSTRUCTIONS_NAME = "instructions.json"
APPLIED_NAME = "applied.json"
LAYOUT_NAME = "layout.json"
STORY_NAME = "video_story.json"
VIDEO_SCRIPT_NAME = "video_script.json"
STILLS_DIR = "stills"

# Which stage produces each prerequisite file — the hint in a MissingInput message. The brief is
# the one input no stage writes: Claude (or the user) authors it, so its hint names the command.
PRODUCER: dict[str, str] = {
    ANALYSIS_NAME: "analyze",
    "vocab.json": "groups",
    "creative_brief.schema.json": "groups",
    LAYOUT_NAME: "groups",
    "validation.json": "validate-brief",
    INSTRUCTIONS_NAME: "realize",
    APPLIED_NAME: "apply",
    "qa.json": "qa",
}
BRIEF_HINT = "write it (the /xlo:design command), then `xlo validate-brief`"
STORY_HINT = "write it (the /xlo:video command)"


class MissingInput(FileNotFoundError):
    """A stage prerequisite file is absent. `str(exc)` is the user-facing message; the CLI exits 2."""

    def __init__(self, path: Path, hint: str | None = None):
        self.path = Path(path)
        name = self.path.name
        if hint is None:
            if name == BRIEF_NAME:
                hint = BRIEF_HINT
            elif name == STORY_NAME:
                hint = STORY_HINT
            else:
                stage = PRODUCER.get(name)
                hint = f"run `xlo {stage}` first" if stage else "it must exist"
        self.hint = hint
        super().__init__(f"missing {name}: {hint}")


def require(path, hint: str | None = None) -> Path:
    """The path, when it exists; else `MissingInput` with the producing stage named."""
    p = Path(path)
    if not p.exists():
        raise MissingInput(p, hint)
    return p


def resolve_song_dir(song: str | None, cache: str | None) -> Path:
    """The song's cache dir from `--cache <dir>` (taken as-is) or `--song <mp3>` (via the content
    hash, like every stage before this change). Neither → ValueError for the CLI to report."""
    if cache:
        return Path(cache).expanduser()
    if song:
        if not Path(song).is_file():
            raise FileNotFoundError(f"song not found: {song}")
        return cache_root() / song_key(song)
    raise ValueError("give --song <mp3> or --cache <dir>")


# ---------------------------------------------------------------- loaders

def load_analysis(song_dir) -> SongAnalysis:
    return SongAnalysis.model_validate_json(require(Path(song_dir) / ANALYSIS_NAME).read_text())


def load_brief_json(song_dir) -> dict:
    """The raw brief dict (the validator checks the raw file so one pass reports everything)."""
    text = require(Path(song_dir) / BRIEF_NAME).read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{BRIEF_NAME} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{BRIEF_NAME} must be a JSON object")
    return data


def load_brief(song_dir) -> ShowPlan:
    """The brief as a `ShowPlan` (the `$schema` key is ignored on read)."""
    return ShowPlan.model_validate(load_brief_json(song_dir))


def load_instructions(song_dir) -> list[EffectInstruction]:
    raw = json.loads(require(Path(song_dir) / INSTRUCTIONS_NAME).read_text())
    return [EffectInstruction.model_validate(x) for x in raw]


def write_instructions(song_dir, instrs: list[EffectInstruction]) -> Path:
    """`instructions.json`: one dump per instruction, indent 1 — the same shape `xlo run` cached."""
    out = Path(song_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / INSTRUCTIONS_NAME
    path.write_text(json.dumps([i.model_dump() for i in instrs], indent=1))
    return path


def load_applied(song_dir) -> dict | None:
    """`applied.json` when present (QA's placement check reads it), else None."""
    p = Path(song_dir) / APPLIED_NAME
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return data if isinstance(data, dict) else None


def write_applied(song_dir, applied: dict) -> Path:
    out = Path(song_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / APPLIED_NAME
    path.write_text(json.dumps(applied, indent=1))
    return path


def load_layout(song_dir) -> dict:
    """`layout.json` (`{show_folder, models}`) from `xlo groups`; `{}` when absent so the offline
    stages degrade (no faces / matrix text / `.fseq` lookup) instead of failing."""
    p = Path(song_dir) / LAYOUT_NAME
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_layout(song_dir, *, show_folder: str | None, models: list[str]) -> Path:
    out = Path(song_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / LAYOUT_NAME
    path.write_text(json.dumps({"show_folder": show_folder or "", "models": list(models)}, indent=1))
    return path


def load_story_json(song_dir) -> dict:
    text = require(Path(song_dir) / STORY_NAME).read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{STORY_NAME} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{STORY_NAME} must be a JSON object")
    return data


# ---------------------------------------------------------------- derived facts

def downbeats_ms(sa) -> list[int]:
    """Downbeat times (bar_position == 1) in ms, for the validator's boundary warnings."""
    return [int(round(float(b.time) * 1000)) for b in (getattr(sa, "beats", None) or [])
            if getattr(b, "bar_position", None) == 1]


def duration_ms(sa) -> int:
    return int(round(float(getattr(sa, "duration_s", 0.0) or 0.0) * 1000))


def song_path_of(song: str | None, sa) -> str:
    """The audio path a stage should name: `--song` when given, else the analysis' own path."""
    return song or str(getattr(sa, "path", "") or "")


def locate_fseq(name: str, show_folder: str | None):
    """The compiled `.fseq` for a saved sequence (sandbox container first, then the show folder)."""
    from .media import resolve_artifact
    return resolve_artifact(f"{name}.fseq", show_folder)


def fseq_series(fseq_path, show_folder: str | None, groups=None):
    """A per-group `FseqSeries` over the `.fseq` (None when the layout files or the [preview]
    extra are missing — the metrics then stay neutral)."""
    if fseq_path is None or not show_folder:
        return None
    try:
        from xlights_core.preview import FseqSeries, group_channel_index
    except ImportError:
        return None
    rgb = Path(show_folder) / "xlights_rgbeffects.xml"
    net = Path(show_folder) / "xlights_networks.xml"
    if not (rgb.exists() and net.exists()):
        return None
    idx = group_channel_index(str(rgb), str(net), groups=list(groups) if groups else None)
    if not idx:
        return None
    return FseqSeries(str(fseq_path), idx)
