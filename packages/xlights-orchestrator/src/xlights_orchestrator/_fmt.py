"""Tiny shared formatting helpers."""

from __future__ import annotations


def mmss(ms: int) -> str:
    """Milliseconds → 'm:ss' (floored, never negative)."""
    s = max(0, int(ms)) // 1000
    return f"{s // 60}:{s % 60:02d}"
