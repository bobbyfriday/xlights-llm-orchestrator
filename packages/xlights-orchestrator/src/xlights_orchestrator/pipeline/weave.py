"""The cell weaver: deterministic expansion of LLM-designed CellRecipes into beat-snapped cells.

The community fabric (docs/effects-layering-analysis.md) is ~49 distinct cell designs/min reused
~12× each at ~1,300 placements/min — the repetition is mechanical, so the LLM designs the few
recipes (judgment) and this module expands them across the section's real beat grid (realization),
the same split as palettes/beats/brightness.
"""

from __future__ import annotations

from xlights_core.knowledge.colors import contrast_anchors
from xlights_core.knowledge.value_curves import brightness_setting, motion_curve_setting

from ..agents.catalog import candidate_look_ids, placeable_effect_types
from ..show_plan import CellRecipe, EffectInstruction, SectionPlan, SectionWeave
from .beats import (
    _downsample,
    effect_palette,
    effect_speed_setting,
    section_is_rhythmic,
    wash_brightness,
)
from .semantic_groups import ACCENT_GROUPS, BED_PREFERENCE, RHYTHM_GROUPS, RHYTHM_POOL

# Density budget + bed brightness are show-feel dials (see tuning.py).
from .tuning import BUDGET_BASE, BUDGET_SCALE, WEAVE_BED_BRIGHTNESS as BED_BRIGHTNESS

MAX_WOVEN_RECIPES = 3            # one carrier + up to two textures/accents (layer pressure cap)

# Motion vocabulary for the fallback weave's texture pick (cell-able types; see qa.rules).
_FALLBACK_CARRIER = "SingleStrand"
# Only bed-CAPABLE effects may run as the section-spanning bed (catalog §2.1 v0.3) — an LLM
# recipe naming Pinwheel/Meteors as "bed" demotes to a texture (it weaves instead).
_BED_EFFECTS = {"Color Wash", "Plasma", "On"}


# Direction realized through the EFFECTS' OWN settings (no grouping/target changes — user
# decision). Values are strictly corpus-observed (community .xsq) — valid by construction.
# direction -> (key, value) per effect type; missing pairs no-op.
DIRECTION_KNOBS: dict[str, dict[str, tuple[str, str]]] = {
    "SingleStrand": {"ltr": ("E_CHOICE_Chase_Type1", "Left-Right"),
                     "rtl": ("E_CHOICE_Chase_Type1", "Right-Left"),
                     "bounce": ("E_CHOICE_Chase_Type1", "Dual Bounce"),
                     "center_out": ("E_CHOICE_Chase_Type1", "From Middle"),
                     "center_in": ("E_CHOICE_Chase_Type1", "To Middle")},
    "Bars": {"ltr": ("E_CHOICE_Bars_Direction", "Right"),
             "rtl": ("E_CHOICE_Bars_Direction", "Left"),
             "up": ("E_CHOICE_Bars_Direction", "up"),
             "down": ("E_CHOICE_Bars_Direction", "down"),
             "center_out": ("E_CHOICE_Bars_Direction", "H-expand"),
             "center_in": ("E_CHOICE_Bars_Direction", "H-compress")},
    "Garlands": {"ltr": ("E_CHOICE_Garlands_Direction", "Right"),
                 "rtl": ("E_CHOICE_Garlands_Direction", "Left"),
                 "up": ("E_CHOICE_Garlands_Direction", "Up"),
                 "down": ("E_CHOICE_Garlands_Direction", "Down"),
                 "bounce": ("E_CHOICE_Garlands_Direction", "Left then Right")},
    "Meteors": {"ltr": ("E_CHOICE_Meteors_Effect", "Right"),
                "up": ("E_CHOICE_Meteors_Effect", "Up"),
                "down": ("E_CHOICE_Meteors_Effect", "Down"),
                "center_out": ("E_CHOICE_Meteors_Effect", "Explode"),
                "center_in": ("E_CHOICE_Meteors_Effect", "Implode")},
    "Fill": {"ltr": ("E_CHOICE_Fill_Direction", "Right"),
             "rtl": ("E_CHOICE_Fill_Direction", "Left"),
             "up": ("E_CHOICE_Fill_Direction", "Up"),
             "down": ("E_CHOICE_Fill_Direction", "Down")},
    "Wave": {"ltr": ("E_CHOICE_Wave_Direction", "Left to Right"),
             "rtl": ("E_CHOICE_Wave_Direction", "Right to Left")},
    "Butterfly": {"ltr": ("E_CHOICE_Butterfly_Direction", "Normal"),
                  "rtl": ("E_CHOICE_Butterfly_Direction", "Reverse")},
    "Marquee": {"ltr": ("E_CHECKBOX_Marquee_Reverse", "0"),
                "rtl": ("E_CHECKBOX_Marquee_Reverse", "1")},
    "Fan": {"center_out": ("E_CHECKBOX_Fan_Reverse", "0"),
            "center_in": ("E_CHECKBOX_Fan_Reverse", "1")},
    "Galaxy": {"center_out": ("E_CHECKBOX_Galaxy_Reverse", "0"),
               "center_in": ("E_CHECKBOX_Galaxy_Reverse", "1")},
    "Pinwheel": {"ltr": ("E_CHECKBOX_Pinwheel_Rotation", "1"),
                 "rtl": ("E_CHECKBOX_Pinwheel_Rotation", "0")},
}
# effects whose bounce lives INSIDE the effect (no per-bar flipping needed)
_NATIVE_BOUNCE = {"SingleStrand", "Garlands"}
_BEATS_PER_BAR = 4
# a HORIZONTAL/RADIAL sweep on a chase-family effect must travel across the GROUP to be seen —
# per-model rendering confines it to each prop for half a second (the invisible-sweep failure)
_SWEEP_DIRECTIONS = {"ltr", "rtl", "bounce", "alternate", "center_out", "center_in"}
_CHASE_FAMILY = {"SingleStrand", "Garlands", "Marquee", "Wave", "Bars"}
_SWEEP_MIN_BEATS = 2                      # motion needs dwell time to track


