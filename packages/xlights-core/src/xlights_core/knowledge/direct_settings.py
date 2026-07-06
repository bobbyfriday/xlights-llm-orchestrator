"""Code-owned settings templates for **asset-bound** effect types (F-B).

The mined preset catalog guarantees "valid by construction" because every settings string was
observed in a community `.xsq`. That guarantee cannot extend to effects whose settings reference
things *outside* the string — image/video paths, face definitions, timing-track names on someone
else's disk. `DIRECT_TYPES` is the small allowlist of such types this module can build settings
for **from scratch in code**: a template with a fixed key set, varying only documented knobs, whose
external references (when any) are bound only to resources the caller proves exist, and whose output
round-trips through the settings parser.

The output is validated live via `editing.validate_direct` (a `-m live` scratch-sequence probe)
once per template per xLights upgrade; xLights accepting the string (`worked=true`) and rendering it
is the runtime half of the "valid by construction" contract that mining gives the catalog for free.

Deliberately OUT of `DIRECT_TYPES`: Pictures, Video, Shader, DMX. Adding a type here is an explicit
OpenSpec change, not a config tweak — each new type needs its own probe + live validation.
"""
from __future__ import annotations

from .settings import parse_settings, serialize_settings

# The allowlist. Text is buildable today; Faces is a skeleton until F-D lands its probe.
DIRECT_TYPES = frozenset({"Text", "Faces"})

# xLights Text scroll directions accepted by `E_CHOICE_Text_Dir` (v1 subset).
_TEXT_DIRS = frozenset({"none", "left", "right", "up", "down"})


def _sanitize_glyph_text(text: str) -> str:
    """Pin the comma/equals decision: REJECT (do not silently mangle). A settings string is
    comma-delimited with `key=value` pairs, so a literal ',' or '=' in the glyph text would
    corrupt the parse. v1 forbids them explicitly; F-C (matrix text) can revisit escaping when it
    authors real lyric text."""
    if "," in text or "=" in text:
        raise ValueError("Text glyphs may not contain ',' or '=' (they break settings parsing)")
    return text


def build_text_settings(
    text: str,
    *,
    movement: str = "none",
    font_size: int = 12,
    bold: bool = True,
    speed: int = 10,
    center: bool = True,
) -> str:
    """Build a Text effect settings string from scratch (the F-B "corpus of one" template).

    Varies only the documented knobs: the glyph text, scroll ``movement`` (one of ``_TEXT_DIRS``),
    ``font_size``/``bold`` (folded into the font descriptor), scroll ``speed``, and ``center``.
    Everything else is fixed. Raises ``ValueError`` on an unknown movement, a non-positive font
    size, or glyph text containing ',' / '='. The result round-trips through ``parse_settings``.
    """
    if movement not in _TEXT_DIRS:
        raise ValueError(f"unknown Text movement {movement!r} (want one of {sorted(_TEXT_DIRS)})")
    if font_size <= 0:
        raise ValueError(f"font_size must be positive, got {font_size}")
    glyphs = _sanitize_glyph_text(text)
    font = f"Arial {font_size}" + (" bold" if bold else "")
    pairs = [
        ("E_TEXTCTRL_Text", glyphs),
        ("E_CHOICE_Text_Dir", movement),
        ("E_CHECKBOX_TextToCenter", "1" if center else "0"),
        ("E_SLIDER_Text_Speed", str(int(speed))),
        ("E_FONTPICKER_Text_Font", font),
    ]
    settings = serialize_settings(pairs)
    # ring-1 validation: the string must survive a parse/serialize round-trip unchanged.
    if serialize_settings(parse_settings(settings)) != settings:
        raise ValueError(f"built Text settings do not round-trip: {settings!r}")
    return settings


def build_faces_settings(
    *,
    timing_track: str,
    face_definition: str,
    eyes: str = "Auto",
    outline: bool = True,
) -> str:
    """Skeleton for the Faces template — raises until F-D (lyric-driven faces) lands its probe.

    Both external references are REQUIRED and are never defaulted: a Faces effect binds to a
    timing track (phoneme/word events) and a face definition (mouth/eye picture set), both of which
    must be resources the pipeline itself created and verified. F-D will freeze this template from a
    live probe and bind these references to created resources; until then, building one is an error."""
    raise NotImplementedError(
        "build_faces_settings is a skeleton until F-D (lyric-driven Faces) lands its live probe; "
        f"it will require an existing timing_track ({timing_track!r}) and face_definition "
        f"({face_definition!r}), eyes={eyes!r}, outline={outline!r}."
    )
