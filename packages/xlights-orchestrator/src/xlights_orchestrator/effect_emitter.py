"""Apply EffectInstruction[] to a fresh xLights sequence — safe, additive, groups-only."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from xlights_core import XLightsClient, XLightsResponseError, XLightsTargetMissing
from xlights_core.editing import CleanSlateRequired, PresetPlacementError, place_direct, place_preset
from xlights_core.knowledge.validators import KnobValueError

from .pipeline.render_style import resolve_buffer_style

from .show_plan import EffectInstruction

_log = logging.getLogger(__name__)

_SKIPPABLE = (PresetPlacementError, XLightsTargetMissing, ValueError, KnobValueError, KeyError,
              XLightsResponseError)
# Asset-bound effects carry their own model assets (face defs / pictures) and aren't in the mined
# preset library, so they're placed from explicit settings rather than a library Look.
_ASSET_BOUND = frozenset({"Faces"})
MAX_LAYERS = 6        # defensive ceiling — beyond this xLights refuses anyway (and catalog
                      # rule #10 caps rows at 4; generation trims to that BEFORE emitting)


def _free_layer(occ: dict, target: str, start: int, end: int, start_layer: int) -> int:
    """Find a layer on `target` whose time range doesn't overlap an existing effect."""
    layer = max(0, start_layer)
    while any(not (end <= s or start >= e) for s, e in occ.get((target, layer), [])):
        layer += 1
    return layer


def _top_layer(occ: dict, target: str, start: int, end: int) -> int:
    """The LOGICAL layer above every effect overlapping [start,end] on `target` (the pipeline's
    convention: 0 is the bottom, higher is on top), so an on_top accent sits above ALL
    overlappers — not just in the lowest free gap, which `_free_layer` would put it UNDER a
    longer spanning layer. `_xlights_layers` turns logical layers into xLights indices."""
    top = -1
    for (tg, layer), spans in occ.items():
        if tg == target and any(not (end <= s or start >= e) for s, e in spans):
            top = max(top, layer)
    return top + 1


def _logical_layers(instructions: list[EffectInstruction]) -> list[int | None]:
    """Each instruction's LOGICAL layer (0 = bottom, higher renders on top), assigned in list
    order by occupancy: an `on_top` row goes above every overlapper, any other row into the
    lowest free gap at or above its requested `layer`. `None` where the row would exceed
    `MAX_LAYERS` (the caller skips it). Pure; assumes every row places."""
    occ: dict[tuple[str, int], list[tuple[int, int]]] = {}
    out: list[int | None] = []
    for ins in instructions:
        if getattr(ins, "on_top", False):
            layer = _top_layer(occ, ins.target, ins.start_ms, ins.end_ms)
        else:
            layer = _free_layer(occ, ins.target, ins.start_ms, ins.end_ms, ins.layer)
            if layer >= MAX_LAYERS:
                out.append(None)
                continue
        occ.setdefault((ins.target, layer), []).append((ins.start_ms, ins.end_ms))
        out.append(layer)
    return out


def _xlights_layers(instructions: list[EffectInstruction], logical: list[int | None]) -> list[int | None]:
    """Logical layers → xLights layer indices. xLights numbers layers from the TOP: its layer 1
    (index 0 in `addEffect`) renders over index 1, and so on — verified live 2026-11-02 (red On
    at index 0 covers blue at index 1; a mask at index 3 does nothing to index 2), and it is how
    every community `.xsq` reads. So on each target the deepest logical layer becomes index 0 and
    the bottom (logical 0) the highest index; relative order is preserved for every row."""
    depth: dict[str, int] = {}
    for ins, lg in zip(instructions, logical):
        if lg is not None:
            depth[ins.target] = max(depth.get(ins.target, 0), lg)
    return [None if lg is None else depth[ins.target] - lg for ins, lg in zip(instructions, logical)]


