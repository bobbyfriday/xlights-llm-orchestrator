"""Apply EffectInstruction[] to a fresh xLights sequence — safe, additive, groups-only."""

from __future__ import annotations

import asyncio
from typing import Any

from xlights_core import XLightsClient, XLightsResponseError, XLightsTargetMissing
from xlights_core.editing import CleanSlateRequired, PresetPlacementError, place_preset
from xlights_core.knowledge.validators import KnobValueError

from .pipeline.render_style import resolve_buffer_style

from .show_plan import EffectInstruction

_SKIPPABLE = (PresetPlacementError, XLightsTargetMissing, ValueError, KnobValueError, KeyError)


def _free_layer(occ: dict, target: str, start: int, end: int, start_layer: int) -> int:
    """Find a layer on `target` whose time range doesn't overlap an existing effect."""
    layer = max(0, start_layer)
    while any(not (end <= s or start >= e) for s, e in occ.get((target, layer), [])):
        layer += 1
    return layer


async def apply_instructions(
    client: XLightsClient,
    instructions: list[EffectInstruction],
    *,
    duration_secs: int,
    settle_secs: float = 0.6,
) -> dict[str, Any]:
    """Create a clean-slate ANIMATION sequence (replacing any open one) and additively place
    the instructions. Audio is NOT attached here — `newSequence(mediaFile)` crashes xLights
    (LoadAudioData modal); the song is attached by an offline `.xsq` patch at finalize instead.
    """
    # Clean slate: explicitly close any open sequence FIRST (quiet+force discards silently).
    # newSequence(force=True) alone is NOT enough — with unsaved changes open it pops a
    # "save changes?" modal that hangs the call. close-then-create is the proven path.
    try:
        await client.close_sequence(force=True, quiet=True)
    except XLightsResponseError:
        pass  # nothing open / already closed
    try:
        await client.new_sequence(duration_secs=duration_secs, frame_ms=50, force=True)
    except XLightsResponseError as exc:
        if "already open" in (exc.message or "").lower():
            raise CleanSlateRequired(
                "a sequence is open in xLights; close it before generating"
            ) from exc
        raise

    await asyncio.sleep(settle_secs)  # let sequence elements populate (racy)

    occupancy: dict[tuple[str, int], list[tuple[int, int]]] = {}
    placed: list[dict] = []
    skipped: list[dict] = []

    for ins in instructions:
        layer = _free_layer(occupancy, ins.target, ins.start_ms, ins.end_ms, ins.layer)
        # LLM's render style if valid, else a fallback — never the sparse unset default.
        extra = dict(ins.extra_settings)
        extra["B_CHOICE_BufferStyle"] = resolve_buffer_style(ins.render_style, ins.effect_type)
        try:
            await place_preset(
                client, ins.target, ins.effect_type, ins.look_id,
                knob_values=ins.knob_values or None, palette_id=ins.palette_id,
                palette_colors=ins.palette_colors or None,
                extra_settings=extra,
                layer=layer, start_ms=ins.start_ms, end_ms=ins.end_ms,
            )
            occupancy.setdefault((ins.target, layer), []).append((ins.start_ms, ins.end_ms))
            placed.append({"target": ins.target, "effect": ins.effect_type,
                           "look": ins.look_id, "layer": layer,
                           "start_ms": ins.start_ms, "end_ms": ins.end_ms,
                           "section_index": ins.section_index})
        except _SKIPPABLE as exc:
            skipped.append({"target": ins.target, "effect": ins.effect_type,
                            "start_ms": ins.start_ms, "end_ms": ins.end_ms,
                            "section_index": ins.section_index,
                            "reason": f"{type(exc).__name__}: {exc}"})

    await client.render_all()
    return {"placed": placed, "skipped": skipped, "rendered": True}
