"""Parsing helpers for xLights settings strings and value curves.

A settings string is a CSV of ``KEY=VALUE`` (values may contain ``=`` — e.g. value
curves — but never ``,``, verified across the corpus). A value-curve value is itself a
``|``-delimited mini-DSL: ``Active=TRUE|Id=...|Type=Ramp|Min=..|Max=..|P1=..|RV=..|``.
"""

from __future__ import annotations

from .constants import is_timing_track_curve_type


def parse_settings(s: str) -> list[tuple[str, str]]:
    """Parse a settings string into ordered (key, value) pairs. Empty -> []."""
    s = s.strip()
    if not s:
        return []
    pairs: list[tuple[str, str]] = []
    for seg in s.split(","):
        if "=" not in seg:
            # Empty/dangling segment (e.g. trailing comma); preserve as keyless skip.
            continue
        k, v = seg.split("=", 1)
        pairs.append((k, v))
    return pairs


def serialize_settings(pairs: list[tuple[str, str]]) -> str:
    """Inverse of parse_settings for a given ordering."""
    return ",".join(f"{k}={v}" for k, v in pairs)


def parse_value_curve(value: str) -> dict[str, str]:
    """Parse a value-curve value (``Active=..|Type=..|...``) into a field map."""
    fields: dict[str, str] = {}
    for part in value.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v
    return fields


def classify_value_curve(value: str) -> str:
    """Classify a value-curve value: 'parametric' | 'custom' | 'timing-track'."""
    fields = parse_value_curve(value)
    ctype = fields.get("Type", "")
    if is_timing_track_curve_type(ctype):
        return "timing-track"
    if ctype.strip().lower() == "custom":
        return "custom"
    return "parametric"


def value_curve_is_active(value: str) -> bool:
    return parse_value_curve(value).get("Active", "FALSE").strip().upper() == "TRUE"