def direction_setting(effect_type: str, direction: str, bar: int) -> dict[str, str]:
    """The effect-native settings for a cell's direction; `{}` when unmapped (never a skip).

    `bounce` uses the effect's native bounce when it has one; otherwise the direction VALUE
    flips at bar boundaries (ltr/rtl, or up/down for vertical-natured effects) — constant
    within a bar so the gesture reads as phrasing, not jitter.
    """
    table = DIRECTION_KNOBS.get(effect_type)
    if not table or not direction:
        return {}
    # "alternate" ALWAYS flips the value per bar (counter-phase via the bar offset) — unlike
    # "bounce", it bypasses native bounce types so two staggered layers can weave.
    if direction == "alternate" or (direction == "bounce" and effect_type not in _NATIVE_BOUNCE):
        pair = ("ltr", "rtl") if "ltr" in table and "rtl" in table else \
               ("up", "down") if "up" in table and "down" in table else None
        if pair is None:
            return {}
        direction = pair[bar % 2]
    kv = table.get(direction)
    return {kv[0]: kv[1]} if kv else {}


def canon_effect_type(name: str) -> str:
    """Normalize an effect name to its placeable form ('Single Strand' → 'SingleStrand') —
    LLMs echo the guides' display names, the API wants xLights' internal ones."""
    if not name:
        return name
    types = placeable_effect_types()
    if name in types:
        return name
    squeezed = name.replace(" ", "")
    return next((t for t in types if t == squeezed or t.replace(" ", "") == squeezed), name)


def cell_budget(intensity: float, section_ms: int) -> int:
    """Max woven instructions for a section — scales with energy and length."""
    i = max(0.0, min(1.0, intensity or 0.0))
    return max(4, int(section_ms / 60000.0 * (BUDGET_BASE + BUDGET_SCALE * i)))


def rhythm_pool(section: SectionPlan, available_groups: list[str]) -> list[str]:
    """The groups the deterministic beat layer chases. Respects the brief: builds from the groups
    the brief actually chose (pulse_groups, then rhythm props in target_groups), and only INJECTS
    the default rhythm pool when the section is rhythmic. A deliberately quiet section that chose
    no rhythm groups gets `[]` — code won't light props the brief kept dark."""
    groups = [g for g in (section.pulse_groups or []) if g in available_groups]
    rhythm_set = set(RHYTHM_POOL) | set(RHYTHM_GROUPS)
    for g in (section.target_groups or []):                  # rhythm props the brief explicitly chose
        if g in available_groups and g in rhythm_set and g not in groups:
            groups.append(g)
    if groups or not section_is_rhythmic(section):
        return groups                  # the brief named rhythm groups (use exactly those), OR
                                       # it's a quiet section that named none (stay dark)
    for g in RHYTHM_POOL:              # rhythmic but the brief named no rhythm groups → inject default
        if len(groups) >= 3:
            break
        if g in available_groups:
            groups.append(g)
    return groups or [g for g in RHYTHM_GROUPS if g in available_groups] \
        or [g for g in section.target_groups if g in available_groups]


