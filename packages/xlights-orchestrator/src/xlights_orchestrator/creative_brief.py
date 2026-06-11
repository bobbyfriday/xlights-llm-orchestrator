"""Pure Markdown render of the creative brief (ShowPlan) for human review.

Leads with the plain-language `experience` so a non-musician can confirm the vibe, then the
grounded direction (palette, group motifs, per-section direction, key moments).
"""

from __future__ import annotations

from .show_plan import ShowPlan


def _mmss(ms: int) -> str:
    s = max(0, int(ms)) // 1000
    return f"{s // 60}:{s % 60:02d}"


def render_creative_brief(plan: ShowPlan) -> str:
    L: list[str] = ["# Creative brief\n"]
    if plan.experience:
        L.append("## What the show is\n" + plan.experience + "\n")        # plain-language, leads
    if plan.concept:
        L.append("\n**Concept:** " + plan.concept + "\n")
    if plan.palette:
        cols = ", ".join(plan.palette.colors)
        L.append(f"\n**Palette** ({plan.palette.name}): {cols}\n")
        if plan.palette.mapping:
            L.append(plan.palette.mapping + "\n")
    if plan.group_motifs:
        L.append("\n## Group roles\n")
        for g, m in plan.group_motifs.items():
            bits = " · ".join(b for b in [m.role, m.style, m.color] if b)
            L.append(f"- **{g}** — {bits}\n")

    L.append("\n## Sections\n")
    for i, s in enumerate(plan.sections):
        L.append(f"\n### {i}. {_mmss(s.start_ms)}–{_mmss(s.end_ms)} · intensity {s.intensity:.2f}\n")
        if s.look:
            L.append(f"*{s.look}*\n")                                     # plain "what you see"
        if s.palette:
            L.append(f"- palette: {', '.join(s.palette)}\n")
        if s.target_groups:
            L.append(f"- groups: {', '.join(s.target_groups)}\n")
        fx = ", ".join(s.effect_types) or s.effect_family
        if fx:
            L.append(f"- effects: {fx}" + (f" · {s.motion}" if s.motion else "") + "\n")
        if s.rationale:
            L.append(f"- why: {s.rationale}\n")
        if s.transition:
            L.append(f"- → {s.transition}\n")

    if plan.key_moments:
        L.append("\n## Key moments\n")
        for k in plan.key_moments:
            L.append(f"- **{_mmss(k.at_ms)}** ({k.kind}) — {k.treatment}\n")
    return "".join(L)
