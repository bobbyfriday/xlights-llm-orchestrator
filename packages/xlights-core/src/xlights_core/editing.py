"""Write-side helpers: place a preset, and validate a preset against live xLights.

These bridge the low-level :class:`XLightsClient` write methods and the
:mod:`xlights_core.knowledge` preset library.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .client import XLightsClient
from .exceptions import XLightsResponseError, XLightsTargetMissing
from .knowledge.colors import palette_from_colors
from .knowledge.preset_library import PresetLibrary, get_library


class PresetPlacementError(Exception):
    """xLights accepted the request but did not add the effect (worked=false)."""


class CleanSlateRequired(Exception):
    """A user sequence is open; validation refuses to discard it."""


async def place_preset(
    client: XLightsClient,
    target: str,
    effect_type: str,
    look_id: str,
    *,
    knob_values: dict[str, str] | None = None,
    palette_id: str | None = None,
    palette_colors: list[str] | None = None,
    extra_settings: dict[str, str] | None = None,
    layer: int = 0,
    start_ms: int,
    end_ms: int,
    library: PresetLibrary | None = None,
) -> str:
    """Assemble a preset and place it. Returns the assembled settings string.

    Raises on bad knob values (KnobValueError), unknown layout target (ValueError),
    bad timing (ValueError), missing sequence element (XLightsTargetMissing), or a
    placement that xLights didn't accept (PresetPlacementError).
    """
    lib = library or get_library()
    look = lib.get_look(effect_type, look_id)
    # Prefer the brief's realized colors; fall back cleanly to a mined palette so placement
    # never breaks if the colors can't be realized.
    palette = palette_from_colors(palette_colors) if palette_colors else None
    if not palette:
        palette = lib.get_palette(palette_id).palette_string if palette_id else ""
    settings = lib.assemble(look, knob_values)  # validates knobs per constraint
    if extra_settings:
        # OVERRIDE keys the look already carries (xLights honors the FIRST occurrence of a
        # duplicate key, so blind-append loses to the frozen base); append the rest.
        # Values may contain '|' (value curves) but never ',' — splitting on ',' is safe.
        pairs = [p for p in settings.split(",") if p]
        remaining = dict(extra_settings)
        for i, p in enumerate(pairs):
            k = p.split("=", 1)[0]
            if k in remaining:
                pairs[i] = f"{k}={remaining.pop(k)}"
        pairs += [f"{k}={v}" for k, v in remaining.items()]
        settings = ",".join(pairs)

    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError(f"bad timing: start={start_ms} end={end_ms}")
    if target not in set(await client.get_models()):
        raise ValueError(f"target {target!r} not in layout")

    worked = await client.add_effect(
        target, effect_type, settings, palette, layer=layer,
        start_ms=start_ms, end_ms=end_ms,
    )
    if not worked:
        raise PresetPlacementError(
            f"xLights did not add {effect_type}/{look_id} on {target!r} "
            f"({start_ms}-{end_ms}ms, layer {layer}) — overlap or unusable effect/layer"
        )
    return settings


async def validate_preset(
    client: XLightsClient,
    effect_type: str,
    look_id: str,
    *,
    knob_values: dict[str, str] | None = None,
    palette_id: str | None = None,
    target: str | None = None,
    duration_secs: int = 10,
    window_ms: int = 2000,
    settle_secs: float = 0.5,
    max_target_tries: int = 12,
    library: PresetLibrary | None = None,
) -> dict[str, Any]:
    """Validate a preset on a disposable scratch sequence; never touch user work.

    Returns ``{accepted, worked, rendered, target, reason}``. Requires that no user
    sequence is open (refuses rather than forcing). A fresh sequence only contains a
    subset of layout models as *elements*, and they populate slightly after creation —
    so we settle briefly, and when no explicit target is given we pick the first model
    that is actually an element of the scratch sequence.
    """
    # Clean slate: a non-forced new_sequence fails with "already open" if one is open.
    try:
        await client.new_sequence(duration_secs=duration_secs, frame_ms=50)
    except XLightsResponseError as exc:
        if "already open" in (exc.message or "").lower():
            raise CleanSlateRequired(
                "a sequence is open in xLights; close it before validating presets"
            ) from exc
        raise

    result: dict[str, Any] = {
        "accepted": False, "worked": False, "rendered": False,
        "target": target, "reason": None,
    }
    try:
        await asyncio.sleep(settle_secs)  # let sequence elements populate

        if target is not None:
            candidates = [target]
        else:
            candidates = (await client.get_model_names())[:max_target_tries]
        if not candidates:
            result["reason"] = "no usable target model in layout"
            return result

        last_missing: str | None = None
        for tgt in candidates:
            try:
                await place_preset(
                    client, tgt, effect_type, look_id,
                    knob_values=knob_values, palette_id=palette_id,
                    start_ms=0, end_ms=window_ms, library=library,
                )
                result["worked"] = True
                result["target"] = tgt
                break
            except XLightsTargetMissing as exc:
                last_missing = exc.message  # not an element of this scratch seq; try next
                continue
            except PresetPlacementError as exc:
                result["target"] = tgt
                result["reason"] = str(exc)
                return result
        else:
            result["reason"] = f"no target was an element of the scratch sequence ({last_missing})"
            return result

        await client.render_all()
        result["rendered"] = True
        result["accepted"] = True
        return result
    finally:
        # Discard the scratch (its own changes are disposable).
        await client.close_sequence(force=True, quiet=True)
