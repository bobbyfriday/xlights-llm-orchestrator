"""Visual-critique step for the refine loop: render stills+clips of the current show,
run the multimodal critic, persist a human-readable review bundle, return advisory findings.

Fully graceful — missing `[preview]`/ffmpeg/`.fseq` → returns [] and refinement continues.
The `.fseq` is written by the orchestrator's render+save into the macOS sandbox container
(`~/Library/Containers/org.xlights/Data/`), NOT the show folder (see [[xlights-automation-quirks]]).
"""

from __future__ import annotations

import logging
from pathlib import Path

from .. import degradations, telemetry
from ..agents import visual_critic as vc_mod
from ..models.registry import run_agent
from ..refine import Finding
from .media import SANDBOX_DATA as _SANDBOX, resolve_artifact

log = logging.getLogger(__name__)


def _resolve_fseq(seq_name: str, show_folder: str | None) -> Path | None:
    return resolve_artifact(f"{seq_name}.fseq", show_folder)


def _persist_bundle(root: Path, media: list[tuple], vf, findings: list[Finding]) -> None:
    try:
        root.mkdir(parents=True, exist_ok=True)
        for i, (label, png, mp4) in enumerate(media):
            base = f"s{i}_{label.replace(' ', '_')[:24]}"
            (root / f"{base}.png").write_bytes(png)
            if mp4:
                (root / f"{base}.mp4").write_bytes(mp4)
        (root / "findings.json").write_text(vf.model_dump_json(indent=1))
        lines = ["# Visual review\n", f"**Summary:** {vf.summary}\n"]
        for i, (label, _png, mp4) in enumerate(media):
            lines.append(f"\n## section {i}: {label}\n")
            lines.append(f"![still](s{i}_{label.replace(' ', '_')[:24]}.png)\n")
            if mp4:
                lines.append(f"[clip](s{i}_{label.replace(' ', '_')[:24]}.mp4)\n")
            for f in vf.findings:
                if f.section_index == i:
                    lines.append(f"- **[{f.severity}/{f.aspect}]** {f.detail}\n")
        (root / "review.md").write_text("".join(lines))
    except Exception as exc:  # noqa: BLE001 — persistence is cosmetic (findings still returned)
        log.debug("visual review bundle not persisted: %s", exc)


def make_visual_critique(client, *, save_as: str | None, song_key: str, cache_root: Path,
                         critic=None, max_sections: int = 6, clip_secs: int = 10,
                         enable_video: bool = True, real=None):
    """Build the default visual-critique callable for the refine loop. Returns async fn(state)->[Finding]."""
    counter = {"i": 0}

    async def _vc(st) -> list[Finding]:
        try:
            from xlights_core.preview import PreviewRenderer
        except ImportError:
            return []
        if not save_as:
            return []
        show_folder = None
        try:
            await client.save_sequence(save_as)        # write the current .fseq
            show_folder = await client.get_show_folder()
        except Exception as exc:  # noqa: BLE001 — no fresh .fseq → the critic can't run this iter
            degradations.note("visual:critique", exc, stage="refine")
        fseq = _resolve_fseq(save_as, show_folder)
        rgb = Path(show_folder) / "xlights_rgbeffects.xml" if show_folder else None
        net = Path(show_folder) / "xlights_networks.xml" if show_folder else None
        if not (fseq and rgb and rgb.exists() and net and net.exists()):
            log.info("visual critique: render data/layout not found; skipping")
            return []
        try:
            renderer = PreviewRenderer(fseq, rgb, net)
        except Exception as exc:  # noqa: BLE001 — no offline renderer → the critic can't run
            degradations.note("visual:critique", exc, stage="refine")
            return []

        use_real = real is not None and await real.refresh(client)   # judge the REAL render when possible
        secs = (st.music_brief.sections if st.music_brief else [])[:max_sections]
        media = []
        for sec in secs:
            t = renderer.brightest_frame_ms(sec.start_ms, sec.end_ms)  # offline picks the moment
            png = (real.frame_png(t) if use_real else None) or renderer.render_frame(t)
            clip = None
            if enable_video:
                c_end = min(sec.end_ms, sec.start_ms + clip_secs * 1000)
                clip = (real.clip_mp4(sec.start_ms, c_end) if use_real else None)                     or renderer.render_clip(sec.start_ms, c_end)
            media.append((sec.label, png, clip))
        if not media:
            return []

        agent = critic or vc_mod.visual_critic_agent()
        _vc_res = await run_agent(agent, vc_mod.render_input(media, st.show_plan, st.music_brief),
                                  role="visual-critic", attempts=2)
        telemetry.record("visual_critic", _vc_res)
        vf = _vc_res.output
        findings = vc_mod.to_findings(vf)
        root = cache_root / song_key / "visual_review" / f"iter{counter['i']}"
        counter["i"] += 1
        _persist_bundle(root, media, vf, findings)
        log.info("visual critique: %d findings → %s", len(findings), root)
        return findings

    return _vc


