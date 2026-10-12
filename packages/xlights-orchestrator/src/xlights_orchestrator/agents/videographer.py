"""Videographer agent: a song's story material + the media plan -> a storyboard for the centerpiece matrix.

The input is built from STORY fields only (lyrics, narrative, themes, sentiment, mood, featured
lines) plus section structure, energy, the show palette and — new — each section's MEDIUM (filmed
or procedural) and asset group, so the film is written for what can render it. The lights'
per-section look / motion / effect types / target groups are deliberately withheld so the film
cannot replicate the display.

A deterministic person-lint runs as an output validator: a procedural beat (or any procedural
stand-in) naming a person, face, hand or animal gets ONE model retry naming the beat and the term;
a second hit fails validation, and nothing is written.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, cast

from pydantic_ai import Agent, ModelRetry

from ..media_plan import MediaPlan
from ..models import build_agent
from ..video_script import VideographerOut

_PROMPT = (Path(__file__).parent / "prompts" / "videographer.md").read_text()

# ShowPlan section fields that describe the LIGHTS — never shown to the Videographer.
LIGHTING_FIELDS = ("look", "motion", "effect_types", "effect_family", "target_groups", "transition",
                   "rationale", "scene_id", "scene_adaptation", "pulse_groups", "accent_effect")

# Things procedural rendering cannot draw. A word list in ONE place (a false positive is a one-line
# fix). Matched on word boundaries, case-insensitive, singular/plural where it matters.
PERSON_TERMS = (
    "person", "people", "man", "men", "woman", "women", "child", "children", "kid", "kids", "boy",
    "girl", "baby", "mother", "father", "grandmother", "grandfather", "family", "crowd", "dancer",
    "dancers", "traveler", "traveller", "figure", "figures", "silhouette of a person", "stranger",
    "investigator", "soldier", "singer", "couple", "lovers",
    "face", "faces", "eyes", "hand", "hands", "fingers", "arm", "arms", "feet", "footsteps",
    "animal", "animals", "dog", "cat", "horse", "deer", "reindeer", "bird", "birds", "wolf", "owl",
)
_TERM_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted(PERSON_TERMS, key=len, reverse=True))
                      + r")\b", re.IGNORECASE)


def lint_media(out: VideographerOut, media: Mapping[int, str]) -> list[str]:
    """Violations of the medium contract, as messages the model can act on. Procedural beats'
    imagery/action and EVERY stand-in must be free of PERSON_TERMS; filmed beats need a stand-in."""
    problems: list[str] = []
    for b in out.beats:
        med = media.get(b.section_index)
        if med is None:
            continue
        if med == "procedural":
            hit = _TERM_RE.search(f"{b.imagery} {b.action}")
            if hit:
                problems.append(f"beat for section {b.section_index} is PROCEDURAL but depicts "
                                f"'{hit.group(0)}' — rewrite it with the procedural vocabulary "
                                f"(no people, faces, hands or animals); carry any character with a "
                                f"proxy object motif")
        else:
            if not b.procedural_stand_in.strip():
                problems.append(f"beat for section {b.section_index} is FILMED but has no "
                                f"procedural_stand_in — add one sentence in the procedural vocabulary")
            else:
                hit = _TERM_RE.search(b.procedural_stand_in)
                if hit:
                    problems.append(f"the procedural_stand_in for section {b.section_index} depicts "
                                    f"'{hit.group(0)}' — a stand-in must use only the procedural "
                                    f"vocabulary")
    return problems


def videographer_agent(plan: MediaPlan | None = None, *, model: Any = None) -> "Agent[None, VideographerOut]":
    """The role's agent. With a plan, the media-lint output validator is attached (one ModelRetry)."""
    agent = cast("Agent[None, VideographerOut]",
                 build_agent("videographer", output_type=VideographerOut, system_prompt=_PROMPT, model=model))
    if plan is not None:
        media: dict[int, str] = {s.index: s.medium for s in plan.sections}

        @agent.output_validator
        async def _media_contract(ctx: Any, out: VideographerOut) -> VideographerOut:
            problems = lint_media(out, media)
            if problems:
                raise ModelRetry("Fix these and return the whole storyboard again:\n- "
                                 + "\n- ".join(problems))
            return out
    return agent


def _line(label: str, value) -> str:
    if value in (None, "", [], {}):
        return f"{label}: (not available)"
    if isinstance(value, list):
        return f"{label}: " + "; ".join(str(v) for v in value)
    return f"{label}: {value}"


def render_input(*, song: str, description: dict, brief: dict, sections: list[tuple[int, int]],
                 labels: list[str], energies: list[float],
                 lyrics: list[tuple[int, str]], plan: MediaPlan | None = None) -> str:
    """The Videographer's prompt input. Reads only story fields + structure + palette + media."""
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
         ""]
    if plan is not None:
        filmed = plan.filmed_assets()
        L += ["MEDIA (decided for you — write each beat FOR its medium)",
              "  Filmed sections are rendered by a video model from your description; they may show "
              "people, faces and real places. Each filmed beat ALSO needs a procedural_stand_in.",
              "  Procedural sections are rendered by code: snow, light, geometry, silhouettes of "
              "objects — never people, faces, hands or animals.",
              "  Filmed asset groups (write a group as one shot that returns; the camera and light may vary): "
              + ("; ".join(f"{a.id} = sections {', '.join(map(str, a.sections))}" for a in filmed)
                 if filmed else "(none — the whole film is procedural)"), ""]
    L += ["SECTIONS (write exactly one beat per index)"]
    for i, ((s, e), lab, en) in enumerate(zip(sections, labels, energies)):
        mark = "  <- CLIMAX" if i == climax else ""
        media = ""
        if plan is not None:
            sm = plan.sections[i]
            media = (f" · FILMED (asset {sm.asset}, {sm.clips} clip{'s' if sm.clips != 1 else ''})"
                     if sm.medium == "filmed" else " · PROCEDURAL")
        L.append(f"  [{i}] {lab or 'section'} · {(e - s) / 1000:.1f}s · energy {en:.2f}{media}{mark}")
    L += ["", "LYRICS (time the line is sung → section index)"]
    if lyrics:
        for ms, text in lyrics:
            idx = next((i for i, (s, e) in enumerate(sections) if s <= ms < e), None)
            L.append(f"  [{idx}] {text}" if idx is not None else f"  [-] {text}")
    else:
        L.append("  (no aligned lyrics — instrumental or lyrics unavailable)")
    return "\n".join(L)
