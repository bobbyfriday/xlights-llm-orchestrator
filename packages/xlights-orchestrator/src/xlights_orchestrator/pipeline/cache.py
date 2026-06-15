"""Per-song stage cache paths. Resume = cached stage artifacts keyed by song content hash."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def cache_root() -> Path:
    return Path(os.environ.get("XLO_CACHE_DIR", "data")) / "orchestrator"


def song_key(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def cache_path(key: str, stage: str) -> Path:
    return cache_root() / key / f"{stage}.json"
