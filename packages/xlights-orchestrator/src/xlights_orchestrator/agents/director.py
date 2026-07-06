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


def render_layout_block(manifest, groups: list[str]) -> str:
    """A compact (~1 KB) layout traits block for the targetable SEM_ groups: per group its role,
    member count, ~nodes, band, and symmetry/order, plus one display line. Grounds the Director in
    the layout's scale/geometry/symmetry (F-E gap #2) — appended only when a manifest exists."""
    if manifest is None:
        return ""
    props = {p.id: p for p in getattr(manifest, "props", None) or []}
    grec = getattr(manifest, "groups", None) or {}
    lines: list[str] = []
    for name in groups:
        gr = grec.get(name)
        if gr is None or not gr.members:
            continue
        members = [props[m] for m in gr.members if m in props]
        if not members:
            continue
        roles = {m.role for m in members}
        role = next(iter(roles)) if len(roles) == 1 else "mixed"
        nodes = sum(m.nodes for m in members)
        bands = {m.pos.band for m in members}
        band = next(iter(bands)) if len(bands) == 1 else "spanning"
        sym = "ordered" if gr.ordered else ("symmetric" if any(m.mirror_of for m in members) else "")
        tag = f" {sym}" if sym else ""
        lines.append(f"- {name}: {role.lower()} ×{len(members)}, ~{nodes} nodes, {band}{tag}")
    d = getattr(manifest, "display", None)
    disp = ""
    if d is not None:
        s = "symmetric" if getattr(d, "symmetric", False) else "asymmetric"
        disp = (f"display: ~{getattr(d, 'width_units', 0):.0f} units wide, focal center "
                f"x={getattr(d, 'focal_x', 0.5):.2f}, {s}\n")
    if not lines:
        return ""
    return ("\n\nLAYOUT TRAITS (scale/geometry/symmetry of each targetable group — plan to them):\n"
            + disp + "\n".join(lines))


def render_input(brief: MusicBrief, groups: list[str], placeable_types: list[str],
                 manifest=None) -> str:
    instrumental = not brief.featured_lyric_moments and not brief.narrative_summary
    return (
        "SONG DESCRIPTION (interpreted — design the show ENTIRELY from this):\n"
        + brief.model_dump_json(indent=1)
        + f"\n\nINSTRUMENTAL: {json.dumps(instrumental)}"
        + "\n\nAVAILABLE GROUPS (choose targets only from these):\n" + json.dumps(groups)
        + render_layout_block(manifest, groups)          # appended only when a manifest exists
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
          "- per section, PHRASING: set `phrasing` to EXACTLY the one word 'legato' or 'staccato'"
          " (no other words). Use 'legato' for calm, introspective, or melancholy sections — the"
          " cells get soft, evolving fades instead of crisp on/off edges, so they breathe rather"
          " than flash; use 'staccato' for energetic, punchy, rhythmic sections that want crisp"
          " hits. Leave it blank to default by the section's energy. You choose only the FEEL —"
          " code owns the actual fade/dissolve timing.\n"
          "- per section, TREATMENT: set `treatment` to EXACTLY one word choosing which LAYERS the"
          " section runs — the point is to WITHHOLD layers in quiet moments, not merely dim them, so"
          " the peak has contrast to land against. 'full' = the whole stack (bed + weave + accents +"
          " composites + feature) — reserve for the peak and biggest choruses; 'pulse' = a bed with"
          " beat accents and a feature, but no busy weave/composite fabric — the workhorse for"
          " ordinary energetic verses/choruses; 'feature' = a dim bed with ONE hero element and only"
          " sparse accents — a spotlight moment; 'gesture' = a single motion on ≤2 groups and nothing"
          " else — a near-empty held breath; 'rest' = a dim bed on ≤2 groups — the quietest moments."
          " Withhold on purpose: a verse that is 'the chorus but dimmer' reads as samey. Leave blank"
          " to let code pick by energy.\n"
          "- per-section palette: 3-5 colors INCLUDING a contrast/accent color (not one warm"
          " family) — multi-color effects (Plasma/Spirals/Bars) need 3+ colors to render."
          " LED COLOR REALITY: pixels render hue CONTRAST well and subtle tints terribly —"
          " gold + amber + warm white reads as ONE color on a real display. Every section"
          " palette MUST span hues (≥1 cool vs warm anchor); save tonal subtlety for indoor"
          " media, not LEDs."
          " HOLIDAY BIAS: if the song is a Christmas/holiday piece, prefer the traditional"
          " RED + GREEN + WHITE primary palette with 1–2 accent colors (gold, cool white, ice"
          " blue), unless the song's mood clearly calls for something else — red vs green are"
          " hue-distant, so this also reads with strong LED contrast."
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
