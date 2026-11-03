"""Resolve an effect's xLights buffer/render style (`B_CHOICE_BufferStyle`).

Render style is a CREATIVE choice made per effect (a cast scene row or a cell recipe can carry one).
This module only validates that choice and provides a deterministic FALLBACK so an
effect is never left on the unset (sparse group-canvas) default that caused the dark choruses.
"""

from __future__ import annotations

KNOWN_STYLES = {
    "Default", "Per Preview", "Per Model Default", "Per Model Per Preview",
    "Single Line", "Per Model Single Line",
    # The rest of xLights' buffer styles as the community corpus uses them (the effect files
    # under .claude/skills/xlo-effects recommend several: Overlay - Scaled on a matrix ring,
    # Horizontal Per Model/Strand on a garland). Unknown spellings still fall back.
    "Overlay - Scaled", "Overlay - Centered",
    "Horizontal Stack", "Vertical Stack", "Horizontal Stack - Scaled", "Vertical Stack - Scaled",
    "Horizontal Per Model", "Vertical Per Model",
    "Horizontal Per Model/Strand", "Vertical Per Model/Strand",
    "Per Model Horizontal Per Strand", "Per Model Vertical Per Strand",
    "As Pixel", "Default Model As A Pixel", "Single Line Model As A Pixel",
    "Layer Star", "Stacked X Horizontally", "Stacked Y Horizontally", "Overlaid X", "Overlaid Z",
    "Per Model Default Deep",
}

# Fallback only — used when the LLM didn't choose. Fill effects render per-model (each prop fills);
# cross-display gestures travel across the real yard; simple fills use the plain canvas.
_SWEEP = {"Shockwave", "Wave", "SingleStrand", "Marquee", "Warp", "Curtain", "Bars", "Fan"}
_SIMPLE = {"On", "Off", "Fill", "Strobe", "VU Meter"}


def fallback_style(effect_type: str) -> str:
    if effect_type in _SWEEP:
        return "Per Preview"
    if effect_type in _SIMPLE:
        return "Default"
    return "Per Model Default"          # fill effects + anything unknown → per-model fill (safe vs dark)


def resolve_buffer_style(render_style: str, effect_type: str) -> str:
    """The LLM's choice if valid, else a sensible fallback — never the unset sparse default."""
    return render_style if render_style in KNOWN_STYLES else fallback_style(effect_type)
