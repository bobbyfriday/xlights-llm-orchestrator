"""`xlo cache-rename`: retrofit pre-slug bare-hash cache entries to readable `<slug>--<hash>` names.

Two caches, two hashes:
- analyzer (`XLO_CACHE_DIR`): `<sha1-40>.json` + `<sha1-40>/stems`, hash over a version prefix +
  bytes. The JSON records the source `path`, so the slug comes from there; new digest = first 16.
- orchestrator (`cache_root()`): `<sha1-16>/`, hash over raw bytes. No source recorded, so the
  digest is matched against candidate audio files (analysis-recorded paths + `--songs` dirs).

Dry run by default. Unmatched entries are reported and left alone (they still resolve as legacy).
The revision log embeds its own dir path (`review_bundle`) and `song_key`, so it is rewritten too.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from xlights_core import cache_names
from xlights_core.audio.analyzer import default_cache_dir

from .cache import cache_root, content_digest

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX16 = re.compile(r"^[0-9a-f]{16}$")
_AUDIO = ("*.mp3", "*.wav", "*.m4a", "*.flac", "*.ogg")
_REWRITE = ("revision_log.jsonl", "revision_log.md")


@dataclass
class Rename:
    root: Path
    old: str
    new: str | None          # None = no source song found
    source: str | None = None


def _analysis_sources(root: Path) -> dict[str, str]:
    """Analyzer legacy name → the source path its JSON recorded."""
    out = {}
    for f in sorted(root.glob("*.json")):
        if _HEX40.match(f.stem):
            try:
                out[f.stem] = json.loads(f.read_text()).get("path") or ""
            except (OSError, ValueError):
                out[f.stem] = ""
    return out


def plan(song_dirs: list[Path]) -> list[Rename]:
    aroot, oroot = default_cache_dir(), cache_root()
    sources = _analysis_sources(aroot)
    plans = []

    legacy = sorted({p.name.removesuffix(".json") for p in aroot.glob("*")
                     if _HEX40.match(p.name.removesuffix(".json"))}) if aroot.is_dir() else []
    for old in legacy:
        src = sources.get(old)
        plans.append(Rename(aroot, old, cache_names.entry_name(src, old[:16]) if src else None, src))

    # Orchestrator dirs: hash each candidate audio file once, analysis-recorded paths first.
    candidates = [Path(s) for s in sources.values() if s]
    for d in song_dirs:
        for pat in _AUDIO:
            candidates += sorted(d.glob(pat))
    by_digest: dict[str, str] = {}
    for c in dict.fromkeys(candidates):
        if c.is_file():
            by_digest.setdefault(content_digest(str(c)), str(c))
    if oroot.is_dir():
        for d in sorted(p for p in oroot.iterdir() if p.is_dir() and _HEX16.match(p.name)):
            src = by_digest.get(d.name)
            plans.append(Rename(oroot, d.name, cache_names.entry_name(src, d.name) if src else None,
                                src))
    return plans


def apply(r: Rename) -> list[str]:
    """Rename one entry (dir and/or `.json`) and rewrite its revision log. Returns notes."""
    notes = []
    for suffix in ("", ".json"):
        src, dst = r.root / f"{r.old}{suffix}", r.root / f"{r.new}{suffix}"
        if not src.exists():
            continue
        if dst.exists():
            notes.append(f"skipped {src.name}: {dst.name} already exists")
            continue
        src.rename(dst)
    for name in _REWRITE:
        f = r.root / r.new / name
        if f.is_file():
            text = f.read_text()
            if r.old in text:
                f.write_text(text.replace(r.old, r.new))
    return notes


def run(song_dirs: list[Path], *, do_apply: bool) -> str:
    plans = plan(song_dirs)
    if not plans:
        return "nothing to rename — every cache entry already has a readable name"
    lines = []
    for r in plans:
        where = r.root.name
        if r.new is None:
            lines.append(f"  ?? {where}/{r.old}  (no matching song found — pass --songs DIR)")
            continue
        lines.append(f"  {where}/{r.old} → {r.new}")
        if do_apply:
            lines += [f"     {n}" for n in apply(r)]
    todo = sum(r.new is not None for r in plans)
    head = (f"renamed {todo} entr{'y' if todo == 1 else 'ies'}:" if do_apply
            else f"would rename {todo} entr{'y' if todo == 1 else 'ies'} (dry run; --apply to do it):")
    return "\n".join([head, *lines])
