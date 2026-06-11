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
    scene_note = ""
    if getattr(section, "scene_id", ""):
        scene_note = ("\n\nSCENE: realize cookbook scene " + section.scene_id
                      + " — follow its stack table (rows top-to-bottom, layers, effects, render"
                        " styles) cast onto the real groups per this adaptation: "
                      + (section.scene_adaptation or "(cast sensibly)")
                      + ". Multiple instructions on the same target are fine (layers are assigned"
                        " automatically); blend modes are not settable — design for Normal.")
    brief_note = scene_note                          # the creative brief this section must realize
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
          " bars. Prefer SEVERAL SHORT effects across a section over one long static wash — the"
          " display should keep changing."
        + "\n\nProduce effect instructions that follow the creative brief for this section."
    )
