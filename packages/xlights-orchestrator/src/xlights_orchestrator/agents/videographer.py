"""Videographer agent: a song's story material -> a storyboard for the centerpiece video matrix.

The input is built from STORY fields only (lyrics, narrative, themes, sentiment, mood, featured
lines) plus section structure, energy and the show palette. The lights' per-section look / motion /
effect types / target groups are deliberately withheld so the film cannot replicate the display.
"""

from __future__ import annotations

from pathlib import Path

from ..models import build_agent
from ..video_script import VideographerOut

_PROMPT = (Path(__file__).parent / "prompts" / "videographer.md").read_text()

# ShowPlan section fields that describe the LIGHTS — never shown to the Videographer.
LIGHTING_FIELDS = ("look", "motion", "effect_types", "effect_family", "target_groups", "transition",
                   "rationale", "scene_id", "scene_adaptation", "pulse_groups", "accent_effect")


def videographer_agent():
    return build_agent("videographer", output_type=VideographerOut, system_prompt=_PROMPT)


def _line(label: str, value) -> str:
    if value in (None, "", [], {}):
        return f"{label}: (not available)"
    if isinstance(value, list):
        return f"{label}: " + "; ".join(str(v) for v in value)
    return f"{label}: {value}"


def render_input(*, song: str, description: dict, brief: dict, sections: list[tuple[int, int]],
                 labels: list[str], energies: list[float],
                 lyrics: list[tuple[int, str]]) -> str:
    """The Videographer's prompt input. Reads only story fields + structure + palette."""
    palette = brief.get("palette") or {}
    pal = ", ".join(palette.get("colors") or []) if isinstance(palette, dict) else ""
    pal_name = palette.get("name", "") if isinstance(palette, dict) else ""
    climax = max(range(len(energies)), key=lambda i: energies[i]) if energies else None

    L = [f"SONG: {song}", "",
         "STORY MATERIAL",
         _line("Narrative / journey", description.get("narrative_or_journey")),
         _line("Themes", description.get("candidate_themes")),
         _line("Sentiment", description.get("sentiment")),
         _line("Mood", description.get("key_mood")),
         _line("Featured lines", description.get("featured_lines")),
         "",
         "LIGHT SHOW (for colour and tone only — never depict it)",
         _line("Palette", f"{pal_name} — {pal}" if pal_name else pal),
         _line("Concept", brief.get("concept")),
         "",
         "SECTIONS (write exactly one beat per index)"]
    for i, ((s, e), lab, en) in enumerate(zip(sections, labels, energies)):
        mark = "  <- CLIMAX" if i == climax else ""
        L.append(f"  [{i}] {lab or 'section'} · {(e - s) / 1000:.1f}s · energy {en:.2f}{mark}")
    L += ["", "LYRICS (time the line is sung → section index)"]
    if lyrics:
        for ms, text in lyrics:
            idx = next((i for i, (s, e) in enumerate(sections) if s <= ms < e), None)
            L.append(f"  [{idx}] {text}" if idx is not None else f"  [-] {text}")
    else:
        L.append("  (no aligned lyrics — instrumental or lyrics unavailable)")
    return "\n".join(L)
