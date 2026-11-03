"""Realize a section's authored STACK (`SectionPlan.stack`, the xlo-effects vocabulary).

The brief's designer (reading the effect files) says exactly what each layer is: the effect, the
catalog look and its knobs, the raw settings (value curves, blur, sparkles), blend, transform,
direction, palette, whether it holds the section or is re-cut on a beat grid, and whether a
twin layer sits above it. Code does the mechanical part — one row per group (or per cell), the
beat-snapped cuts, the twin's difference, the layer indices — and nothing creative: no speed by
energy, no brightness by energy, no rotated carriers. Where the brief has a stack, the
synthesized weave, composites, phrase gesture, VU and final layer step aside (`generate`).
"""

from __future__ import annotations

from xlights_core.knowledge import get_library
from xlights_core.knowledge.value_curves import brightness_setting

from ..show_plan import CellRecipe, EffectInstruction, SectionPlan, StackLayer
from .beats import effect_palette
from .catalog import pick_look, ranked_look_ids
from .effect_meta import SIGNED_DIRECTION_KEYS
from .weave import _slot_targets, apply_direction, canon_effect_type

_COUNTER = {"ltr": "rtl", "rtl": "ltr", "up": "down", "down": "up",
            "center_out": "center_in", "center_in": "center_out", "": "rtl"}
# the SLIDER dials a counter twin negates when the layer set them (Spirals' twist, Pinwheel's
# twist, Ripple's rotation); checkboxes such as Pinwheel's Rotation are directions, not dials
_TWIST_SUFFIXES = ("_Rotation", "_Twist")


def _cells(section: SectionPlan, rhythm: dict, cell_beats: int) -> list[tuple[int, int, int]]:
    """(slot, start_ms, end_ms) per cell on the section's beat grid; the trailing partial cell
    merges into the last. One spanning cell when the section has no beats."""
    beats = sorted(int(b) for b in (rhythm.get("beats_ms") or [])
                   if section.start_ms <= int(b) < section.end_ms)
    if len(beats) < 2 or cell_beats <= 0:
        return [(0, section.start_ms, section.end_ms)]
    starts = beats[::cell_beats]
    out: list[tuple[int, int, int]] = []
    for i, t in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else section.end_ms
        if end > t:
            out.append((i, int(t), int(min(end, section.end_ms))))
    return out


def _negate(value: str, effect_type: str = "", look_id: str = "", key: str = "") -> str:
    """`-value`, clamped into the look's observed range for that knob (a counter twin of
    `Spirals#80`'s Rotation −80 is +40, the range's top, not an unplaceable +80)."""
    try:
        x = -float(value)
    except ValueError:
        return value
    if look_id and key:
        try:
            knob = next(k for k in get_library().get_look(effect_type, look_id).knobs if k.key == key)
            if knob.numeric and knob.min is not None and knob.max is not None:
                x = min(knob.max, max(knob.min, x))
        except (KeyError, StopIteration):
            pass
    return f"{x:g}"


def _twin_of(ins: EffectInstruction, layer: StackLayer, slot: int, bar: int, *,
             section_palette: list[str], pal_offset: int) -> EffectInstruction:
    twin = ins.model_copy(deep=True)
    twin.layer = ins.layer + 1                 # the twin sits just above its base (logical layers)
    et = ins.effect_type
    if layer.twin == "mirror":
        twin.extra_settings["B_CHOICE_BufferTransform"] = (
            "Flip Horizontal" if ins.extra_settings.get("B_CHOICE_BufferTransform") else "Rotate 180")
    elif layer.twin == "flip":
        twin.extra_settings["B_CHOICE_BufferTransform"] = "Flip Horizontal"
    elif layer.twin == "counter":
        for key in SIGNED_DIRECTION_KEYS:                        # keep the knob's magnitude (Spirals' spin)
            if key in twin.knob_values and key not in twin.extra_settings:
                twin.extra_settings[key] = twin.knob_values[key]
        twin.directed = apply_direction(twin.extra_settings, et, _COUNTER.get(layer.direction, "rtl"), bar)
        for key, val in list(twin.knob_values.items()):          # negate a set twist/rotation dial
            if key.startswith("E_SLIDER_") and key.endswith(_TWIST_SUFFIXES):
                twin.knob_values[key] = _negate(val, et, ins.look_id, key)
        for key, val in list(twin.extra_settings.items()):
            if key.startswith("E_SLIDER_") and key.endswith(_TWIST_SUFFIXES):
                twin.extra_settings[key] = _negate(val)
    elif layer.twin == "color":
        if layer.palette:
            twin.palette_colors = layer.palette[1:] + layer.palette[:1]
        else:
            twin.palette_colors = effect_palette(section_palette, et, slot + 1, pal_offset)
    return twin


