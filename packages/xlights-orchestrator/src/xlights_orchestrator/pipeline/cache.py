"""Per-song stage cache paths. Resume = cached stage artifacts keyed by song content hash, in a
readable `<song-slug>--<hash>` dir (see `xlights_core.cache_names`).

The layout is FLAT and provider-independent — every stage artifact sits directly in the song dir:

    data/analyses/orchestrator/<song-slug>--<hash>/
      song_analysis.json        (deterministic audio analysis; shared by every stage)
      analysis_digest.md
      vocab.json                (targetable groups, placeable types, scene ids, stems, colors)
      creative_brief.json       (+ creative_brief.schema.json)
      validation.json
      instructions.json
      applied.json
      qa.json
      stills/<section>.png
      video_story.json          → video_script.json + .md

There is no model-routing namespace. Older caches carry `m-xxxxxxxx/` subdirs from the
former per-routing namespace; those are simply never read (the shared `song_analysis.json` and
targetable-groups probe at the song root are reused as before).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from xlights_core import cache_names


def cache_root() -> Path:
    return Path(os.environ.get("XLO_CACHE_DIR", "data")) / "orchestrator"


def content_digest(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def song_key(path: str) -> str:
    """The song's cache dir name under `cache_root()`: `<song-slug>--<digest>`. The digest is the
    identity (renamed/duplicate MP3s share one dir); a pre-slug bare-digest dir keeps resolving."""
    digest = content_digest(path)
    return cache_names.resolve(cache_root(), path, digest, legacy=(digest,))


def cache_path(key: str, stage: str) -> Path:
    """Path for a per-song stage artifact: the flat `<root>/<key>/<stage>.json`."""
    return cache_root() / key / f"{stage}.json"
