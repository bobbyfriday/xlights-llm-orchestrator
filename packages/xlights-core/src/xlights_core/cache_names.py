"""Human-readable cache entry names: ``<song-slug>--<digest>``.

The digest (a content hash) is the identity; the slug is decoration so a person can find a song's
cache in Finder. Resolution matches on the digest suffix, so renamed or duplicated MP3s still share
one entry, and a pre-slug bare-digest entry keeps resolving (no cache goes cold). An entry is
either a directory or a ``<name>.json`` file (the analyzer keeps both side by side).
"""

from __future__ import annotations

import re
from pathlib import Path

SEP = "--"
_TRACK_NO = re.compile(r"^\d+\s*[-._ ]\s*")   # "12 - Carmina Burana" → "Carmina Burana"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(source: str | Path, *, max_len: int = 48) -> str:
    """``mp3/04 - Carol Of The Bells.mp3`` → ``carol-of-the-bells``. Never empty."""
    stem = _TRACK_NO.sub("", Path(source).stem.strip())
    slug = _NON_ALNUM.sub("-", stem.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "song"


def entry_name(source: str | Path, digest: str) -> str:
    return f"{slugify(source)}{SEP}{digest}"


def digest_of(name: str) -> str:
    """The digest part of an entry name (slugged or bare), ``.json`` suffix tolerated."""
    name = name.removesuffix(".json")
    return name.rsplit(SEP, 1)[-1]


def find_existing(root: Path, digest: str, *, legacy: tuple[str, ...] = ()) -> str | None:
    """The name of an existing entry for ``digest`` under ``root``: a slugged ``*--<digest>``
    entry first, else one of the ``legacy`` bare names. None when nothing is cached yet."""
    if not root.is_dir():
        return None
    names = {p.name.removesuffix(".json") for p in root.glob(f"*{SEP}{digest}*")}
    slugged = sorted(n for n in names if n.endswith(f"{SEP}{digest}"))
    if slugged:
        return slugged[0]
    return next((n for n in legacy if (root / n).exists() or (root / f"{n}.json").exists()), None)


def resolve(root: Path, source: str | Path, digest: str, *, legacy: tuple[str, ...] = ()) -> str:
    """The entry name to use for ``source``: whatever already exists for its digest, else a fresh
    ``<slug>--<digest>``."""
    return find_existing(root, digest, legacy=legacy) or entry_name(source, digest)