def carrier_covers(weave: SectionWeave | None, section: SectionPlan,
                   available_groups: list[str]) -> bool:
    """True when a carrier recipe's VALID groups intersect the actual rhythm pool — only then may
    the beat-accent layer drop its every-beat chase (the carrier IS the beat now)."""
    if weave is None:
        return False
    pool = set(rhythm_pool(section, available_groups))
    for r in weave.cells:
        if r.role == "carrier" and set(r.groups) & set(available_groups) & pool:
            return True
    return False


def fallback_weave(section: SectionPlan, available_groups: list[str]) -> SectionWeave:
    """A deterministic default fabric: a chase carrier on the rhythm pool + a sparse texture from
    the section's own effect vocabulary. Used when the LLM omits the weave — the fabric never
    depends on perfect LLM output.

    NON-RHYTHMIC sections get NO synthesized fabric: a deliberately quiet/still section the brief
    asked for is not a dead section, and code must not inject a chase the brief didn't want."""
    from ..qa.rules import DURATION_CELLABLE
    if not section_is_rhythmic(section):
        return SectionWeave(cells=[])
    cells = [CellRecipe(effect_type=_FALLBACK_CARRIER, role="carrier", cell_beats=1,
                        alternation="chase", direction="bounce",
                        groups=rhythm_pool(section, available_groups))]
    texture = next((t for t in (canon_effect_type(x) for x in section.effect_types or [])
                    if t in DURATION_CELLABLE and t != _FALLBACK_CARRIER), None)
    tex_groups = [g for g in section.target_groups
                  if g in available_groups and g not in ACCENT_GROUPS]
    if texture and tex_groups:
        cells.append(CellRecipe(effect_type=texture, role="texture", cell_beats=4,
                                alternation="sparse", groups=tex_groups))
    return SectionWeave(cells=cells)