def clamp_layer_budget(instructions: list[EffectInstruction], max_layers: int = 4
                       ) -> tuple[list[EffectInstruction], int]:
    """Enforce the catalog's layer ceiling (rule #10: ≤4 layers per row) BEFORE emitting:
    placements that would stack deeper than `max_layers` concurrent layers on a target are
    dropped, earliest-first wins (beds/washes/carriers come first in the stream by
    construction). Returns (kept, dropped_count) — deliberate trims, not placement skips."""
    occ: dict[tuple[str, int], list[tuple[int, int]]] = {}
    kept: list[EffectInstruction] = []
    dropped = 0
    # An authored stack row (`source == "stack"`) is the designer's decision: it claims its
    # layers before any synthesized row (accents, triggers, flashes) competes for them, so a
    # twin or an overlay is never the row that gets trimmed. Output order is preserved.
    order = sorted(range(len(instructions)),
                   key=lambda i: (0 if getattr(instructions[i], "source", "") == "stack" else 1, i))
    keep_idx: set[int] = set()
    for i in order:
        ins = instructions[i]
        if getattr(ins, "on_top", False):            # punch-through accents are never clamped
            keep_idx.add(i)
            continue
        layer = _free_layer(occ, ins.target, ins.start_ms, ins.end_ms, ins.layer)
        if layer >= max_layers:
            dropped += 1
            continue
        occ.setdefault((ins.target, layer), []).append((ins.start_ms, ins.end_ms))
        keep_idx.add(i)
    kept = [instructions[i] for i in range(len(instructions)) if i in keep_idx]
    return kept, dropped


def _outcome(index: int, ins: EffectInstruction, *, placed: bool, layer: int | None,
             reason: str = "") -> dict:
    """One `applied.json` outcome row: the instruction's index in the emitted list plus what
    happened to it (`placed`, the layer it landed on, or the skip `reason`)."""
    return {"index": index, "placed": placed, "reason": reason, "layer": layer,
            "target": ins.target, "effect": ins.effect_type, "section_index": ins.section_index,
            "start_ms": ins.start_ms, "end_ms": ins.end_ms}


