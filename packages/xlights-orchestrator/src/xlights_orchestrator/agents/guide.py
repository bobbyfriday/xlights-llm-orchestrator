"""Inject user-maintained xLights guides into the design/generation/critique agents' system
prompts. Single editable source per guide; a missing guide is a clean no-op. Each agent gets the
guides relevant to its job (see the factory wrappers). See [[end-to-end-status]]."""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

# key -> (env override, default path, section title shown to the agent)
_GUIDES: dict[str, tuple[str, str, str]] = {
    "sequencing": ("XLO_SEQUENCING_GUIDE", "xlights-sequencing-guide.md",
                   "SEQUENCING BEST-PRACTICES"),
    "effects": ("XLO_EFFECTS_CATALOG", "xlights-effects-catalog.md",
                "EFFECTS CATALOG (choose effects + looks from here; respect prop affinities & energy bands)"),
    "layering": ("XLO_LAYERING_GUIDE", "xlights-layering-rendering-guide.md",
                 "LAYERING & RENDER-STYLE GUIDE (layers, blending, group-canvas vs per-model)"),
    "scenes": ("XLO_SCENE_COOKBOOK", "xlights-scene-cookbook.md",
               "SCENE COOKBOOK (named multi-prop scene recipes — compose sections from these;"
               " row names are display ARCHETYPES to cast onto the real groups)"),
    "triggers": ("XLO_TRIGGER_COOKBOOK", "xlights-trigger-cookbook.md",
                 "TRIGGER COOKBOOK (curated semantic accents — code-applied, not for the prompt)"),
}
_cache: dict[str, str] = {}                  # keyed by resolved path so tests with distinct files work


def load_guide(key: str) -> str:
    """A guide's text (cached by path); '' if unconfigured/unreadable (best-effort, never raises)."""
    env, default, _ = _GUIDES[key]
    path = os.environ.get(env) or default
    if path in _cache:
        return _cache[path]
    try:
        text = Path(path).read_text()
        log.debug("guide %s loaded from %s (%d chars)", key, path, len(text))
    except Exception as exc:  # noqa: BLE001 — best-effort; no guide is a valid state
        log.debug("guide %s not loaded (%s): %s", key, path, exc)
        text = ""
    _cache[path] = text
    return text


def with_guides(prompt: str, *keys: str) -> str:
    """Append the named guides (each delimited) to a system prompt; missing guides are skipped."""
    out = prompt
    for key in keys:
        g = load_guide(key)
        if g:
            title = _GUIDES[key][2]
            out += f"\n\n## {title} (apply unless the grounded song data says otherwise)\n\n{g}"
    return out


# -- back-compat (the original single-guide API) --
def sequencing_guide() -> str:
    return load_guide("sequencing")


def with_guide(prompt: str) -> str:
    return with_guides(prompt, "sequencing")
