"""Realize named/hex colors as a valid xLights `C_BUTTON_Palette` settings string.

The creative brief chooses colors by name ("warm white", "deep blue"); this turns them into
the same palette-string format mined from the .xsq corpus (8 `C_BUTTON_PaletteN` slots +
`C_CHECKBOX_PaletteN=1` for the active ones). Unknown/empty → None so callers fall back to a
mined palette. Solid colors only (no gradients).
"""

from __future__ import annotations

import re

# Curated common show colors → hex. Extend freely; lookup is case/space/hyphen-insensitive.
NAMED_COLORS: dict[str, str] = {
    "white": "#FFFFFF", "warm white": "#FFF1D0", "cool white": "#F0F8FF",
    "black": "#000000",
    "red": "#FF0000", "crimson": "#DC143C", "scarlet": "#FF2400", "dark red": "#8B0000",
    "orange": "#FF8C00", "amber": "#FFBF00", "gold": "#FFD700", "yellow": "#FFFF00",
    "green": "#00FF00", "dark green": "#006400", "lime": "#BFFF00", "teal": "#008080",
    "mint": "#98FF98", "emerald": "#50C878",
    "cyan": "#00FFFF", "aqua": "#00FFFF", "turquoise": "#40E0D0",
    "blue": "#0000FF", "deep blue": "#00008B", "navy": "#000080", "royal blue": "#4169E1",
    "ice blue": "#AADAFF", "sky blue": "#87CEEB", "light blue": "#ADD8E6",
    "purple": "#800080", "violet": "#8A2BE2", "lavender": "#B57EDC", "indigo": "#4B0082",
    "magenta": "#FF00FF", "pink": "#FF69B4", "hot pink": "#FF1493", "rose": "#FF66CC",
    "silver": "#C0C0C0", "gray": "#808080", "grey": "#808080",
    # common show colors the Director reaches for
    "copper": "#B87333", "bronze": "#CD7F32", "champagne": "#F7E7CE", "peach": "#FFCBA4",
    "midnight blue": "#191970", "sapphire": "#0F52BA", "frost": "#E3F2FD", "snow white": "#FFFAFA",
    "sunburst orange": "#FD5E53", "candy red": "#E0115F", "ruby": "#9B111E", "burgundy": "#800020",
    "forest green": "#228B22", "lime green": "#32CD32", "royal purple": "#7851A9",
}

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_NORM = re.compile(r"[\s_-]+")
_SLOTS = 8


def _resolve(color: str) -> str | None:
    c = color.strip()
    if _HEX.match(c):
        return c.upper()
    key = _NORM.sub(" ", c.lower()).strip()
    return NAMED_COLORS.get(key)


def _luminance(hex_color: str) -> float:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _brighten(hex_color: str, amount: float = 0.65) -> str:
    """Blend a color toward white for a brighter accent flash."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    r, g, b = (round(c + (255 - c) * amount) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def split_palette(colors: list[str]) -> tuple[list[str], list[str]]:
    """Split a section palette into (base, accent) so beats CONTRAST the wash.

    ≥2 colors → base = the calmer/darker colors, accent = the single brightest. 1 color →
    base = it, accent = a brightened variant. Nothing resolvable → ([], []) so callers fall back.
    Returns hex lists (palette_from_colors accepts hex directly).
    """
    hexes: list[str] = []
    for c in colors or []:
        h = _resolve(c)
        if h and h not in hexes:
            hexes.append(h)
    if not hexes:
        return ([], [])
    if len(hexes) == 1:
        return ([hexes[0]], [_brighten(hexes[0])])
    ranked = sorted(hexes, key=_luminance)        # ascending; brightest last
    return (ranked[:-1], [ranked[-1]])


def palette_from_colors(colors: list[str]) -> str | None:
    """Build a `C_BUTTON_Palette` settings string from named/hex colors, or None if none resolve."""
    hexes: list[str] = []
    for c in colors or []:
        h = _resolve(c)
        if h and h not in hexes:
            hexes.append(h)
        if len(hexes) >= _SLOTS:
            break
    if not hexes:
        return None
    parts = [f"C_BUTTON_Palette{i + 1}={hexes[i] if i < len(hexes) else '#000000'}"
             for i in range(_SLOTS)]
    parts += [f"C_CHECKBOX_Palette{i + 1}=1" for i in range(len(hexes))]   # active = the realized colors
    return ",".join(parts)


def expand_palette(colors: list[str], n: int = 5) -> list[str]:
    """Grow a section's resolved colors to ~n hexes with light/dark/hue-shift variants.

    Multi-color effects (Plasma, Spirals, Bars...) need 3+ colors to render as intended; a thin
    2-color brief gets deterministic same-family variants rather than staying monochromatic.
    """
    import colorsys

    bases: list[str] = []
    for c in colors or []:
        h = _resolve(c)
        if h and h not in bases:
            bases.append(h)
    if not bases:
        return []
    out = list(bases[:n])

    def _variant(hex_color: str, dl: float, dh: float) -> str:
        r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
        r2, g2, b2 = colorsys.hls_to_rgb((hh + dh) % 1.0, max(0.08, min(0.95, ll + dl)), ss)
        return f"#{round(r2 * 255):02X}{round(g2 * 255):02X}{round(b2 * 255):02X}"

    tweaks = [(0.22, 0.0), (-0.18, 0.0), (0.0, 0.06), (0.12, -0.05), (-0.10, 0.04)]
    i = 0
    while len(out) < n and i < len(tweaks) * len(bases):
        dl, dh = tweaks[i // len(bases)]
        v = _variant(bases[i % len(bases)], dl, dh)
        if v not in out:
            out.append(v)
        i += 1
    return out[:n]
