"""Visual critic: looks at rendered stills + clips of the show, returns scoped findings.

Multimodal (image + video) — proven against gemini-3.1-pro-preview this session.
Findings are ADVISORY: they inform the Judge/human, they never enter the objective gate.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import BinaryContent

from ..models import build_agent
from .guide import with_guides
from ..refine import Finding

_PROMPT = (
    "You are the visual critic of a rendered Christmas light show. For each section you get a STILL"
    " (spatial: coverage/color/dark areas/monotony), a short VIDEO CLIP (motion/energy over time),"
    " and the section's MUSICAL CONTEXT (label, intensity, neighbors). Judge the visuals AGAINST THE"
    " MUSIC AT THAT MOMENT: darkness/staticness/low-energy is NOT inherently wrong — a dark, quiet"
    " beat before a transition is intentional and good; the same mid-peak is a defect. Also assess"
    " whether the show is dynamic and varied (not repetitive, not random) and whether the effects go"
    " with the music. Return a short `summary` plus scoped `findings` (each: section_index, severity,"
    " aspect, plain-language issue/fix). Mark severity=error ONLY for a real defect IN CONTEXT (e.g."
    " dark/static during a high-energy moment, repetitive, random, energy-mismatched) — never for"
    " darkness/quiet that fits the music. Do not invent issues if a section fits its moment."
)


class VisualFinding(BaseModel):
    section_index: int | None = None
    severity: Literal["info", "warn", "error"] = "warn"
    aspect: Literal["coverage", "color", "motion", "energy", "other"] = "other"
    detail: str


class VisualFindings(BaseModel):
    summary: str = ""
    findings: list[VisualFinding] = []


def visual_critic_agent():
    return build_agent("visual_critic", output_type=VisualFindings, system_prompt=with_guides(_PROMPT, "sequencing", "layering"))


def render_input(media: list[tuple], plan, brief) -> list:
    """media: list of (label, png_bytes, mp4_bytes|None) aligned to brief.sections. Multimodal prompt."""
    secs = list(getattr(brief, "sections", []) or [])
    themes = getattr(brief, "candidate_themes", []) if brief else []
    mood = getattr(brief, "key_mood", "") if brief else ""
    parts: list = [
        "SHOW INTENT:\n" + json.dumps({"key_mood": mood, "themes": themes})
        + "\n\nFor each section judge the visuals AGAINST THE MUSIC at that moment (use the context):"
    ]
    for i, (label, png, mp4) in enumerate(media):
        sec = secs[i] if i < len(secs) else None     # sampler builds media from sections in order
        ctx = {
            "section_index": i, "label": label,
            "intensity": getattr(sec, "intensity", None) if sec else None,
            "prev": secs[i - 1].label if (sec and i > 0) else None,
            "next": secs[i + 1].label if (sec and i + 1 < len(secs)) else None,
        }
        parts.append(f"\n--- section {i} [{label}] music: {json.dumps(ctx)} ---")
        parts.append(BinaryContent(data=png, media_type="image/png"))
        if mp4:
            parts.append(BinaryContent(data=mp4, media_type="video/mp4"))
    parts.append("\nReturn VisualFindings (summary + scoped findings; set section_index on each).")
    return parts


def to_findings(vf: VisualFindings) -> list[Finding]:
    """Map visual findings into the refine `Finding` shape — always ADVISORY (objective=False)."""
    out = []
    for f in vf.findings:
        scope = f"section {f.section_index}" if f.section_index is not None else "global"
        out.append(Finding(scope=scope, severity=f.severity, metric=f"visual:{f.aspect}",
                           detail=f.detail, objective=False, section_index=f.section_index))
    return out
