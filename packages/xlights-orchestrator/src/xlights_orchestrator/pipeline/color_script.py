"""Show-level color script (Phase 3): a deterministic plan post-pass giving the whole show one
palette thread instead of independent per-section color choices.

Three deterministic moves, no LLM call, run right after the Director produces the plan and after any
section redesign:
- ANCHOR: the most frequent resolvable color across section palettes becomes a persistent thread —
  injected into any section missing it.
- CHORUS SIGNATURE: the chorus label's sections share one signature pair (their two most hue-distant
  colors), reused VERBATIM across every occurrence so the choruses rhyme in color too.
- BRIDGE CONTRAST: the lowest-recurrence mid-song section (the bridge heuristic) leads with the
  complement of the anchor, so the bridge reads as a deliberate departure.

Idempotent: re-running injects nothing new once the anchor/signature are already present.
"""

from __future__ import annotations

from collections import Counter

from xlights_core.knowledge.colors import (
    _chromatic_hues,
    _hue_dist,
    _resolve,
    ensure_contrast,
)


def _resolvable(colors) -> list[str]:
    return [c for c in (colors or []) if _resolve(c)]


def _most_frequent_color(sections) -> str | None:
    """The most common resolvable color across section palettes (by resolved hex, first name wins)."""
    counts: Counter[str] = Counter()
    name_for: dict[str, str] = {}
    for sec in sections:
        seen: set[str] = set()
        for c in getattr(sec, "palette", None) or []:
            hx = _resolve(c)
            if hx and hx not in seen:              # count each color once per section
                seen.add(hx)
                counts[hx] += 1
                name_for.setdefault(hx, c)
    if not counts:
        return None
    top_hex, _ = counts.most_common(1)[0]
    return name_for[top_hex]


def _signature_pair(sections, indices) -> list[str]:
    """The two most hue-distant colors across the chorus sections' palettes — the shared signature."""
    pool: list[str] = []
    for si in indices:
        if 0 <= si < len(sections):
            for c in getattr(sections[si], "palette", None) or []:
                if c not in pool:
                    pool.append(c)
    chrom = _chromatic_hues(pool)
    if len(chrom) >= 2:
        a, b = max(((x, y) for i, x in enumerate(chrom) for y in chrom[i + 1:]),
                   key=lambda p: _hue_dist(p[0][1], p[1][1]))
        # map the chosen hexes back to the original names where possible (stable, human-readable)
        by_hex = {}
        for c in pool:
            hx = _resolve(c)
            if hx:
                by_hex.setdefault(hx, c)
        return [by_hex.get(a[0], a[0]), by_hex.get(b[0], b[0])]
    return _resolvable(pool)[:2]


def _bridge_index(sections, repetition_map) -> int | None:
    """The bridge heuristic: the lowest-recurrence section in the MIDDLE third of the show. A section
    whose label recurs a lot is a chorus/verse; a near-unique mid-song section is the bridge."""
    n = len(sections)
    if n < 3:
        return None
    recurrence = {}
    for indices in (repetition_map or {}).values():
        for si in indices:
            recurrence[si] = max(recurrence.get(si, 0), len(indices))
    lo, hi = n // 3, 2 * n // 3
    mid = list(range(lo, max(lo + 1, hi + 1)))
    return min(mid, key=lambda si: recurrence.get(si, 1))


def _prepend(colors, color) -> list[str]:
    out = [c for c in (colors or []) if c != color]
    return [color] + out


def apply_color_script(plan, repetition_map=None):
    """Rewrite section palettes in place per the color script; returns the plan. No-op-safe on an
    empty plan or when no color resolves."""
    sections = list(getattr(plan, "sections", None) or [])
    if not sections:
        return plan
    anchor = _most_frequent_color(sections)
    if anchor is not None:
        for sec in sections:                       # the anchor threads every section
            pal = list(getattr(sec, "palette", None) or [])
            if not any(_resolve(c) == _resolve(anchor) for c in pal):
                sec.palette = pal + [anchor]

    # the chorus label's occurrences share one signature pair, verbatim across every occurrence
    rm = repetition_map or {}
    chorus_key = next((k for k in rm if "chorus" in k.lower() and len(rm[k]) > 1), None)
    if chorus_key is None:                          # no explicit chorus → the most-recurring label
        recurring = [(k, v) for k, v in rm.items() if len(v) > 1]
        chorus_key = max(recurring, key=lambda kv: len(kv[1]))[0] if recurring else None
    if chorus_key is not None:
        pair = _signature_pair(sections, rm[chorus_key])
        for si in rm[chorus_key]:
            if 0 <= si < len(sections):
                pal = [c for c in (sections[si].palette or []) if c not in pair]
                sections[si].palette = list(pair) + pal   # signature leads, verbatim + shared

    # the bridge leads with the anchor's complement — a deliberate hue departure
    bi = _bridge_index(sections, rm)
    if bi is not None and anchor is not None:
        floored = ensure_contrast([anchor])         # anchor + its injected complement
        complement = next((c for c in floored if _resolve(c) != _resolve(anchor)), None)
        if complement is not None:
            sections[bi].palette = _prepend(sections[bi].palette, complement)
    return plan
