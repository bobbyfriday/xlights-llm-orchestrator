"""Per-purpose extracts of the user guides for the per-section generator (21 calls/run):
deterministic heading slices instead of the full ~100KB corpus. The Director (1 call/run)
keeps the full guides. Best-effort throughout — every function degrades to '' (a thinner
prompt is a valid state; never raise)."""

from __future__ import annotations

import re

from .guide import load_guide

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$", re.MULTILINE)


def _cut(text: str, want) -> str:
    """Concatenated sections whose heading title satisfies `want(title)`; each section runs
    from its heading to the next heading of the same-or-higher level. '' when none match.
    Level-1 headings are document titles, never sections — they'd swallow the whole guide."""
    heads = [(m.start(), len(m.group(1)), m.group(2)) for m in _HEADING.finditer(text)]
    out: list[str] = []
    for i, (start, level, title) in enumerate(heads):
        if level == 1 or not want(title):
            continue
        end = len(text)
        for s2, l2, _ in heads[i + 1:]:
            if l2 <= level:
                end = s2
                break
        out.append(re.sub(r"\n+-{3,}\s*$", "", text[start:end].rstrip()))  # drop trailing hr
    return "\n\n".join(out)


def catalog_essentials() -> str:
    """Quick Reference Table (incl. duration classes) + Placement Decision Rules — the parts
    a per-section generator actually decides with; per-effect prose stays Director-only."""
    text = load_guide("effects")
    return _cut(text, lambda t: "Quick Reference Table" in t or "Placement Decision Rules" in t)


def layering_essentials() -> str:
    """The render-style section of the layering guide; first 4KB if the headings move.
    'Render Style' first — a bare 'Render'/'Buffer' match drags in 3 more sections (~5KB)."""
    text = load_guide("layering")
    out = _cut(text, lambda t: "Render Style" in t)
    if not out:
        out = _cut(text, lambda t: "Render" in t or "Buffer" in t)
    return out or text[:4096]


def scene_recipe(scene_id: str) -> str:
    """ONLY the named scene's block from the cookbook (heading contains the id, e.g. 'SC-09');
    '' when scene_id is empty or unknown."""
    if not scene_id:
        return ""
    return _cut(load_guide("scenes"), lambda t: scene_id in t)


def sequencing_essentials() -> str:
    """Core Philosophy plus rhythm/call sections, bounded to ~3KB total. The raw first-3KB
    opening is mostly ToC + version boilerplate, and an unbounded extract blows the
    generator's <15KB prompt budget — prefer the philosophy section; fall back to the
    opening slice only when the heading moved."""
    text = load_guide("sequencing")
    head = _cut(text, lambda t: "Philosophy" in t)
    if not head:
        head = text[:3072]
    extra = _cut(text, lambda t: "rhythm" in t.lower() or "call" in t.lower())
    out = (head + ("\n\n" + extra if extra else "")).strip()
    if len(out) > 3072:                       # bound, cut on a line boundary
        out = out[:3072]
        if "\n" in out:
            out = out[:out.rfind("\n")].rstrip()
    return out
