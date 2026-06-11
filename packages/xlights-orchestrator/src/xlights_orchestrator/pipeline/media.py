"""Song naming + media staging for audio-backed sequences.

xLights is sandboxed and chokes on spaces/inaccessible paths (a bad media path pops a
modal that hangs), so we copy the song into the show folder under a safe, no-spaces name
and attach THAT path. See [[xlights-automation-quirks]].
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

_SAFE = re.compile(r"[^A-Za-z0-9]+")

# The macOS app container is where xLights actually writes/reads sequences (sandbox).
SANDBOX_DATA = Path.home() / "Library/Containers/org.xlights/Data"


def safe_name(song_path: str | Path) -> str:
    """Filename stem → a safe, no-spaces sequence/media name.

    `mad russian christmas.mp3` → `mad_russian_christmas`. Empty/odd → `show`.
    """
    stem = Path(song_path).stem
    name = _SAFE.sub("_", stem).strip("_")
    return name or "show"


def prepare_media(song_path: str | Path, show_folder: str | Path | None) -> Path | None:
    """Copy the song into the show folder under a safe name (preserving extension) so
    xLights can read it. Idempotent (skip if a same-size copy exists). Returns the dest
    path, or None if the source is missing / copy fails / no show folder (caller degrades).
    """
    if not show_folder:
        return None
    src = Path(song_path)
    if not src.is_file():
        log.warning("media: source song not found: %s", src)
        return None
    dest = Path(show_folder) / f"{safe_name(src)}{src.suffix}"
    try:
        if dest.exists() and dest.stat().st_size == src.stat().st_size:
            return dest                      # already staged, identical → reuse
        shutil.copy2(src, dest)
        return dest
    except OSError as exc:
        log.warning("media: could not stage %s → %s: %s", src, dest, exc)
        return None


def resolve_xsq(save_as: str, show_folder: str | Path | None) -> Path | None:
    """Find the saved `.xsq` — the sandbox container Data dir first, then the show folder."""
    for d in (SANDBOX_DATA, Path(show_folder) if show_folder else None):
        if d and (d / f"{save_as}.xsq").exists():
            return d / f"{save_as}.xsq"
    return None


def patch_xsq_media(xsq_path: str | Path, media_path: str | Path, duration_s: float) -> bool:
    """Make a saved Animation `.xsq` a Media sequence OFFLINE — set <sequenceType>Media,
    <mediaFile>, <sequenceDuration> in the <head>. Attaching audio via the live API crashes
    xLights (LoadAudioData modal), so we edit the XML on disk; the human opens it to play.
    Best-effort: returns False (leaving the file intact) on any problem. Idempotent.
    """
    import xml.etree.ElementTree as ET

    xsq_path = Path(xsq_path)
    try:
        tree = ET.parse(xsq_path)
        head = tree.getroot().find("head")
        if head is None:
            log.warning("xsq patch: no <head> in %s", xsq_path)
            return False

        def _set(tag, text):
            el = head.find(tag)
            if el is None:
                el = ET.SubElement(head, tag)
            el.text = str(text)

        _set("sequenceType", "Media")
        _set("mediaFile", str(media_path))
        _set("sequenceDuration", f"{float(duration_s):.3f}")
        tree.write(xsq_path, encoding="UTF-8", xml_declaration=True)
        return True
    except Exception as exc:  # noqa: BLE001 — best-effort; leave the animation .xsq intact
        log.warning("xsq patch failed for %s: %s", xsq_path, exc)
        return False