def _layer_plan(section: SectionPlan, available_groups: list[str]) -> tuple[list[tuple[str, list[str]]], dict[str, int]]:
    """Per stack layer: its canonical effect type and real groups; per target: how many xLights
    layers the stack occupies on it (a twin counts two)."""
    plan: list[tuple[str, list[str]]] = []
    depth: dict[str, int] = {}
    for layer in section.stack or []:
        et = canon_effect_type(layer.effect_type)
        groups = [g for g in (layer.groups or section.target_groups or [])
                  if not available_groups or g in available_groups]
        if not ranked_look_ids(et) or not groups:
            plan.append(("", []))
            continue
        plan.append((et, groups))
        for g in groups:
            depth[g] = depth.get(g, 0) + (2 if layer.twin else 1)
    return plan, depth


def expand_stack(section: SectionPlan, rhythm: dict, available_groups: list[str], *,
                 seed: int = 0, pal_offset: int = 0, beats_per_bar: int = 4) -> list[EffectInstruction]:
    """The section's stack as placeable rows, in the pipeline's LOGICAL layers: the brief lists
    layers bottom → top and so do the `layer` indices (0 = bottom, per TARGET; a twin sits one
    above its base). The emitter flips logical layers to xLights indices (0 = top) at placement
    — see `effect_emitter._xlights_layers`. Deterministic."""
    out: list[EffectInstruction] = []
    plan, _depth = _layer_plan(section, available_groups)
    used: dict[str, int] = {}                  # per TARGET: slots taken from the bottom so far
    for li, layer in enumerate(section.stack or []):
        et, groups = plan[li]
        if not et:
            continue
        looks = ranked_look_ids(et)
        look = layer.look_id if layer.look_id in looks else pick_look(et, seed + li)
        base: dict[str, str] = dict(layer.settings)
        if layer.blend:
            base["T_CHOICE_LayerMethod"] = layer.blend
        if layer.transform and layer.transform != "None":
            base["B_CHOICE_BufferTransform"] = layer.transform
        if layer.fade_in:
            base["T_TEXTCTRL_Fadein"] = f"{layer.fade_in:g}"
        if layer.fade_out:
            base["T_TEXTCTRL_Fadeout"] = f"{layer.fade_out:g}"
        if layer.brightness is not None:
            base.update(brightness_setting(layer.brightness * 100.0))
        celled = layer.cell_beats > 0
        recipe = CellRecipe(effect_type=et, alternation=layer.alternation or "all", groups=groups)
        for slot, start, end in _cells(section, rhythm, layer.cell_beats):
            targets = _slot_targets(recipe, slot, groups) if celled else groups
            bar = (slot * max(1, layer.cell_beats)) // max(1, beats_per_bar)
            for target in targets:
                cursor = used.get(target, 0)      # the next free logical layer on this target
                extra = dict(base)
                direction = layer.direction or ("ltr" if layer.twin == "counter" else "")
                if direction:
                    for key in SIGNED_DIRECTION_KEYS:            # a direction keeps the knob's pace
                        if key in layer.knobs and key not in extra:
                            extra[key] = layer.knobs[key]
                directed = apply_direction(extra, et, direction, bar) if direction else False
                colors = (list(layer.palette) if layer.palette
                          else effect_palette(section.palette, et, slot if celled else li, pal_offset))
                ins = EffectInstruction(
                    target=target, effect_type=et, look_id=look, knob_values=dict(layer.knobs),
                    palette_colors=colors, render_style=layer.render_style, extra_settings=extra,
                    layer=cursor, start_ms=start, end_ms=end, directed=directed, source="stack")
                out.append(ins)
                if layer.twin:
                    out.append(_twin_of(ins, layer, slot, bar, section_palette=section.palette,
                                        pal_offset=pal_offset))
        for target in groups:
            used[target] = used.get(target, 0) + (2 if layer.twin else 1)
    return out


def stack_has_role(section: SectionPlan, role: str) -> bool:
    return any(lyr.role == role for lyr in (getattr(section, "stack", None) or []))
