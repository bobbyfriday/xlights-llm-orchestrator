"""AudioAnalyzer: path -> SongAnalysis, with content-hash caching.

Plugins are required: the analyzer checks them up front and fails clearly if missing.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from . import fusion
from .extractors import vamp_host
from .schema import ANALYZER_VERSION, SongAnalysis

DEFAULT_CACHE_DIR = Path(os.environ.get("XLO_CACHE_DIR", "data/analyses"))


def _encode_mp3(path: Path, y, sr: int) -> bool:
    """Pipe mono float32 PCM through ffmpeg → mp3. Returns True on success."""
    import subprocess

    import numpy as np

    data = np.asarray(y, dtype=np.float32).tobytes()
    cmd = ["ffmpeg", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
           "-codec:a", "libmp3lame", "-q:a", "4", str(path)]
    proc = subprocess.run(cmd, input=data, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.returncode == 0 and path.exists()


def _stems_need_refresh(analysis: SongAnalysis) -> bool:
    """Re-separate if stems are missing, or the cached set doesn't cover the configured model."""
    if analysis.stems is None:
        return True
    from .extractors.stems import SIX_STEM, stems_model

    if "6s" in stems_model():
        have = {s.stem for s in analysis.stems}
        return not SIX_STEM.issubset(have)     # 6-stem model but cache lacks guitar/piano
    return False


def _content_key(path: str) -> str:
    h = hashlib.sha1()
    h.update(f"v{ANALYZER_VERSION}:".encode())
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class AudioAnalyzer:
    def __init__(self, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> None:
        self.cache_dir = Path(cache_dir)

    def analyze(self, path: str, *, use_cache: bool = True, stems: bool = False) -> SongAnalysis:
        vamp_host.check_required_plugins()  # fail fast if a required plugin is missing
        stems = stems or os.environ.get("XLO_STEMS") == "1"

        key = _content_key(path)
        cache_file = self.cache_dir / f"{key}.json"
        if use_cache and cache_file.exists():
            analysis = SongAnalysis.model_validate_json(cache_file.read_text())
            # Augment-and-resave: re-run ONLY the (expensive) separation step when the cached
            # stems are missing OR don't match the configured model (e.g. a 4-stem cache under
            # the 6-stem model), then rewrite — auto-upgrades without recomputing the analysis.
            if stems and _stems_need_refresh(analysis):
                self._attach_stems(analysis, path, key)
                cache_file.write_text(analysis.model_dump_json())
            return analysis

        y, sr = vamp_host.load_audio(path)
        analysis = fusion.build(str(path), y, sr)
        if stems:
            self._attach_stems(analysis, path, key)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(analysis.model_dump_json())
        return analysis

    def attach_lyrics(self, analysis: SongAnalysis, path: str, *, text: str,
                      title: str = "", artist: str = "") -> bool:
        """Align lyric TEXT against the persisted vocal stem → timed lyrics on the analysis,
        re-saving the cache (augment-and-resave, like stems). Graceful: False on any failure."""
        from .lyrics_align import align_lyrics
        key = _content_key(path)
        stem = next((self.cache_dir / key / "stems" / f"vocals.{ext}"
                     for ext in ("wav", "mp3")
                     if (self.cache_dir / key / "stems" / f"vocals.{ext}").exists()), None)
        if stem is None:
            return False
        aligned = align_lyrics(str(stem), text)
        if not aligned:
            return False
        # headers_fetch: this attach saw marker-aware text — pre-change caches (headers
        # stripped at fetch) re-attach once and upgrade; marker-less songs never re-align again.
        analysis.lyrics = {"title": title, "artist": artist, "text": text,
                           "headers_fetch": True, **aligned}
        from .structure import refine_segments_with_lyrics
        if refine_segments_with_lyrics(analysis):      # lyric markers → the real structure
            self._refresh_section_instrumentation(analysis, key)
        try:
            (self.cache_dir / f"{key}.json").write_text(analysis.model_dump_json())
        except Exception:  # noqa: BLE001 — cache write is best-effort
            pass
        return True

    def _refresh_section_instrumentation(self, analysis: SongAnalysis, key: str) -> None:
        """Recompute per-section instrument prevalence over the REFINED segments from the
        persisted stems (best-effort — stale coarse windows still time-overlap-match if absent)."""
        try:
            import librosa
            from .extractors import stems as stems_ext
            separated = {}
            for f in sorted((self.cache_dir / key / "stems").glob("*.*")):
                if f.suffix in (".wav", ".mp3"):
                    y, _ = librosa.load(str(f), sr=analysis.sample_rate, mono=True)
                    separated[f.stem] = y
            if separated:
                analysis.section_instrumentation = stems_ext.section_instrumentation(
                    separated, analysis.sample_rate, analysis.segments)
        except Exception:  # noqa: BLE001 — enrichment only; overlap-matching covers the gap
            pass

    def _attach_stems(self, analysis: SongAnalysis, path: str, key: str) -> None:
        """Separate, persist inspectable stem wavs, attach features + per-section prevalence.

        Graceful: if separation is unavailable, leaves analysis.stems as None."""
        from .extractors import stems as stems_ext

        separated = stems_ext.separate(path, analysis.sample_rate)
        if not separated:
            return
        analysis.stems = stems_ext.stem_features(separated, analysis.sample_rate)
        analysis.section_instrumentation = stems_ext.section_instrumentation(
            separated, analysis.sample_rate, analysis.segments
        )
        self._persist_stems(separated, analysis.sample_rate, key)

    def _persist_stems(self, separated: dict, sr: int, key: str) -> None:
        """Write each stem as an inspectable mp3 (ffmpeg) under the cache dir, wav fallback
        when ffmpeg is absent. Best-effort — never fails the analysis."""
        import logging
        import shutil

        log = logging.getLogger(__name__)
        stem_dir = self.cache_dir / key / "stems"
        try:
            stem_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("could not create stem dir: %s", exc)
            return
        have_ffmpeg = shutil.which("ffmpeg") is not None
        for name, y in separated.items():
            try:
                if have_ffmpeg and _encode_mp3(stem_dir / f"{name}.mp3", y, sr):
                    continue
                import soundfile as sf  # wav fallback (no ffmpeg)
                sf.write(str(stem_dir / f"{name}.wav"), y, sr)
            except Exception as exc:  # noqa: BLE001 — persistence is non-essential
                log.warning("could not persist stem %s: %s", name, exc)
