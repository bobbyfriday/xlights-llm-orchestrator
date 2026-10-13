"""Optional lyric-text acquisition via Genius. Online, cached upstream, graceful.

Reads artist/title from the audio file's tags (filename fallback), then fetches the
lyric TEXT (untimed) from Genius. Any miss — no token, no tags, no match, network
error, timeout — returns None and the panel simply runs without the lyric analyst.
Word-level timing (forced alignment) is out of scope (a later enrichment).

Retry asymmetry (I2): this module deliberately keeps ``lyricsgenius(retries=1)`` (Genius'
own internal retry) and is NOT wrapped by ``xlights_core.retry.with_retry`` — doing so
would stack a second retry loop on top of the library's, doubling worst-case wall time on
a persistently-down Genius. The LLM/transport ``with_retry`` seams are separate and do not
touch this path.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from pydantic import BaseModel

log = logging.getLogger(__name__)


class LyricData(BaseModel):
    title: str
    artist: str
    text: str


def _tags(song_path: str) -> tuple[str | None, str | None]:
    """(artist, title) from audio tags, else (None, filename-derived title)."""
    artist = title = None
    try:
        from mutagen import File as MutagenFile

        m = MutagenFile(song_path, easy=True)
        if m:
            artist = (m.get("artist") or [None])[0]
            title = (m.get("title") or [None])[0]
    except Exception as exc:  # noqa: BLE001 — tags are best-effort
        log.debug("tag read failed for %s: %s", song_path, exc)
    if title:
        return artist, title
    # filename fallback: "01 - Some Title.mp3" -> "Some Title". Keep a tag artist even
    # when the title tag is missing — artist-only tags used to skip lyrics entirely.
    stem = Path(song_path).stem
    stem = re.sub(r"^\s*\d+\s*[-_.]\s*", "", stem).strip()
    return artist, (stem or None)


def fetch_lyrics(song_path: str, *, timeout: int = 8) -> LyricData | None:
    token = os.environ.get("GENIUS_ACCESS_TOKEN")
    if not token:
        log.info("no GENIUS_ACCESS_TOKEN; skipping lyrics")
        return None
    artist, title = _tags(song_path)
    if not title:
        log.info("no title for %s; skipping lyrics", song_path)
        return None
    try:
        import lyricsgenius

        genius = lyricsgenius.Genius(
            token, timeout=timeout, retries=1, remove_section_headers=False,
        )  # keep [Verse]/[Chorus] markers — they become timed section boundaries
        song = genius.search_song(title, artist or "")
        if not song or not getattr(song, "lyrics", None):
            log.info("no Genius match for %r / %r", title, artist)
            return None
        return LyricData(title=song.title or title, artist=song.artist or (artist or ""),
                         text=song.lyrics)
    except Exception as exc:  # noqa: BLE001 — lyrics are optional enrichment
        from .degradations import note
        note("audio:lyrics", f"Genius fetch failed for {title!r}: {exc}", stage="analyze")
        return None


def timed_lines(lyrics: dict) -> list[tuple[str, int, int]]:
    """Best-effort (text, start_ms, end_ms) per lyric line from the untyped analysis lyrics dict
    (`SongAnalysis.lyrics`): the digest, the timing tracks and the matrix captions all read it."""
    out: list[tuple[str, int, int]] = []
    if not isinstance(lyrics, dict):
        return out

    def _ms(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        return int(v * 1000) if v < 10000 else int(v)   # seconds vs already-ms heuristic

    lines = lyrics.get("lines") or lyrics.get("synced") or []
    for ln in lines if isinstance(lines, list) else []:
        if not isinstance(ln, dict):
            continue
        text = ln.get("text") or ln.get("line") or ln.get("words")
        start = _ms(ln.get("start", ln.get("start_ms", ln.get("time"))))
        end = _ms(ln.get("end", ln.get("end_ms")))
        if isinstance(text, str) and start is not None:
            out.append((text.strip(), start, end if end is not None else start + 2000))
    return out
