"""Resolve a song's beats-per-bar (the time-signature numerator).

The QM bar-beat tracker runs at its default 4/4 (no bpb parameter is set), so the per-beat
`bar_position` it stamps is a 4/4 grid regardless of the true meter. `brief=None` is the normal
path: the meter comes from the analysis (`detect_beats_per_bar`) and falls back to 4/4. An
explicit time-signature override is honoured when the object passed as `brief` carries one —
`identity.time_signature` (a legacy `MusicBrief`) or a top-level `time_signature` attribute.
Precedence: time-signature override > detected-from-beats > 4/4.
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


def _time_signature_override(brief) -> str | None:
    """A time-signature string from whatever was passed as `brief`, or None. Tolerates None, a
    legacy `MusicBrief` (`identity.time_signature`), a `ShowPlan` (no such field → None), or any
    object with a top-level `time_signature`."""
    if brief is None:
        return None
    ident = getattr(brief, "identity", None)
    ts = getattr(ident, "time_signature", None) if ident is not None else None
    return ts or getattr(brief, "time_signature", None) or None


def resolve_beats_per_bar(sa, brief=None) -> int:
    """The song's beats-per-bar: time-signature override (if `brief` carries one) → meter detected
    from the analysis → 4/4 default. `brief=None` is the normal, analysis-only path."""
    bpb = parse_time_signature(_time_signature_override(brief))
    if bpb:
        return bpb
    return detect_beats_per_bar(sa) or DEFAULT_BEATS_PER_BAR
