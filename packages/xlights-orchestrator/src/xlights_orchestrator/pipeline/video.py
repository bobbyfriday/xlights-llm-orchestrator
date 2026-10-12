"""`xlo video-script`: write a story-driven storyboard for the centerpiece video matrix.

Reads cached artifacts only — no pipeline stage re-runs, no xLights. The MEDIA PLAN (which sections
are filmed by Veo and which are procedural) is decided first, by code, from cached structure and the
clip budget; the Videographer then writes one beat per section FOR its medium (one LLM call).
Writes `video_script.json` + `video_script.md` + `media_plan.json` into the song's cache directory.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .. import telemetry, veo_ledger
from ..media_plan import MediaBudget, apply_media, build_handoff, featured_hits, plan as plan_media, summary
from ..models.registry import run_agent, veo_config
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
                           max_shot_s: float | None = None, veo_clips: int | None = None,
                           pinned: list[int] | None = None, agent=None, model=None) -> Path:
    """Generate and write the script + media plan; returns the Markdown path. Raises on any refusal,
    before spending a model call and without writing anything.

    `veo_clips` is the CAMPAIGN clip budget the story may assume (default: one day's quota from
    config; 0 ⇒ all procedural). `pinned` sections are filmed first. `max_shot_s` overrides the
    filmed clip length (procedural shots are never split). `agent` injects a ready agent (tests);
    `model` substitutes the model while keeping the role's media-lint validator."""
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
    missing = [n for n, p in (("creative_brief (show plan)", brief_p),
                              ("song_description (music brief)", desc_p)) if p is None]
    if missing:
        raise FileNotFoundError(f"no cached {', '.join(missing)} for {song} under {song_dir} — "
                                f"run `xlo run --song` for this song first")
    assert brief_p is not None and desc_p is not None

    if not analysis_p.exists():
        # Older caches predate the persisted analysis. Re-analyze the audio offline (no xLights,
        # no LLM) and persist it — the same fallback `xlo regen` uses (regen.py).
        log.info("no cached song_analysis for %s — analyzing the audio (one-time)", song)
        from xlights_core.audio import AudioAnalyzer
        analysis_p.write_text(AudioAnalyzer().analyze(song).model_dump_json())
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

    # The media plan: code, before the model, from structure + budget + today's ledger.
    veo = veo_config()
    budget = MediaBudget(campaign_clips=int(veo["daily_clips"]) if veo_clips is None else int(veo_clips),
                         clip_s=float(veo["clip_s"]), max_stretch=float(veo["max_stretch"]),
                         pinned=list(pinned or []))
    if budget.campaign_clips < 0:
        raise ValueError(f"--veo-clips must be >= 0, got {budget.campaign_clips}")
    remaining = veo_ledger.remaining_today(int(veo["daily_clips"]), str(veo["quota_reset_tz"]))
    media = plan_media(sections, labels, energies,
                       featured_hits(description.get("featured_lines") or [], lyrics, sections),
                       budget, remaining, per_second_usd=veo.get("per_second_usd"))

    from ..agents.videographer import render_input, videographer_agent
    prompt = render_input(song=title, description=description, brief=brief, sections=sections,
                          labels=labels, energies=energies, lyrics=lyrics, plan=media)
    agent = agent or videographer_agent(media, model=model)
    if telemetry.current() is None:
        telemetry.start_run()
    result = await run_agent(agent, prompt, role="videographer")
    telemetry.record("videographer", result)
    out = result.output

    shots = resolve_beats(out, sections, frame_ms=frame_ms, labels=labels,
                          energies=energies, lyrics=lyrics)
    apply_media(shots, media)
    shots = split_long_shots(shots, max_shot_s=max_shot_s or budget.effective_clip_s,
                             downbeats_ms=downbeats_ms(analysis), frame_ms=frame_ms)
    assign_lyrics(shots, lyrics)
    palette = brief.get("palette") or {}
    media.handoff = build_handoff(shots, list(palette.get("colors") or []) if isinstance(palette, dict)
                                  else [], constraints)

    source = ", ".join(str(p.relative_to(song_dir)) for p in (brief_p, desc_p, analysis_p))
    vs = VideoScript(song=title, source=source, logline=out.logline, motifs=out.motifs,
                     constraints=constraints, shots=shots, media=summary(media))
    (song_dir / "video_script.json").write_text(vs.model_dump_json(indent=1))
    (song_dir / "media_plan.json").write_text(media.model_dump_json(indent=1))
    md = song_dir / "video_script.md"
    md.write_text(render_markdown(vs))

    from .run import _emit_usage_summary
    _emit_usage_summary(key, None)
    return md
