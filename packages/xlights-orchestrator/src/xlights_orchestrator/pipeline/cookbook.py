"""The two hand-editable cookbooks the realization reads: the scene cookbook
(`xlights-scene-cookbook.md`, cast by `pipeline/scenes` and listed by `xlo groups` as the brief's
`scene_id` vocabulary) and the trigger cookbook (`xlights-trigger-cookbook.md`, parsed by
`pipeline/triggers`). Both live at the repo root; a missing file is a clean no-op ('' / [])."""

from __future__ import annotations

import logging
import re
from functools import cache
from pathlib import Path

log = logging.getLogger(__name__)

_FILES = {
    "scenes": "xlights-scene-cookbook.md",
    "triggers": "xlights-trigger-cookbook.md",
}
# packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/cookbook.py → repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_HEADING = re.compile(r"^(#{1,4})\s+(.*)$", re.MULTILINE)


def _guide_path(key: str) -> Path:
    """The cookbook file: the working directory's copy when present (the CLI runs from the repo
    root), else the repo root resolved from this module."""
    name = _FILES[key]
    local = Path(name)
    return local.resolve() if local.is_file() else _REPO_ROOT / name


@cache
def _read(path: Path) -> str:
    try:
        return path.read_text()
    except Exception as exc:  # noqa: BLE001 — best-effort; no cookbook is a valid state
        log.debug("cookbook not loaded (%s): %s", path, exc)
        return ""


def load_guide(key: str) -> str:
    """A cookbook's text ('scenes' | 'triggers'), cached; '' if absent/unreadable (never raises)."""
    return _read(_guide_path(key))


def _cut(text: str, want) -> str:
    """Concatenated sections whose heading title satisfies `want(title)`; each section runs
    from its heading to the next heading of the same-or-higher level. '' when none match.
    Level-1 headings are document titles, never sections — they'd swallow the whole guide."""
    heads = [(m.start(), len(m.group(1)), m.group(2)) for m in _HEADING.finditer(text)]
    out: list[str] = []
    for i, (start, level, title) in enumerate(heads):
        if level == 1 or not want(title):
            continue
        end = len(text)
        for s2, l2, _ in heads[i + 1:]:
            if l2 <= level:
                end = s2
                break
        out.append(re.sub(r"\n+-{3,}\s*$", "", text[start:end].rstrip()))  # drop trailing hr
    return "\n\n".join(out)


def scene_recipe(scene_id: str) -> str:
    """ONLY the named scene's block from the cookbook (heading contains the id, e.g. 'SC-09');
    '' when scene_id is empty or unknown."""
    if not scene_id:
        return ""
    return _cut(load_guide("scenes"), lambda t: scene_id in t)


def scene_ids() -> list[str]:
    """Every `SC-NN` scene id defined in the scene cookbook (sorted, unique) — the source for the
    brief schema's `scene_id` vocabulary. Empty when the cookbook is absent."""
    return sorted(set(re.findall(r"SC-\d+", load_guide("scenes") or "")))
