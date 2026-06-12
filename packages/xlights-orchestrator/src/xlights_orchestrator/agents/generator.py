"""Generator agent: one SectionPlan (+ look/palette menu) -> EffectInstruction[]."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import build_agent
from .guide import with_guides
from ..show_plan import SectionEffects, SectionPlan
from .catalog import candidate_look_ids, palette_menu

_PROMPT = (Path(__file__).parent / "prompts" / "generator.md").read_text()


def generator_agent():
    return build_agent("generator", output_type=SectionEffects,
                       system_prompt=with_guides(_PROMPT, "sequencing", "effects", "layering", "scenes"))


def render_input(section: SectionPlan, revision=None, *, concept: str = "", motifs=None) -> str:
    # Look candidates for every effect type the section may place (family + effect_types),
    # so a scene stack's bed/feature/sparkle rows can each use their own type.
    families = dict.fromkeys([section.effect_family, *section.effect_types])
    looks = {ft: ids for ft in families if ft and (ids := candidate_look_ids(ft))}
    revision_note = ""
    if revision is not None:
        revision_note = (
            "\n\nREVISION — the previous attempt at this section had an issue. Fix it:\n"
            f"  issue: {revision.issue}\n  try: {revision.suggested_fix}\n"
            f"  do NOT repeat: {revision.do_not_repeat}"
        )
    brief_note = ""                                  # the creative brief this section must realize
    if concept:
        brief_note += "\n\nSHOW CONCEPT (keep the through-line):\n" + concept
    if motifs:
        brief_note += "\n\nGROUP MOTIFS for this section's groups (honor each group's role/style/color):\n" + \
                      json.dumps({g: m.model_dump() for g, m in motifs.items()})
    scene_note = ""
    if section.scene_id:
        scene_note = (
            f"\n\nSCENE: this section realizes cookbook scene {section.scene_id}"
            + (f" — casting: {section.scene_adaptation}" if section.scene_adaptation else "")
            + ".\nBuild the scene's stack table as instructions: one instruction per row+layer on"
              " the cast groups. The cookbook's L1 is the TOP layer → `layer` 0, L2 → 1, L3 → 2."
              " Set a row's blend mode by putting T_CHOICE_LayerMethod in `extra_settings` on the"
              " UPPER layer's instruction (e.g. {\"T_CHOICE_LayerMethod\": \"Max\"}; values per"
              " the layering guide: Max, Average, Subtractive, 1 is Mask, ...; omit for Normal)."
              " Use the scene's per-row render styles, and avoid its listed failure modes."
              " Substitute a placeable effect type when a row's effect isn't in the candidates"
              " (e.g. a Color Wash bed → a dim On)."
        )
    return (
        "SECTION PLAN (realize its look/palette/effect_types/motion):\n" + section.model_dump_json(indent=1)
        + brief_note
        + scene_note
        + "\n\nCANDIDATE LOOK IDS by effect type (each instruction's look_id MUST come from its"
          " own effect_type's list):\n"
        + json.dumps(looks)
        + "\n\nPALETTE MENU (pick palette_id from these):\n"
        + json.dumps(palette_menu())
        + revision_note
        + "\n\nFor EACH effect set `render_style` (per the layering guide): 'Per Model Default' so every"
          " prop in a group runs the effect and FILLS (most radial/texture effects on groups — this is"
          " how high-energy sections light up); 'Per Preview' for a gesture that should travel/radiate"
          " across the whole yard (sweeps, Shockwave, Wave); 'Default' for simple On/washes. A group-"
          "canvas effect renders as one sparse shape and reads dark — prefer per-model unless you want"
          " one unified gesture."
        + "\n\nDURATION CLASSES: hit effects (Shockwave/Strobe/Lightning) are ≤1-bar PUNCTUATION —"
          " never section-spanning washes. Phrase effects (Curtain/Fill/Morph/Fan/Fireworks) span ≤8"
          " bars. Motion effects (SingleStrand/Spirals/Pinwheel/Ripple/Wave/Bars) are CELL-ABLE —"
          " the weave (below) places them as short beat cells; only beds (ColorWash/Plasma/dim On"
          " on whole-yard rows) run long."
        + "\n\nWEAVE — also design `weave.cells`: 3–6 CELL RECIPES that code expands into"
          " beat-snapped cells across the section (community fabric: short motion cells reused"
          " ~12x, NOT long washes). Each recipe: effect_type (MOTION effects — SingleStrand chase"
          " is the canonical beat-carrier; On/Twinkle only as accent/bed roles), role (exactly one"
          " 'carrier' riding the beat on the rhythm groups; 1–2 'texture'; optional 'bed'),"
          " groups (the alternation set), cell_beats (1=carrier, 2–4=texture), alternation"
          " ('chase' rotates one group per cell, 'pingpong' bounces, 'all' hits every group,"
          " 'sparse' breathes every other cell), direction (the effect's OWN motion direction:"
          " 'ltr'/'rtl' sweeps, 'bounce' alternates, 'center_out'/'center_in' radiate,"
          " 'up'/'down' run vertically — builds go up, releases come down, call-and-response"
          " alternates ltr/rtl between recipes), blend (T_CHOICE_LayerMethod — 'Max' overlays,"
          " 'Brightness' envelopes; only meaningful over a bed/carrier on the same groups),"
          " motion_curve ('rotation'/'twist'/'radius'/'position' — ramps that param over each"
          " cell), transition ('Wipe' flows cells into each other). Blend modes ARE settable."
        + "\n\nProduce effect instructions that follow the creative brief for this section."
    )