def make_lit_sampler(*, save_as: str | None, show_folder: str | None, real=None):
    """A sync `t_ms -> lit_pixel_count` over the current `.fseq`, for the coverage QA.

    Lazily (re)builds the renderer when the `.fseq` changes on disk; raises if it can't see
    (missing fseq/deps) — `qa.coverage` treats sampling failure as neutral, never gating blind.
    Returns None when there's no sequence name to resolve.
    """
    if not save_as:
        return None
    state: dict = {}

    def sampler(t_ms: int) -> int:
        import io

        import numpy as np
        from PIL import Image

        from xlights_core.preview import PreviewRenderer

        if real is not None:                          # the REAL render, when an export exists
            png = real.frame_png(int(t_ms))
            if png:
                a = np.array(Image.open(io.BytesIO(png)))[:, :, :3]
                return int((a.max(axis=2) > 30).sum())
        fseq = _resolve_fseq(save_as, show_folder)
        if fseq is None:
            raise FileNotFoundError(f"no .fseq for {save_as!r}")
        mtime = fseq.stat().st_mtime
        if state.get("mtime") != mtime:
            rgb = Path(show_folder) / "xlights_rgbeffects.xml" if show_folder else None
            net = Path(show_folder) / "xlights_networks.xml" if show_folder else None
            state["r"] = PreviewRenderer(str(fseq), str(rgb), str(net))
            state["mtime"] = mtime
        png = state["r"].render_frame(int(t_ms))
        a = np.array(Image.open(io.BytesIO(png)))[:, :, :3]
        return int((a.max(axis=2) > 30).sum())

    return sampler


def make_fseq_series_provider(*, save_as: str | None, show_folder: str | None, groups=None):
    """A callable `() -> FseqSeries | None` over the current `.fseq` (I8 Tier 0).

    Lazily (re)builds the per-group series when the `.fseq` changes on disk (mtime-invalidated like
    `make_lit_sampler`); returns None when it can't see (missing fseq/layout/deps) so the metrics
    degrade to neutral rather than gating blind. Reads channel data only — no live client."""
    if not save_as:
        return None
    state: dict = {}

    def provider():
        try:
            from xlights_core.preview import FseqSeries, group_channel_index
        except ImportError:
            return None
        fseq = _resolve_fseq(save_as, show_folder)
        if fseq is None or not show_folder:
            return None
        rgb = Path(show_folder) / "xlights_rgbeffects.xml"
        net = Path(show_folder) / "xlights_networks.xml"
        if not (rgb.exists() and net.exists()):
            return None
        mtime = fseq.stat().st_mtime
        if state.get("mtime") != mtime:
            idx = group_channel_index(str(rgb), str(net), groups=list(groups) if groups else None)
            if not idx:
                return None
            state["series"] = FseqSeries(str(fseq), idx)
            state["mtime"] = mtime
        return state.get("series")

    return provider


def _ffprobe_duration(path) -> float | None:
    import subprocess
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=30)
        return float(out.stdout.strip())
    except Exception as exc:  # noqa: BLE001 — probe failure → caller uses the known duration
        log.debug("ffprobe duration probe failed for %s: %s", path, exc)
        return None


class RealRender:
    """The REAL xLights render, exported via automation (media-attached sequences ONLY — a
    media-less export crashes xLights). Cached by the `.xsq` mtime; serves offset-corrected
    frames/clips via ffmpeg. Everything best-effort: consumers fall back to the offline renderer."""

    def __init__(self, save_as: str | None, duration_s: float):
        self.save_as = save_as
        self.duration_s = duration_s
        self.path: Path | None = None
        self.offset_ms = 0
        self._stamp: float | None = None

    async def refresh(self, client) -> bool:
        if not self.save_as:
            return False
        try:
            seq = await client.get_open_sequence()
            if not (seq.get("media") or "").strip():
                return False                              # GUARDRAIL: never export media-less
            xsq = _SANDBOX / f"{self.save_as}.xsq"
            stamp = xsq.stat().st_mtime if xsq.exists() else None
            if self.path and self.path.exists() and stamp == self._stamp:
                return True                               # current export still valid
            name = f"{self.save_as}_review.mp4"
            await client.export_video_preview(name)
            out = _SANDBOX / name
            if not out.exists():
                return False
            dur = _ffprobe_duration(out)
            self.offset_ms = max(0, int(((dur or self.duration_s) - self.duration_s) * 1000))
            self.path, self._stamp = out, stamp
            log.info("real render exported (%s, lead-in %dms)", name, self.offset_ms)
            return True
        except Exception as exc:  # noqa: BLE001 — best-effort; consumers fall back to offline
            degradations.note("visual:real-render", exc, stage="refine")
            return False

    def _ff(self, args, timeout=60) -> bytes | None:
        import subprocess
        try:
            out = subprocess.run(["ffmpeg", "-loglevel", "error"] + args + ["pipe:1"],
                                 capture_output=True, timeout=timeout)
            return out.stdout or None
        except Exception as exc:  # noqa: BLE001 — frame/clip extraction → caller uses offline
            log.debug("ffmpeg frame/clip extraction failed: %s", exc)
            return None

    def frame_png(self, t_ms: int) -> bytes | None:
        if not (self.path and self.path.exists()):
            return None
        t = (int(t_ms) + self.offset_ms) / 1000
        return self._ff(["-ss", f"{t:.3f}", "-i", str(self.path), "-vframes", "1",
                         "-f", "image2", "-c:v", "png"])

    def clip_mp4(self, start_ms: int, end_ms: int) -> bytes | None:
        if not (self.path and self.path.exists()):
            return None
        s = (int(start_ms) + self.offset_ms) / 1000
        d = max(0.5, (end_ms - start_ms) / 1000)
        return self._ff(["-ss", f"{s:.3f}", "-i", str(self.path), "-t", f"{d:.3f}",
                         "-an", "-c:v", "libx264", "-preset", "veryfast", "-f", "mp4",
                         "-movflags", "frag_keyframe+empty_moov"], timeout=120)
