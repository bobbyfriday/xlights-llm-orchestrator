"""Stage 1 (analyze) as one reusable call: audio → a fully enriched SongAnalysis.

Shared by `run_pipeline` and the standalone `xlo analyze` bundle export, so the bundle a
downstream LLM consumer reads is exactly what the show pipeline sees: VAMP/librosa features,
optional stems + per-section instrumentation, Genius lyric text aligned on the vocal stem, and
lyric-marker (or instrumental) section refinement. Every enrichment is best-effort — losses are
recorded via `degradations.note` and never fail the analysis.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from xlights_core.audio import AudioAnalyzer, SongAnalysis

from .. import degradations
from ..lyrics import fetch_lyrics

log = logging.getLogger(__name__)


def analyze_song(song_path: str, *, stems: bool = True, lyrics: bool = True,
                 lyrics_text: str | None = None,
                 analyze: Callable[[str], SongAnalysis] | None = None) -> SongAnalysis:
    """Analyze `song_path` (content-hash cached) and attach timed lyrics / refined sections.

    `analyze` replaces the base feature extraction (a test seam with the simple
    (path)->SongAnalysis shape); enrichment still runs on its result. `lyrics_text` supplies
    the lyric text directly (skips Genius); `lyrics=False` skips lyric alignment entirely. The
    audio cache is intentionally not bypassable here: re-analysis is expensive AND lyric
    alignment is not always reproducible. A cached analysis whose
    segmentation predates a structure.py fix self-heals on load (AudioAnalyzer migrates it in
    place from cached lyrics/beats).
    """
    analyzer = AudioAnalyzer()
    sa = analyze(song_path) if analyze is not None else analyzer.analyze(song_path, stems=stems)
    # Timed lyrics: fetch text, align on the vocal stem (cached). This also flips the
    # synthesizer's `instrumental` flag (it reads sa.lyrics) for vocal songs. Re-attach when the
    # cache predates marker-aware fetching (no headers_fetch flag) so lyric section markers
    # upgrade old caches once.
    _ly = getattr(sa, "lyrics", None) or {}
    if lyrics and (lyrics_text is not None or not _ly.get("lines") or not _ly.get("headers_fetch")):
        try:
            title = artist = ""
            text = lyrics_text
            if text is None:
                _ld = fetch_lyrics(song_path)
                if _ld:
                    text, title, artist = _ld.text, _ld.title or "", _ld.artist or ""
            if text and analyzer.attach_lyrics(sa, song_path, text=text, title=title, artist=artist):
                log.info("timed lyrics attached (%d lines)", len((getattr(sa, "lyrics", None) or {}).get("lines", [])))
        except Exception as exc:  # noqa: BLE001 — lyrics are enrichment
            degradations.note("audio:lyrics", exc, stage="analyze")
    # Instrumental complement: still no timed lines → subdivide long audio sections at
    # musical seams so no single look runs past ~32s (best-effort; never blocks the run).
    if not (getattr(sa, "lyrics", None) or {}).get("lines"):
        try:
            if analyzer.refine_instrumental(sa, song_path):
                log.info("instrumental sections refined (%d segments)", len(getattr(sa, "segments", [])))
        except Exception as exc:  # noqa: BLE001 — refinement is enrichment
            degradations.note("audio:instrumental-refine", exc, stage="analyze")
    # Core-owned outcome observed at the seam: stems requested but the analysis has none →
    # all separation backends failed (core logs per-backend; the run reports the terminal loss).
    if stems and not (getattr(sa, "stems", None) or []):
        degradations.note("audio:stems", "all separation backends failed (no per-section instruments)",
                          stage="analyze")
    return sa
