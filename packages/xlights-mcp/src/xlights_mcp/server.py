"""MCP server exposing the xLights automation API as tools.

Reads (models, controllers, effects, layout) plus the write path (new/open/save/close
sequence, addEffect, render) — mutations are serialized by the shared client's write lock.
A single shared :class:`XLightsClient` is created at startup and closed on shutdown.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from mcp.server.fastmcp import Context, FastMCP

from xlights_core import XLightsClient
from xlights_core.editing import (
    CleanSlateRequired,
    PresetPlacementError,
    place_preset,
    validate_preset,
)
from xlights_core.exceptions import XLightsError
from xlights_core.knowledge.validators import KnobValueError

T = TypeVar("T")

# Errors that should surface to the MCP client as clean, typed tool errors.
_TOOL_ERRORS = (XLightsError, PresetPlacementError, CleanSlateRequired, KnobValueError,
                ValueError, KeyError)


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[dict[str, XLightsClient]]:
    client = XLightsClient()
    try:
        yield {"client": client}
    finally:
        await client.aclose()


mcp = FastMCP("xlights", lifespan=_lifespan)


def _client(ctx: Context) -> XLightsClient:
    return ctx.request_context.lifespan_context["client"]


async def _call(coro: Awaitable[T]) -> T:
    """Run a call, translating typed domain errors into clear tool errors."""
    try:
        return await coro
    except _TOOL_ERRORS as exc:
        # Surface the error type so the MCP client sees *which* failure occurred.
        raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc


@mcp.tool()
async def xl_get_version(ctx: Context) -> str:
    """Return the running xLights version string."""
    return await _call(_client(ctx).get_version())


@mcp.tool()
async def xl_get_show_folder(ctx: Context) -> str:
    """Return the path of the currently loaded xLights show folder."""
    return await _call(_client(ctx).get_show_folder())


@mcp.tool()
async def xl_get_models(ctx: Context) -> dict[str, list[str]]:
    """Return the show layout: model names and group names, split by kind."""
    client = _client(ctx)
    return {
        "models": await _call(client.get_model_names()),
        "groups": await _call(client.get_group_names()),
    }


@mcp.tool()
async def xl_get_model(name: str, ctx: Context) -> dict[str, Any]:
    """Return the full attributes of a single model by name."""
    model = await _call(_client(ctx).get_model(name))
    return model.model_dump()


@mcp.tool()
async def xl_get_controllers(ctx: Context) -> list[dict[str, Any]]:
    """Return the configured controllers."""
    controllers = await _call(_client(ctx).get_controllers())
    return [c.model_dump() for c in controllers]


# -- write tools (mutating) ---------------------------------------------------

@mcp.tool()
async def xl_new_sequence(
    ctx: Context,
    duration_secs: int,
    frame_ms: int = 50,
    media_file: str | None = None,
    force: bool = False,
) -> str:
    """Create a new sequence. force=True DISCARDS the currently open sequence (opt-in)."""
    await _call(_client(ctx).new_sequence(
        duration_secs=duration_secs, frame_ms=frame_ms, media_file=media_file, force=force))
    return "created"


@mcp.tool()
async def xl_open_sequence(name: str, ctx: Context) -> str:
    """Open an existing sequence by name/path."""
    await _call(_client(ctx).open_sequence(name))
    return "opened"


@mcp.tool()
async def xl_save_sequence(ctx: Context, name: str | None = None) -> str:
    """Save the open sequence (name required if it has never been named)."""
    await _call(_client(ctx).save_sequence(name))
    return "saved"


@mcp.tool()
async def xl_close_sequence(ctx: Context, force: bool = False, quiet: bool = False) -> str:
    """Close the open sequence. Unsaved changes are refused unless force=True."""
    await _call(_client(ctx).close_sequence(force=force, quiet=quiet))
    return "closed"


@mcp.tool()
async def xl_render_all(ctx: Context) -> str:
    """Render the open sequence."""
    await _call(_client(ctx).render_all())
    return "rendered"


@mcp.tool()
async def xl_add_effect(
    ctx: Context,
    target: str,
    effect_type: str,
    look_id: str,
    start_ms: int,
    end_ms: int,
    knob_values: dict[str, str] | None = None,
    palette_id: str | None = None,
    layer: int = 0,
) -> dict[str, Any]:
    """Place a preset-backed effect: assemble settings from a look + knobs + palette."""
    settings = await _call(place_preset(
        _client(ctx), target, effect_type, look_id,
        knob_values=knob_values, palette_id=palette_id,
        layer=layer, start_ms=start_ms, end_ms=end_ms))
    return {"placed": True, "settings": settings}


@mcp.tool()
async def xl_add_effect_raw(
    ctx: Context,
    target: str,
    effect: str,
    start_ms: int,
    end_ms: int,
    settings: str = "",
    palette: str = "",
    layer: int = 0,
) -> dict[str, Any]:
    """Escape hatch: place an effect from raw settings/palette strings (gated)."""
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError(f"bad timing: start={start_ms} end={end_ms}")
    client = _client(ctx)
    if target not in set(await _call(client.get_models())):
        raise ValueError(f"target {target!r} not in layout")
    worked = await _call(client.add_effect(
        target, effect, settings, palette, layer=layer, start_ms=start_ms, end_ms=end_ms))
    if not worked:
        raise RuntimeError("PresetPlacementError: xLights did not add the effect")
    return {"placed": True}


@mcp.tool()
async def xl_validate_preset(
    ctx: Context,
    effect_type: str,
    look_id: str,
    knob_values: dict[str, str] | None = None,
    palette_id: str | None = None,
    target: str | None = None,
) -> dict[str, Any]:
    """Validate a preset on a disposable scratch sequence (requires no user seq open)."""
    return await _call(validate_preset(
        _client(ctx), effect_type, look_id,
        knob_values=knob_values, palette_id=palette_id, target=target))


# -- audio tools (lazy — only work when the [audio] extra is installed) --------

@mcp.tool()
async def xl_analyze_song(path: str) -> dict[str, Any]:
    """Analyze an audio file → SongAnalysis (needs the [audio] extra + VAMP plugins)."""
    import anyio
    try:
        from xlights_core.audio import AudioAnalyzer
    except Exception as exc:  # noqa: BLE001 - surface a clear tool error
        raise RuntimeError(f"audio extra not installed: {exc}") from exc
    try:
        analysis = await anyio.to_thread.run_sync(lambda: AudioAnalyzer().analyze(path))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc
    return analysis.model_dump()


@mcp.tool()
async def xl_list_vamp_plugins() -> list[str]:
    """List discovered VAMP plugins (needs the [audio] extra)."""
    import anyio
    try:
        from xlights_core.audio.extractors.vamp_host import list_plugins
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"audio extra not installed: {exc}") from exc
    return await anyio.to_thread.run_sync(list_plugins)


def main() -> None:
    """Console entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
