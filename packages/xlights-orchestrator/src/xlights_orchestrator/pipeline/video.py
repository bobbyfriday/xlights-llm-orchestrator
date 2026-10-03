"""`xlo video-script`: write a story-driven storyboard for the centerpiece video matrix.

Reads cached artifacts only — no pipeline stage re-runs, no xLights. One Videographer call per song.
Writes `video_script.json` + `video_script.md` into the song's cache directory.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .. import telemetry
from ..models.registry import run_agent
from ..video_script import (
    VideoScript,
    assign_lyrics,
    constraints_for,
    labels_by_overlap,
    lyric_lines,
    render_markdown,
    resolve_beats,
    split_long_shots,
)
from .cache import cache_root, models_fingerprint, song_key

log = logging.getLogger(__name__)

_SIZE = re.compile(r"^\s*(\d+)\s*[xX×]\s*(\d+)\s*$")


def parse_size(text: str) -> tuple[int, int]:
    m = _SIZE.match(text or "")
    if not m or int(m.group(1)) <= 0 or int(m.group(2)) <= 0:
        raise ValueError(f"--matrix-size must look like 1024x768, got {text!r}")
    return int(m.group(1)), int(m.group(2))


def find_llm_artifact(song_dir: Path, stage: str) -> Path | None:
    """A cached LLM-stage artifact: the current model namespace, else the newest other namespace,
    else the legacy un-namespaced path. Read-only consumer, so any honest copy will do — the
    caller records which one was used."""
    candidates = [song_dir / models_fingerprint() / f"{stage}.json"]
    others = sorted((p for p in song_dir.glob(f"m-*/{stage}.json") if p not in candidates),
                    key=lambda p: p.stat().st_mtime, reverse=True)
    candidates += others + [song_dir / f"{stage}.json"]
    return next((p for p in candidates if p.exists()), None)


def downbeats_ms(analysis: dict) -> list[int]:
    return [int(round(float(b["time"]) * 1000)) for b in analysis.get("beats") or []
            if b.get("bar_position") == 1 and b.get("time") is not None]


def song_title(analysis: dict, song_path: str) -> str:
    ly = analysis.get("lyrics") or {}
    title, artist = (ly.get("title") or "").strip(), (ly.get("artist") or "").strip()
    if title:
        return f"{title} — {artist}" if artist else title
    return Path(song_path).stem


async def run_video_script(song: str, *, matrix_size: str | None, frame_ms: int = 50,
                           max_shot_s: float | None = None, agent=None) -> Path:
    """Generate and write the script; returns the Markdown path. Raises on any refusal, before
    spending a model call and without writing anything."""
    if not matrix_size:
        raise ValueError("--matrix-size is required (e.g. 1024x768); the script will not guess "
                         "the video matrix's resolution")
    width, height = parse_size(matrix_size)
    if not Path(song).exists():
        raise FileNotFoundError(f"song not found: {song}")

    key = song_key(song)
    song_dir = cache_root() / key
    analysis_p = song_dir / "song_analysis.json"
    brief_p = find_llm_artifact(song_dir, "creative_brief")
    desc_p = find_llm_artifact(song_dir, "song_description")
    missing = [n for n, p in (("song_analysis", analysis_p if analysis_p.exists() else None),
                              ("creative_brief (show plan)", brief_p),
                              ("song_description (music brief)", desc_p)) if p is None]
    if missing:
        raise FileNotFoundError(f"no cached {', '.join(missing)} for {song} under {song_dir} — "
                                f"run `xlo run --song` for this song first")
    assert brief_p is not None and desc_p is not None

    analysis = json.loads(analysis_p.read_text())
    brief = json.loads(brief_p.read_text())
    description = json.loads(desc_p.read_text())

    plan = brief.get("sections") or []
    if not plan:
        raise ValueError(f"cached creative brief has no sections: {brief_p}")
    sections = [(int(s["start_ms"]), int(s["end_ms"])) for s in plan]
    energies = [float(s.get("intensity") or 0.0) for s in plan]
    labels = labels_by_overlap(sections, description.get("sections") or [])
    lyrics = lyric_lines((analysis.get("lyrics") or {}).get("lines") or [])
    title = song_title(analysis, song)
    constraints = constraints_for(width, height, frame_ms, sections[-1][1])

    from ..agents.videographer import render_input, videographer_agent
    prompt = render_input(song=title, description=description, brief=brief, sections=sections,
                          labels=labels, energies=energies, lyrics=lyrics)
    agent = agent or videographer_agent()
    if telemetry.current() is None:
        telemetry.start_run()
    result = await run_agent(agent, prompt, role="videographer")
    telemetry.record("videographer", result)
    out = result.output

    shots = resolve_beats(out, sections, frame_ms=frame_ms, labels=labels,
                          energies=energies, lyrics=lyrics)
    shots = split_long_shots(shots, max_shot_s=max_shot_s, downbeats_ms=downbeats_ms(analysis),
                             frame_ms=frame_ms)
    assign_lyrics(shots, lyrics)

    source = ", ".join(str(p.relative_to(song_dir)) for p in (brief_p, desc_p, analysis_p))
    vs = VideoScript(song=title, source=source, logline=out.logline, motifs=out.motifs,
                     constraints=constraints, shots=shots)
    (song_dir / "video_script.json").write_text(vs.model_dump_json(indent=1))
    md = song_dir / "video_script.md"
    md.write_text(render_markdown(vs))

    from .run import _emit_usage_summary
    _emit_usage_summary(key, None)
    return md
