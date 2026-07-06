"""Write-side helpers: place a preset, and validate a preset against live xLights.

These bridge the low-level :class:`XLightsClient` write methods and the
:mod:`xlights_core.knowledge` preset library.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .client import XLightsClient
from .exceptions import XLightsError, XLightsResponseError, XLightsTargetMissing
from .knowledge.colors import palette_from_colors
from .knowledge.preset_library import PresetLibrary, get_library
from .knowledge.settings import parse_settings, serialize_settings


# Settings keys REMOVED from current xLights but still carried by mined looks (authored in
# older versions). Stripped at assembly — they were already non-functional; shipping them only
# makes the editor log `ApplySetting: Unable to find` on every effect selection.
DROP_KEYS = {"E_CHECKBOX_Chase_3dFade1"}

log = logging.getLogger(__name__)


class PresetPlacementError(Exception):
    """xLights accepted the request but did not add the effect (worked=false)."""


class CleanSlateRequired(Exception):
    """A user sequence is open; validation refuses to discard it."""


def _merge_extra_settings(settings: str, extra: dict[str, str] | None) -> str:
    """Merge ``extra`` into a settings string: OVERRIDE keys the string already carries (xLights
    honors the FIRST occurrence of a duplicate key, so a blind append loses to the frozen base),
    then append the rest. Values may contain '|' (value curves) but never ',', so splitting on
    ',' is safe. Shared by the preset and direct placement paths."""
    if not extra:
        return settings
    pairs = [p for p in settings.split(",") if p]
    remaining = dict(extra)
    for i, p in enumerate(pairs):
        k = p.split("=", 1)[0]
        if k in remaining:
            pairs[i] = f"{k}={remaining.pop(k)}"
    pairs += [f"{k}={v}" for k, v in remaining.items()]
    return ",".join(pairs)


async def _check_timing_and_target(
    client: XLightsClient, target: str, start_ms: int, end_ms: int,
    known_targets: set[str] | None = None,
) -> None:
    """Shared placement guards: a valid window and a target that exists in the layout.

    ``known_targets`` (F-J batching seam) is a prefetched layout-name set — pass it to check
    against a set fetched ONCE per emit instead of a ``get_models()`` round-trip per placement
    (~270 placements/emit → one call). ``None`` keeps the per-call fetch (unchanged default)."""
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError(f"bad timing: start={start_ms} end={end_ms}")
    names = known_targets if known_targets is not None else set(await client.get_models())
    if target not in names:
        raise ValueError(f"target {target!r} not in layout")


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
    known_targets: set[str] | None = None,
) -> str:
    """Assemble a preset and place it. Returns the assembled settings string.

    Raises on bad knob values (KnobValueError), unknown layout target (ValueError),
    bad timing (ValueError), missing sequence element (XLightsTargetMissing), or a
    placement that xLights didn't accept (PresetPlacementError).

    ``known_targets`` (optional) is a prefetched layout-name set for the target check — pass it
    from a batching caller to avoid one ``get_models()`` round-trip per placement.
    """
    lib = library or get_library()
    look = lib.get_look(effect_type, look_id)
    # Prefer the brief's realized colors; fall back cleanly to a mined palette so placement
    # never breaks if the colors can't be realized.
    palette = palette_from_colors(palette_colors) if palette_colors else None
    if not palette:
        palette = lib.get_palette(palette_id).palette_string if palette_id else ""
    settings = lib.assemble(look, knob_values)  # validates knobs per constraint
    if DROP_KEYS:                               # stale keys current xLights no longer has
        settings = ",".join(p for p in settings.split(",")
                            if p and p.split("=", 1)[0] not in DROP_KEYS)
    settings = _merge_extra_settings(settings, extra_settings)

    await _check_timing_and_target(client, target, start_ms, end_ms, known_targets)

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


async def place_direct(
    client: XLightsClient,
    target: str,
    effect_type: str,
    settings: str,
    *,
    palette_colors: list[str] | None = None,
    extra_settings: dict[str, str] | None = None,
    layer: int = 0,
    start_ms: int,
    end_ms: int,
    known_targets: set[str] | None = None,
) -> str:
    """Place an **asset-bound** (code-templated) effect whose settings are built from scratch
    rather than assembled from the mined catalog — the sibling of :func:`place_preset` for the
    F-B `DIRECT_TYPES`. It skips catalog assembly but keeps every guard: syntactic round-trip
    validation of the settings string, the shared `extra_settings` first-occurrence-wins merge,
    `palette_from_colors`, the timing/target checks, and `PresetPlacementError` on `worked=false`.

    Returns the merged settings string actually sent to xLights. Raises ``ValueError`` on a
    non-round-tripping settings string or bad timing/target, ``PresetPlacementError`` if xLights
    did not add the effect.
    """
    # syntactic validation: a code-built template must survive a parse/serialize round-trip
    # (a stray comma/equals would have xLights mis-parse the string).
    if serialize_settings(parse_settings(settings)) != settings:
        raise ValueError(f"direct settings do not round-trip (unparseable): {settings!r}")
    merged = _merge_extra_settings(settings, extra_settings)
    palette = palette_from_colors(palette_colors) if palette_colors else ""

    await _check_timing_and_target(client, target, start_ms, end_ms, known_targets)

    worked = await client.add_effect(
        target, effect_type, merged, palette, layer=layer,
        start_ms=start_ms, end_ms=end_ms,
    )
    if not worked:
        raise PresetPlacementError(
            f"xLights did not add direct {effect_type} on {target!r} "
            f"({start_ms}-{end_ms}ms, layer {layer}) — overlap or unusable effect/layer"
        )
    return merged


async def validate_direct(
    client: XLightsClient,
    effect_type: str,
    settings: str,
    *,
    target: str | None = None,
    duration_secs: int = 10,
    window_ms: int = 2000,
    settle_secs: float = 0.5,
    max_target_tries: int = 12,
) -> dict[str, Any]:
    """Live-validate a code-templated direct settings string on a disposable scratch sequence —
    the runtime half of "valid by construction" for `DIRECT_TYPES`. Mirrors :func:`validate_preset`
    (clean slate → place the template → render → assert `worked` → discard). Marked ``live``;
    run once per template per xLights upgrade. Returns ``{accepted, worked, rendered, target,
    reason}`` and never touches user work (refuses if a sequence is open)."""
    try:
        await client.new_sequence(duration_secs=duration_secs, frame_ms=50)
    except XLightsResponseError as exc:
        if "already open" in (exc.message or "").lower():
            raise CleanSlateRequired(
                "a sequence is open in xLights; close it before validating direct settings"
            ) from exc
        raise

    result: dict[str, Any] = {
        "accepted": False, "worked": False, "rendered": False,
        "target": target, "reason": None,
    }
    try:
        await asyncio.sleep(settle_secs)  # let sequence elements populate
        candidates = [target] if target is not None else (await client.get_model_names())[:max_target_tries]
        if not candidates:
            result["reason"] = "no usable target model in layout"
            return result

        last_missing: str | None = None
        for tgt in candidates:
            try:
                await place_direct(client, tgt, effect_type, settings, start_ms=0, end_ms=window_ms)
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
        try:
            await client.close_sequence(force=True, quiet=True)
        except XLightsError as exc:
            log.warning("could not close scratch sequence: %s", exc)


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
        # Discard the scratch (its own changes are disposable). Best-effort: a failure
        # closing must not mask the validation result or the body's real exception.
        try:
            await client.close_sequence(force=True, quiet=True)
        except XLightsError as exc:
            log.warning("could not close scratch sequence: %s", exc)