async def apply_instructions(
    client: XLightsClient,
    instructions: list[EffectInstruction],
    *,
    duration_secs: int,
    settle_secs: float = 0.6,
    render: bool = True,
) -> dict[str, Any]:
    """Create a clean-slate ANIMATION sequence (replacing any open one) and additively place
    the instructions. Audio is NOT attached here — `newSequence(mediaFile)` crashes xLights
    (LoadAudioData modal); `xlo apply` saves, patches the `.xsq` to Media offline and reopens it.

    Returns `{placed, skipped, rendered, outcomes}`: `placed`/`skipped` are the per-placement
    rows callers have always read (now each carrying its `index` into `instructions`);
    `outcomes` is one row per instruction, in order, with `placed: bool` and the skip `reason`
    (the `_SKIPPABLE` exception message, or the layer-budget note) — what `xlo apply` writes to
    `applied.json`. `render=False` skips the trailing `renderAll` (the `xlo apply --render`
    switch; the default renders, as a plain emit always has).
    """
    # Clean slate: explicitly close any open sequence FIRST (quiet+force discards silently).
    # newSequence(force=True) alone is NOT enough — with unsaved changes open it pops a
    # "save changes?" modal that hangs the call. close-then-create is the proven path.
    try:
        await client.close_sequence(force=True, quiet=True)
    except XLightsResponseError:
        pass  # nothing open / already closed
    try:
        try:    # canonical render order when the SEM Master view is loaded (post-restart)
            await client.new_sequence(duration_secs=duration_secs, frame_ms=50, force=True,
                                      view="SEM Master")
        except Exception as exc:  # noqa: BLE001 — view not loaded yet → default view
            from .degradations import note
            note("emit:view", exc, stage="apply")
            await client.new_sequence(duration_secs=duration_secs, frame_ms=50, force=True)
    except XLightsResponseError as exc:
        if "already open" in (exc.message or "").lower():
            raise CleanSlateRequired(
                "a sequence is open in xLights; close it before generating"
            ) from exc
        raise

    await asyncio.sleep(settle_secs)  # let sequence elements populate (racy)

    # F-J batching seam: fetch the layout name set ONCE per emit and pass it to every placement,
    # instead of a get_models() round-trip per placement (~270/emit → one call). Best-effort — a
    # failure falls back to the per-call fetch inside place_preset/place_direct (known=None).
    known_targets: set[str] | None = None
    try:
        known_targets = set(await client.get_models())
    except Exception as exc:  # noqa: BLE001 — prefetch is an optimization; per-call fetch covers it
        _log.debug("emit: get_models prefetch failed, falling back to per-call fetch: %s", exc)
        known_targets = None

    placed: list[dict] = []
    skipped: list[dict] = []
    outcomes: list[dict] = []
    # Layers are decided for the whole list first (logical: beds at 0, on_top accents above every
    # overlapper), then flipped to xLights indices (0 = top) per target. The reported `layer` in
    # applied.json is the xLights index — what the sequencer grid shows.
    xl_layers = _xlights_layers(instructions, _logical_layers(instructions))

    for index, ins in enumerate(instructions):
        layer = xl_layers[index]
        if layer is None:
            reason = f"layer budget: would need more than {MAX_LAYERS} layers"
            skipped.append({"index": index, "target": ins.target, "effect": ins.effect_type,
                            "start_ms": ins.start_ms, "end_ms": ins.end_ms,
                            "section_index": ins.section_index, "reason": reason})
            outcomes.append(_outcome(index, ins, placed=False, layer=None, reason=reason))
            continue
        # Asset-bound effects (Faces): place from explicit settings, skip the preset library.
        if ins.effect_type in _ASSET_BOUND:
            settings = ",".join(f"{k}={v}" for k, v in ins.extra_settings.items())
            try:
                if not await client.add_effect(ins.target, ins.effect_type, settings,
                                               layer=layer, start_ms=ins.start_ms, end_ms=ins.end_ms):
                    raise PresetPlacementError("addEffect returned worked=false")
                placed.append({"index": index, "target": ins.target, "effect": ins.effect_type,
                               "look": "", "layer": layer, "start_ms": ins.start_ms,
                               "end_ms": ins.end_ms, "section_index": ins.section_index})
                outcomes.append(_outcome(index, ins, placed=True, layer=layer))
            except _SKIPPABLE as exc:
                reason = f"{type(exc).__name__}: {exc}"
                skipped.append({"index": index, "target": ins.target, "effect": ins.effect_type,
                                "start_ms": ins.start_ms, "end_ms": ins.end_ms,
                                "section_index": ins.section_index, "reason": reason})
                outcomes.append(_outcome(index, ins, placed=False, layer=None, reason=reason))
            continue

        # LLM's render style if valid, else a fallback — never the sparse unset default.
        extra = dict(ins.extra_settings)
        extra["B_CHOICE_BufferStyle"] = resolve_buffer_style(ins.render_style, ins.effect_type)
        try:
            if getattr(ins, "direct_settings", ""):
                # F-B asset-bound path: settings built in code (Text/Faces), catalog bypassed.
                # Same layer accounting + skip-on-failure; still carries the buffer-style key.
                await place_direct(
                    client, ins.target, ins.effect_type, ins.direct_settings,
                    palette_colors=ins.palette_colors or None,
                    extra_settings=extra,
                    layer=layer, start_ms=ins.start_ms, end_ms=ins.end_ms,
                    known_targets=known_targets,
                )
            else:
                await place_preset(
                    client, ins.target, ins.effect_type, ins.look_id,
                    knob_values=ins.knob_values or None, palette_id=ins.palette_id,
                    palette_colors=ins.palette_colors or None,
                    extra_settings=extra,
                    layer=layer, start_ms=ins.start_ms, end_ms=ins.end_ms,
                    known_targets=known_targets,
                )
            placed.append({"index": index, "target": ins.target, "effect": ins.effect_type,
                           "look": ins.look_id, "layer": layer,
                           "start_ms": ins.start_ms, "end_ms": ins.end_ms,
                           "section_index": ins.section_index})
            outcomes.append(_outcome(index, ins, placed=True, layer=layer))
        except _SKIPPABLE as exc:
            reason = f"{type(exc).__name__}: {exc}"
            skipped.append({"index": index, "target": ins.target, "effect": ins.effect_type,
                            "start_ms": ins.start_ms, "end_ms": ins.end_ms,
                            "section_index": ins.section_index, "reason": reason})
            outcomes.append(_outcome(index, ins, placed=False, layer=None, reason=reason))

    if render:
        await client.render_all()
    return {"placed": placed, "skipped": skipped, "rendered": bool(render), "outcomes": outcomes}