def _slot_targets(recipe: CellRecipe, slot: int, groups: list[str]) -> list[str]:
    """Which group(s) a slot lights — a pure function of (slot index, groups, pattern)."""
    n = len(groups)
    alt = recipe.alternation or "chase"
    if alt == "all":
        return list(groups)
    if alt == "sparse":                       # every other slot breathes
        return [groups[(slot // 2) % n]] if slot % 2 == 0 else []
    if alt == "pingpong" and n > 1:
        period = 2 * n - 2
        k = slot % period
        return [groups[k if k < n else period - k]]
    return [groups[slot % n]]                 # chase


def _valid_recipes(weave: SectionWeave, section: SectionPlan, available_groups: list[str]
                   ) -> tuple[list[CellRecipe], CellRecipe | None, dict[int, int]]:
    """Validate + order: (bed-first realization order is the BLEND-correctness invariant —
    base layers must be PLACED first so the emitter stacks them under the blended cells)."""
    cells = [r.model_copy(update={"effect_type": canon_effect_type(r.effect_type)})
             for r in weave.cells]
    for r in cells:                                      # only bed-capable effects may bed
        if r.role == "bed" and r.effect_type not in _BED_EFFECTS:
            r.role = "texture"                           # a Pinwheel "bed" weaves instead
        if r.direction in _SWEEP_DIRECTIONS and r.effect_type in _CHASE_FAMILY:
            r.cell_beats = max(r.cell_beats, _SWEEP_MIN_BEATS)   # sweeps need dwell time
    beds = [r for r in cells if r.role == "bed"]
    others: list[CellRecipe] = []
    for r in cells:
        if r.role == "bed" or not (r.effect_type and candidate_look_ids(r.effect_type)):
            continue
        groups = [g for g in r.groups if g in available_groups]
        if not groups and r.role == "carrier":           # a carrier always finds the pool
            groups = rhythm_pool(section, available_groups)
        if groups:
            others.append(r.model_copy(update={"groups": groups}))
    others.sort(key=lambda r: 0 if r.role == "carrier" else 1)   # carrier = the base layer
    others = others[:MAX_WOVEN_RECIPES]
    # COUNTER-PHASE: an opposite ltr/rtl chase pair on the same groups reads as a perpetual
    # head-on collision — upgrade both to per-bar alternation in opposite phase, so the layers
    # cross, bounce off the ends, and cross back (a woven figure). The pair is detected from
    # the EFFECTIVE direction (the recipe's field, else the chosen look's own chase-type value:
    # in practice the LLM builds crossing chases by picking two opposed LOOKS with empty
    # direction fields). Explicit "alternate" recipes on shared groups stagger by order.
    phases: dict[int, int] = {}
    chases = [r for r in others if r.effect_type in _CHASE_FAMILY]
    static = [(r, d) for r in chases if (d := _effective_direction(r)) in ("ltr", "rtl")]
    for i, (a, da) in enumerate(static):                 # pair recipes with OVERLAPPING groups
        for b, db in static[i + 1:]:                     # (run 8: a pool-chasing carrier vs a
            if {da, db} == {"ltr", "rtl"} and set(a.groups) & set(b.groups) \
                    and id(a) not in phases and id(b) not in phases:
                a.direction = b.direction = "alternate"
                phases[id(a)], phases[id(b)] = 0, 1      #  single-group texture — overlap, not
    for p, r in enumerate([r for r in chases             #  identical sets)
                           if r.direction == "alternate" and id(r) not in phases]):
        phases[id(r)] = p
    bed = next((b for b in beds if b.effect_type and candidate_look_ids(b.effect_type)), None)
    return others, bed, phases


def _effective_direction(recipe: CellRecipe) -> str:
    """The recipe's direction, else the one implied by its look's own direction value
    (frozen or knob default) — '' when neither resolves to a plain ltr/rtl."""
    if recipe.direction:
        return recipe.direction
    table = DIRECTION_KNOBS.get(recipe.effect_type)
    looks = candidate_look_ids(recipe.effect_type)
    if not table or "ltr" not in table or not looks:
        return ""
    from xlights_core.knowledge.preset_library import get_library
    try:
        look = get_library().get_look(
            recipe.effect_type, recipe.look_id if recipe.look_id in looks else looks[0])
    except Exception:  # noqa: BLE001 — detection is best-effort
        return ""
    key = table["ltr"][0]
    val = look.frozen_base.get(key)
    if val is None:
        kn = next((k for k in look.knobs if k.key == key), None)
        val = kn.default if kn is not None else None
    if val == table["ltr"][1]:
        return "ltr"
    if "rtl" in table and val == table["rtl"][1]:
        return "rtl"
    return ""


def _cell(recipe: CellRecipe, section: SectionPlan, target: str, slot: int,
          start: int, end: int, intensity: float, blended: bool,
          anchors: tuple[str, str] | None = None, phase: int = 0,
          beats_per_bar: int = _BEATS_PER_BAR) -> EffectInstruction:
    looks = candidate_look_ids(recipe.effect_type)
    look = recipe.look_id if recipe.look_id in looks else looks[0]
    palette = recipe.palette or section.palette
    extra = dict(effect_speed_setting(recipe.effect_type, intensity))
    extra.update(brightness_setting(wash_brightness(intensity)))   # cells pop with the energy
    extra.update(motion_curve_setting(recipe.effect_type, recipe.motion_curve, intensity))
    bar = slot * max(1, recipe.cell_beats) // beats_per_bar        # bar index at the song's meter
    extra.update(direction_setting(recipe.effect_type, recipe.direction, bar + phase))
    if recipe.transition:
        extra.update({"T_CHOICE_In_Transition_Type": recipe.transition,
                      "T_CHOICE_Out_Transition_Type": recipe.transition,
                      "T_SLIDER_In_Transition_Adjust": "50",
                      "T_SLIDER_Out_Transition_Adjust": "50"})
    if blended:                               # blend rides the UPPER layer, only over a base.
        # Default Max (live-verified): a top-layer cell's BLACK background otherwise OCCLUDES
        # the bed/wash below it for the cell's whole span — the "mostly dark with sparse
        # effects" failure. Max adds the cell's lit pixels and lets the base shine through.
        extra["T_CHOICE_LayerMethod"] = recipe.blend or "Max"
    # CELLS render per-model by default: the global fallback sends chases to 'Per Preview'
    # (one gesture traveling the WHOLE yard buffer — a 0.5s cell on one group lights almost
    # nothing). A cell is rhythmic multiplicity: every prop in the group runs it.
    # EXCEPT a directional sweep: per-model confines the motion to each prop — the sweep MUST
    # travel the GROUP buffer to be seen. This is forced (not a default): the Generator
    # reflexively sets render_style on every recipe, which silently un-swept the sweeps.
    sweep = recipe.direction in _SWEEP_DIRECTIONS and recipe.effect_type in _CHASE_FAMILY
    style = "Default" if sweep else (recipe.render_style or "Per Model Default")
    # LED-contrast floor: rhythm-carrying cells alternate the two most hue-distant anchors
    # beat-to-beat (pixels render hue contrast, not subtle tints); textures keep the family.
    if anchors and recipe.role in ("carrier", "accent") and not recipe.palette:
        colors = [anchors[slot % 2]]
    else:
        colors = effect_palette(palette, recipe.effect_type, slot)
    return EffectInstruction(
        target=target, effect_type=recipe.effect_type, look_id=look,
        palette_colors=colors,
        render_style=style, extra_settings=extra,
        start_ms=start, end_ms=end)


def expand_weave(section: SectionPlan, weave: SectionWeave | None, rhythm: dict,
                 intensity: float, available_groups: list[str],
                 based_targets: set[str] | None = None) -> list[EffectInstruction]:
    """Expand the section's recipes into beat-snapped cells: slot boundaries on the real beat
    grid (`cell_beats` beats per slot; the trailing partial slot merges into the last), targets
    rotating per the alternation pattern, density bounded by `cell_budget`.

    `based_targets` = targets that already carry a base layer this section (the LLM's washes/
    scene rows) — cells over them blend instead of occluding."""
    if weave is None:
        return []
    bpb = rhythm.get("beats_per_bar") or _BEATS_PER_BAR    # the song's meter, threaded into cells
    recipes, bed, phases = _valid_recipes(weave, section, available_groups)
    out: list[EffectInstruction] = []
    based: set[str] = set(based_targets or ())   # targets with a base layer this section
    if bed is not None:
        groups = [g for g in bed.groups if g in available_groups] or \
                 [g for g in BED_PREFERENCE if g in available_groups][:1]
        for g in groups[:1]:                  # ONE spanning bed (the long-bed exception)
            ins = _cell(bed, section, g, 0, section.start_ms, section.end_ms,
                        intensity, blended=False)
            ins.extra_settings["C_SLIDER_Brightness"] = BED_BRIGHTNESS
            out.append(ins)
            based.add(g)

    beats = sorted(rhythm.get("beats_ms") or [])
    if len(beats) >= 2 and recipes:
        anchors = contrast_anchors(section.palette)      # the LED-legible alternation pair
        carrier_groups = set(recipes[0].groups) if recipes[0].role == "carrier" else set()
        # candidate cells per recipe: (slot, start, end, target, blended)
        per_recipe: list[list[tuple]] = []
        for ri, r in enumerate(recipes):
            # blend only over a target that actually HAS a base layer (bed or another
            # recipe's carrier) — a mask with nothing under it is a black prop.
            based_for_r = based | (carrier_groups if ri > 0 else set())
            starts = beats[::max(1, r.cell_beats)]
            cells: list[tuple] = []
            for i, t in enumerate(starts):
                end = starts[i + 1] if i + 1 < len(starts) else section.end_ms  # partial merges
                end = min(end, section.end_ms)
                if end <= t:
                    continue
                for tgt in _slot_targets(r, i, r.groups):
                    cells.append((i, int(t), int(end), tgt, tgt in based_for_r))
            per_recipe.append(cells)
        total = sum(len(c) for c in per_recipe)
        budget = max(0, cell_budget(intensity, section.end_ms - section.start_ms) - len(out))
        factor = budget / total if total > budget else 1.0
        for r, cells in zip(recipes, per_recipe):
            kept = _downsample(cells, max(1, round(len(cells) * factor))) if factor < 1 else cells
            for slot, t, end, tgt, blended in kept:
                out.append(_cell(r, section, tgt, slot, t, end, intensity, blended,
                                 anchors=anchors, phase=phases.get(id(r), 0), beats_per_bar=bpb))
    return out
