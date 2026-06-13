"""Generator agent: one SectionPlan (+ look/palette menu) -> EffectInstruction[]."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import build_agent
from .guide_extracts import (
    catalog_essentials,
    layering_essentials,
    scene_recipe,
    sequencing_essentials,
)
from ..show_plan import SectionEffects, SectionPlan
from .catalog import candidate_look_ids, palette_menu

_PROMPT = (Path(__file__).parent / "prompts" / "generator.md").read_text()


def _system_prompt() -> str:
    # Extracts, not the full ~100KB guide corpus — the generator runs ~21x/run (≈60% of run
    # cost); the Director's single call carries the full guides. Scene recipes go per-section
    # in render_input. Missing guides degrade to '' (skipped).
    parts = [
        ("EFFECTS CATALOG ESSENTIALS", catalog_essentials()),
        ("RENDER STYLES", layering_essentials()),
        ("SEQUENCING ESSENTIALS", sequencing_essentials()),
    ]
    out = _PROMPT
    for title, text in parts:
        if text:
            out += f"\n\n## {title}\n\n{text}"
    return out


def generator_agent():
    return build_agent("generator", output_type=SectionEffects, system_prompt=_system_prompt())


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
        recipe = scene_recipe(section.scene_id)   # only THIS scene's block (system prompt has none)
        if recipe:
            scene_note += "\n\nSCENE RECIPE (from the cookbook — realize this):\n" + recipe
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
        + "\n\nFEATURE PROPS POP (LED contrast): if this section features a dedicated accent/sparkle"
          " prop group (SEM_SNOWFLAKES, SEM_SPINNERS), light those props BRIGHT in a LIGHT color"
          " (white/ice) so they read, over a DIFFERENT-hued background bed (e.g. blue) on the other"
          " groups — white flakes on a blue house, NOT silver flakes on a navy house (same hue +"
          " dim = invisible). Keep the feature bright even in a calm section."
          " CAVEAT: the named particle effects (Snowflakes/Snowstorm/Meteors) only read as falling"
          " particles on a LARGE canvas (a whole-house/Matrix group on 'Default' or 'Per Preview'"
          " with a high Count); on small dedicated flake-shaped props they render nothing visible —"
          " there light the PROPS directly with a bright solid On in the flake color (a whole-prop"
          " glow). PREFER On over Twinkle/sparse effects on small props — sparse effects light too"
          " few pixels per frame to read on a few-pixel prop."
          " To pin the feature's color, set `palette_colors` EXPLICITLY on that instruction (e.g."
          " [\"white\"] for snow) — an explicit palette_colors is respected as-is; leave it empty"
          " elsewhere to take the section family."
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
          " 'up'/'down' run vertically, 'alternate' flips direction every bar — builds go up,"
          " releases come down; TWO opposite sweeps (or two 'alternate's) on the same groups"
          " auto-weave in counter-phase: cross, bounce off the ends, cross back; directional"
          " sweep cells render across the WHOLE"
          " group and read best at cell_beats 4 — a bar-length traveling gesture), blend"
          " (T_CHOICE_LayerMethod — 'Max' overlays,"
          " 'Brightness' envelopes; only meaningful over a bed/carrier on the same groups),"
          " motion_curve ('rotation'/'twist'/'radius'/'position' — ramps that param over each"
          " cell), transition ('Wipe' flows cells into each other). Blend modes ARE settable."
        + "\n\nProduce effect instructions that follow the creative brief for this section."
    )
