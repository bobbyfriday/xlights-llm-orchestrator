"""Resolve an effect's xLights buffer/render style (`B_CHOICE_BufferStyle`).

Render style is a CREATIVE choice — the Generator picks it per effect (it's injected with the
layering guide). This module only validates that choice and provides a deterministic FALLBACK so an
effect is never left on the unset (sparse group-canvas) default that caused the dark choruses.
"""

from __future__ import annotations

KNOWN_STYLES = {
    "Default", "Per Preview", "Per Model Default", "Per Model Per Preview",
    "Single Line", "Per Model Single Line",
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
