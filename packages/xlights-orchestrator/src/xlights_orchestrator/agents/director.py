"""Director agent: MusicBrief (+ groups, placeable types) -> ShowPlan."""

from __future__ import annotations

import json
from pathlib import Path

from xlights_core.knowledge.colors import NAMED_COLORS

from ..models import build_agent
from .guide import with_guides
from ..music_brief import MusicBrief
from ..show_plan import SectionPlan, ShowPlan

_PROMPT = (Path(__file__).parent / "prompts" / "director.md").read_text()


def director_agent():
    return build_agent("director", output_type=ShowPlan, system_prompt=with_guides(_PROMPT, "sequencing", "effects"))


def render_input(brief: MusicBrief, groups: list[str], placeable_types: list[str]) -> str:
    instrumental = not brief.featured_lyric_moments and not brief.narrative_summary
    return (
        "SONG DESCRIPTION (interpreted — design the show ENTIRELY from this):\n"
        + brief.model_dump_json(indent=1)
        + f"\n\nINSTRUMENTAL: {json.dumps(instrumental)}"
        + "\n\nAVAILABLE GROUPS (choose targets only from these):\n" + json.dumps(groups)
        + "\n\nPLACEABLE EFFECT TYPES (effect_family/effect_types only from these):\n"
        + json.dumps(placeable_types)
        + "\n\nProduce a rich CREATIVE BRIEF as a ShowPlan:\n"
          "- `experience`: 1-2 paragraphs of what the AUDIENCE sees & feels, in PLAIN, NON-MUSICAL"
          " language (everyday words, e.g. 'opens like a single candle, grows to a warm glow, erupts"
          " into a full-yard celebration'). No music theory here.\n"
          "- `concept`, `palette` (named colors + how color maps to the song's energy/harmony),"
          " `group_motifs` (each group's role/style/color, coherent across the show),"
          " `key_moments` (accents/climax/featured lyrics → deliberate punctuation at their times).\n"
          "- per section: a plain-language `look` (what a viewer sees, no theory); plus the grounded"
          " direction — palette, effect_family + effect_types + motion, transition, and a `rationale`"
          " that CITES this section's real intensity / stem shares / accents"
          " (e.g. 'piano 44% intro → soft warm wash on the megatree only').\n"
          "- per-section palette: 3-5 colors INCLUDING a contrast/accent color (not one warm"
          " family) — multi-color effects (Plasma/Spirals/Bars) need 3+ colors to render."
          " Name colors ONLY from this vocabulary: " + ", ".join(sorted(NAMED_COLORS)) + ".\n"
          "- per section, RHYTHMIC INTENT for the beat layer: `pulse_groups` (groups that punctuate"
          " the beat — PREFER `SEM_ARCHES` or the `SEM_SIDE_*` spatial chase), `follow_stem` (the"
          " section's most prominent instrument from its stem shares, e.g. drums for the beat),"
          " `accent_effect` (a placeable punctuation effect, e.g. On), `pulse_on` ('beat' for a"
          " steady chase, 'onset' to ride the instrument's hits).\n"
          "GROUND EVERYTHING in the song description. If INSTRUMENTAL, do NOT invent lyrics, a story,"
          " characters, or a genre not supported by it. The title/filename is NOT evidence of content."
    )


def section_redesigner():
    """Re-plans ONE section whose design caused violations (escalation from the refine loop)."""
    return build_agent("director", output_type=SectionPlan,
                       system_prompt=with_guides(_PROMPT, "sequencing", "effects"))


def redesign_input(section, plan, findings) -> str:
    issues = "\n".join(f"- {getattr(f, 'detail', f)}" for f in findings) or "- (see prior critique)"
    return (
        "REDESIGN ONE SECTION. The rendered show violated normative placement rules that trace to"
        " this section's DESIGN (its chosen effect_types/palette) — regeneration alone cannot fix"
        " a flawed design. Re-plan THIS SECTION ONLY.\n\n"
        "CURRENT SECTION PLAN:\n" + section.model_dump_json(indent=1)
        + "\n\nVIOLATIONS to fix BY DESIGN:\n" + issues
        + "\n\nSHOW CONCEPT (stay coherent): " + (plan.concept or "")
        + "\nKeep start_ms/end_ms and target_groups unchanged. Choose effect_types whose catalog"
          " energy band matches this section's intensity and that suit the targeted props;"
          " 3-5 palette colors from the known vocabulary."
    )
