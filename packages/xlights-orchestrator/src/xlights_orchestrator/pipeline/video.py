"""Small helpers for `xlo video-plan`: the matrix-size flag and the song title the script carries."""

from __future__ import annotations

import re
from pathlib import Path

_SIZE = re.compile(r"^\s*(\d+)\s*[xX×]\s*(\d+)\s*$")


def parse_size(text: str) -> tuple[int, int]:
    m = _SIZE.match(text or "")
    if not m or int(m.group(1)) <= 0 or int(m.group(2)) <= 0:
        raise ValueError(f"--matrix-size must look like 1024x768, got {text!r}")
    return int(m.group(1)), int(m.group(2))


def song_title(analysis: dict, song_path: str) -> str:
    ly = analysis.get("lyrics") or {}
    title, artist = (ly.get("title") or "").strip(), (ly.get("artist") or "").strip()
    if title:
        return f"{title} — {artist}" if artist else title
    return Path(song_path).stem
