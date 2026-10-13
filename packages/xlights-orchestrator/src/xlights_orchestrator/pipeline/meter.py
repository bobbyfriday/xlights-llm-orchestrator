"""Resolve a song's beats-per-bar (the time-signature numerator).

The QM bar-beat tracker runs at its default 4/4 (no bpb parameter is set), so the per-beat
`bar_position` it stamps is a 4/4 grid regardless of the true meter. The meter comes from the
analysis (`detect_beats_per_bar`) and falls back to 4/4.
"""

from __future__ import annotations

import re

DEFAULT_BEATS_PER_BAR = 4


def parse_time_signature(ts: str | None) -> int | None:
    """Beats-per-bar (the numerator) from a time-signature string like '3/4', '6/8', '5'."""
    if not ts:
        return None
    m = re.match(r"\s*(\d{1,2})", ts)
    if not m:
        return None
    n = int(m.group(1))
    return n if 2 <= n <= 12 else None


def detect_beats_per_bar(sa) -> int | None:
    """Modal bar length from the tracker's `bar_position` labels, when clearly consistent.

    Today the tracker is 4/4-pinned, so this typically returns 4 (or None on a weak signal);
    it becomes meaningful once the analyzer configures the tracker's beats-per-bar (Phase 2).
    """
    pos = [p for b in (getattr(sa, "beats", None) or []) if (p := getattr(b, "bar_position", None))]
    if len(pos) < 8:
        return None
    hi = max(pos)
    if 2 <= hi <= 7 and pos.count(1) >= 2 and pos.count(hi) >= 2:
        return hi
    return None


def resolve_beats_per_bar(sa) -> int:
    """The song's beats-per-bar: the meter detected from the analysis, else the 4/4 default."""
    return detect_beats_per_bar(sa) or DEFAULT_BEATS_PER_BAR
