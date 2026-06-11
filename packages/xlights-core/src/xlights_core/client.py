"""Async, read-only client for the xLights automation REST API.

Transport (verified against xLights source ``xLightsAutomations.cpp``):
- Each command is ``GET /<cmd>?param=val`` (or ``POST /<cmd>`` with JSON, unused here).
- With ``Accept: application/json`` the body is ``{"<key>": <value>}`` — a quoted string
  for text results (``version``, ``folder``) or raw JSON for structured results
  (``models``, ``model``, ``controllers``).
- Errors use the HTTP status: ``504`` = not implemented, other non-200 (commonly ``503``)
  = operational error, with body ``{"msg": "..."}``.
"""

from __future__ import annotations

import asyncio
import urllib.parse
from typing import Any

import httpx

from .config import DEFAULT_TIMEOUT, get_base_url
from .exceptions import (
    XLightsConnectionError,
    XLightsNotImplemented,
    XLightsResponseError,
    XLightsTargetMissing,
    XLightsTimeout,
    XLightsUnsavedChanges,
)
from .models import Controller, Model

# render/check on a real (large) open sequence can take a while; the write path
# uses a more generous timeout than reads.
DEFAULT_WRITE_TIMEOUT = 300.0


class XLightsClient:
    """Read-only async client. Use as an async context manager or call ``aclose()``."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = (base_url or get_base_url()).rstrip("/")
        # An injected client (e.g. with a MockTransport in tests) is not owned/closed by us.
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        # Serializes all mutating ops — xLights has one shared open sequence.
        self._write_lock = asyncio.Lock()
        self._write_timeout = max(timeout, DEFAULT_WRITE_TIMEOUT)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "XLightsClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # -- transport ---------------------------------------------------------------

    async def _request(
        self,
        cmd: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        timeout: float | None = None,
    ) -> Any:
        kw: dict[str, Any] = {} if timeout is None else {"timeout": timeout}
        try:
            if method == "GET":
                # Encode spaces as %20, NOT '+': xLights does not decode '+' as a space, so
                # form-encoding silently corrupts spaced values ("Per Model Default" arrived as
                # "Per+Model+Default" → fell back to "Default"; "Rotate 180" stored as "Rotate+180").
                if params:
                    qs = urllib.parse.urlencode(
                        {k: str(v) for k, v in params.items()}, quote_via=urllib.parse.quote)
                    resp = await self._client.get(f"/{cmd}?{qs}", **kw)
                else:
                    resp = await self._client.get(f"/{cmd}", **kw)
            else:
                resp = await self._client.post(f"/{cmd}", json=params or {}, **kw)
        except httpx.TimeoutException as exc:  # includes connect/read timeouts
            raise XLightsTimeout(f"Request to {cmd!r} timed out") from exc
        except httpx.ConnectError as exc:
            raise XLightsConnectionError(
                f"Could not connect to xLights at {self.base_url}"
            ) from exc
        except httpx.HTTPError as exc:  # any other transport-level failure
            raise XLightsConnectionError(f"HTTP error talking to xLights: {exc}") from exc

        return self._handle(cmd, resp)

    def _handle(self, cmd: str, resp: httpx.Response) -> Any:
        try:
            data: Any = resp.json()
        except ValueError:
            data = None

        if resp.status_code == 200:
            return data

        message = None
        if isinstance(data, dict):
            message = data.get("msg") or data.get("message")
        message = message or (resp.text or "").strip() or f"HTTP {resp.status_code}"
        low = message.lower()

        # 504 is overloaded: "not implemented" vs closeSequence's "unsaved changes".
        if resp.status_code == 504:
            if "unsaved" in low:
                raise XLightsUnsavedChanges(status_code=504, message=message, command=cmd)
            raise XLightsNotImplemented(
                f"xLights command {cmd!r} is not implemented", command=cmd
            )
        # addEffect: target not an element of the open sequence.
        if resp.status_code == 503 and "target element" in low:
            raise XLightsTargetMissing(status_code=503, message=message, command=cmd)
        raise XLightsResponseError(
            status_code=resp.status_code, message=message, command=cmd
        )

    @staticmethod
    def _unwrap(data: Any, key: str) -> Any:
        """Return ``data[key]`` if wrapped, else ``data`` (tolerant of either shape)."""
        if isinstance(data, dict) and key in data:
            return data[key]
        return data

    # -- read commands -----------------------------------------------------------

    async def get_version(self) -> str:
        """Return the running xLights version string."""
        return str(self._unwrap(await self._request("getVersion"), "version") or "")

    async def get_show_folder(self) -> str:
        """Return the path of the currently loaded show folder."""
        return str(self._unwrap(await self._request("getShowFolder"), "folder") or "")

    async def get_models(
        self, *, include_models: bool = True, include_groups: bool = True
    ) -> list[str]:
        """Return model/group *names*. Filter via the include flags (uses query params).

        An empty layout returns ``[]`` (not an error).
        """
        params: dict[str, str] = {}
        if not include_models:
            params["models"] = "false"
        if not include_groups:
            params["groups"] = "false"
        names = self._unwrap(await self._request("getModels", params=params), "models")
        return list(names or [])

    async def get_model_names(self) -> list[str]:
        """Names of models only (no groups)."""
        return await self.get_models(include_groups=False)

    async def get_group_names(self) -> list[str]:
        """Names of groups only (no models)."""
        return await self.get_models(include_models=False)

    async def get_model(self, name: str) -> Model:
        """Return one model's full attributes. Unknown name -> ``XLightsResponseError``."""
        raw = self._unwrap(await self._request("getModel", params={"model": name}), "model")
        return Model.model_validate(raw or {})

    async def get_controllers(self) -> list[Controller]:
        """Return the configured controllers."""
        raw = self._unwrap(await self._request("getControllers"), "controllers") or []
        return [Controller.model_validate(c) for c in raw]

    # -- mutations (serialized through the write-lock) ----------------------------

    async def _mutate(self, cmd: str, params: dict[str, Any] | None = None) -> Any:
        async with self._write_lock:
            return await self._request(cmd, params=params, timeout=self._write_timeout)

    async def new_sequence(
        self,
        *,
        duration_secs: int,
        frame_ms: int = 50,
        media_file: str | None = None,
        view: str | None = None,
        force: bool = False,
    ) -> None:
        """Create a new sequence. ``force`` DISCARDS any open sequence — opt-in only."""
        params: dict[str, Any] = {"durationSecs": duration_secs, "frameMS": frame_ms}
        if media_file:
            params["mediaFile"] = media_file
        if view:
            params["view"] = view
        if force:
            params["force"] = "true"
        await self._mutate("newSequence", params)

    async def open_sequence(self, seq: str) -> None:
        """Open an existing sequence by name/path."""
        await self._mutate("openSequence", {"seq": seq})

    async def save_sequence(self, name: str | None = None) -> None:
        """Save the open sequence; ``name`` is required if it has never been named."""
        params = {"seq": name} if name else {}
        await self._mutate("saveSequence", params)

    async def close_sequence(self, *, force: bool = False, quiet: bool = False) -> None:
        """Close the open sequence. Unsaved changes raise XLightsUnsavedChanges unless force."""
        params: dict[str, Any] = {}
        if force:
            params["force"] = "true"
        if quiet:
            params["quiet"] = "true"
        await self._mutate("closeSequence", params)

    async def add_effect(
        self,
        target: str,
        effect: str,
        settings: str = "",
        palette: str = "",
        *,
        layer: int = 0,
        start_ms: int,
        end_ms: int,
    ) -> bool:
        """Place an effect; returns whether xLights actually added it (``worked``).

        HTTP 200 with ``worked=false`` is a failure (e.g. overlap/bad layer), not success.
        Raises XLightsTargetMissing if the target is not an element of the open sequence.
        """
        data = await self._mutate("addEffect", {
            "target": target, "effect": effect, "settings": settings, "palette": palette,
            "layer": layer, "startTime": start_ms, "endTime": end_ms,
        })
        worked = data.get("worked") if isinstance(data, dict) else None
        return str(worked).lower() == "true"

    async def get_open_sequence(self) -> dict:
        """Info about the open sequence ({seq, fullseq, media, ...}); {} if none open."""
        try:
            data = await self._request("getOpenSequence")
            return data if isinstance(data, dict) else {}
        except XLightsResponseError:
            return {}

    async def export_video_preview(self, filename: str) -> str | None:
        """Export the house-preview video (REQUIRES a media-attached sequence — exporting a
        media-less sequence crashes xLights with a bitrate-0 null-deref). Returns the output name."""
        data = await self._mutate("exportVideoPreview", {"filename": filename})
        return data.get("output") if isinstance(data, dict) else None

    async def render_all(self, *, highdef: bool = False) -> None:
        """Render the open sequence (requires one open)."""
        params = {"highdef": "true"} if highdef else {}
        await self._mutate("renderAll", params)
