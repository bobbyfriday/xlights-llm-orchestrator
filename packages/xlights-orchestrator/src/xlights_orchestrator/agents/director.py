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
    return build_agent("director", output_type=ShowPlan,
                       system_prompt=with_guides(_PROMPT, "sequencing", "effects", "scenes"))


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
          "- THE PEAK: find the show's single highest-energy moment (its payoff) and reserve the"
          " BROADEST coverage (most groups / the whole display) and biggest gesture for it; build"
          " the section just before it (rising coverage + brightness into the peak). NEVER spend a"
          " narrow or dark look on the peak — a climax that lights one prop reads as a let-down.\n"
          "- per section: a plain-language `look` (what a viewer sees, no theory); plus the grounded"
          " direction — palette, effect_family + effect_types + motion, transition, and a `rationale`"
          " that CITES this section's real intensity / stem shares / accents"
          " (e.g. 'piano 44% intro → soft warm wash on the megatree only').\n"
          "- per-section palette: 3-5 colors INCLUDING a contrast/accent color (not one warm"
          " family) — multi-color effects (Plasma/Spirals/Bars) need 3+ colors to render."
          " LED COLOR REALITY: pixels render hue CONTRAST well and subtle tints terribly —"
          " gold + amber + warm white reads as ONE color on a real display. Every section"
          " palette MUST span hues (≥1 cool vs warm anchor); save tonal subtlety for indoor"
          " media, not LEDs."
          " Name colors ONLY from this vocabulary: " + ", ".join(sorted(NAMED_COLORS)) + ".\n"
          "- FEATURE PROPS POP: when a section's look centers on a dedicated accent/sparkle prop"
          " group (SEM_SNOWFLAKES, SEM_SPINNERS — e.g. 'snow', 'sparkle', 'stars'), make THOSE"
          " props the BRIGHT, high-contrast focal element in a light color (white/ice) over a"
          " DIFFERENT-hued background bed (e.g. white snowflakes on a blue house) — even in a calm"
          " section, the feature is what the viewer should SEE, so it stays bright while the bed"
          " recedes. A dim or same-hue feature (silver snow on a navy house) disappears on LEDs."
          " A featured section is NEVER near-black: 'still/quiet' means gentle MOTION and a dimmer"
          " bed, NOT darkness — keep a visibly-colored background bed on a BROAD group (SEM_ALL) so"
          " the bright feature has something to pop against.\n"
          "- per section, SCENE: set `scene_id` to the SCENE COOKBOOK scene (e.g. 'SC-01') whose"
          " musical slot and energy band fit this section — the Standard Stack is the default for"
          " ordinary verses/choruses; spend showpieces (drop, finale, masked reveal) only on the"
          " moments that earn them; across repeated choruses apply the Escalating Chorus Series"
          " doctrine (chorus 1 reduced, final chorus maximal). Set scene_id to '' only when no"
          " scene fits. Cookbook rows name display ARCHETYPES (G2-HERO, G0-ALL-LESS-HERO, ...),"
          " NOT real groups: in `scene_adaptation`, cast THIS layout's available groups into the"
          " scene's roles (hero/rhythm/frame/accent/canvas, e.g. 'hero=SEM_FOCAL,"
          " rhythm=SEM_ARCHES+SEM_MINITREES, bed=SEM_ALL') and note any rows this layout cannot"
          " cast. target_groups must include every group the scene casts.\n"
          "- per section, a SCENE from the cookbook: set `scene_id` (e.g. 'SC-01'; '' only when no"
          " scene fits) and `scene_adaptation` casting the scene's archetype rows onto the REAL"
          " groups (e.g. 'G2-HERO→SEM_FOCAL; G2-RHYTHM→SEM_ARCHES+SEM_CANES;"
          " G0-ALL-LESS-HERO→SEM_HOUSE+SEM_ACCENTS until subtractive groups exist;"
          " G2-FRAME→SEM_OUTLINE; G2-ACCENT→SEM_SNOWFLAKES+SEM_SPINNERS; G2-CANVAS→Matrixes').\n"
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
                       system_prompt=with_guides(_PROMPT, "sequencing", "effects", "scenes"))


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
          " 3-5 palette colors from the known vocabulary. You may keep or swap the section's"
          " cookbook `scene_id` (check the scene's failure modes against the violations); keep"
          " `scene_adaptation` consistent with the unchanged target_groups."
    )
