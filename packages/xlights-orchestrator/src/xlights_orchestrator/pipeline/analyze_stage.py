"""The analyze stage: cached audio analysis + lyric attach + instrumental subdivision.

The body of `xlo analyze`. Three steps, each usable alone:

  * `analyze_audio(song, stems=)`      — `AudioAnalyzer().analyze` (the analyzer's own cache;
                                          `use_cache=False` recomputes the whole analysis)
  * `enrich_analysis(sa, song, stems=)` — timed lyrics (Genius + aligner, cached), the
                                          instrumental subdivision, the stems degradation note
  * `cache_analysis(key, sa)`           — persist `song_analysis.json` into the song dir

`analyze_song` chains them and then writes the digest — the whole `xlo analyze` stage.
"""

from __future__ import annotations

import logging
from pathlib import Path

from xlights_core.audio import AudioAnalyzer, SongAnalysis

from .. import degradations
from ..lyrics import fetch_lyrics
from .cache import cache_path, cache_root, song_key
from .digest import write_digest

log = logging.getLogger(__name__)


def analyze_audio(song_path: str, *, stems: bool = True, use_cache: bool = True) -> SongAnalysis:
    """The audio analysis, requesting stems (per-section instrument signal). The analyzer's cache
    is keyed by content hash and self-heals a stale segmentation on load, so `use_cache=True` is
    the normal path; `False` recomputes everything (including stem separation)."""
    return AudioAnalyzer().analyze(song_path, stems=stems, use_cache=use_cache)


def enrich_analysis(sa: SongAnalysis, song_path: str, *, stems: bool = True) -> SongAnalysis:
    """Timed lyrics as part of the INITIAL analysis (fetch text, align on the vocal stem; cached),
    re-attached when the cache predates marker-aware fetching (no `headers_fetch` flag) so lyric
    section markers upgrade old caches once. Still no timed lines → subdivide long audio sections
    at musical seams so no single look runs past ~32 s. Both best-effort; never block the run.
    Also notes the terminal stems loss (stems requested, none attached) as a degradation."""
    _ly = getattr(sa, "lyrics", None) or {}
    if not _ly.get("lines") or not _ly.get("headers_fetch"):
        try:
            _ld = fetch_lyrics(song_path)
            if _ld and _ld.text:
                if AudioAnalyzer().attach_lyrics(sa, song_path, text=_ld.text,
                                                 title=_ld.title or "", artist=_ld.artist or ""):
                    _lines = (getattr(sa, "lyrics", None) or {}).get("lines", [])
                    log.info("timed lyrics attached (%d lines)", len(_lines))
        except Exception as exc:  # noqa: BLE001 — lyrics are enrichment
            degradations.note("audio:lyrics", exc, stage="analyze")
    if not (getattr(sa, "lyrics", None) or {}).get("lines"):
        try:
            if AudioAnalyzer().refine_instrumental(sa, song_path):
                log.info("instrumental sections refined (%d segments)", len(sa.segments))
        except Exception as exc:  # noqa: BLE001 — refinement is enrichment
            degradations.note("audio:instrumental-refine", exc, stage="analyze")
    # Core-owned outcome observed at the seam: stems requested but the analysis has none →
    # all separation backends failed (core logs per-backend; the run reports the terminal loss).
    if stems and not (getattr(sa, "stems", None) or []):
        degradations.note("audio:stems", "all separation backends failed (no per-section instruments)",
                          stage="analyze")
    return sa


def cache_analysis(key: str, sa: SongAnalysis) -> Path | None:
    """Persist the analysis into the song dir so later stages rehydrate without re-analyzing.
    Best-effort (cosmetic): returns the path, or None when the write failed."""
    try:
        sa_cache = cache_path(key, "song_analysis")
        sa_cache.parent.mkdir(parents=True, exist_ok=True)
        sa_cache.write_text(sa.model_dump_json())
        return sa_cache
    except Exception as exc:  # noqa: BLE001 — caching is best-effort (cosmetic)
        log.debug("song_analysis cache write skipped: %s", exc)
        return None


def analyze_song(song_path: str, *, stems: bool = True, use_cache: bool = True
                 ) -> tuple[Path, SongAnalysis, Path]:
    """The `xlo analyze` stage over an audio file: analysis → enrichment → `song_analysis.json`
    + `analysis_digest.md`. Returns `(song_dir, analysis, digest_path)`."""
    key = song_key(song_path)
    sa = enrich_analysis(analyze_audio(song_path, stems=stems, use_cache=use_cache),
                         song_path, stems=stems)
    song_dir = cache_root() / key
    cache_analysis(key, sa)
    return song_dir, sa, write_digest(song_dir, sa)
