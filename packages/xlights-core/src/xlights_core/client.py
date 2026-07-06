"""Async client for the xLights automation REST API — reads plus a serialized write path
(new/open/save/close sequence, addEffect, render).

Transport (verified against xLights source ``xLightsAutomations.cpp``):
- Each command is ``GET /<cmd>?param=val`` (xLights also accepts ``POST /<cmd>`` with
  JSON, unused here).
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
    XLightsTransportError,
    XLightsUnsavedChanges,
)
from .models import Controller, Model
from .retry import with_retry, xlights_transient

# render/check on a real (large) open sequence can take a while; the write path
# uses a more generous timeout than reads.
DEFAULT_WRITE_TIMEOUT = 300.0


def _mutation_transient(exc: BaseException) -> bool:
    """Mutation retry is connection-ONLY: only the provably-never-sent ``XLightsConnectionError``
    is retryable, and the ``XLightsTransportError`` subclass (sent, response lost) and
    ``XLightsTimeout`` are explicitly NOT — retrying either could double-apply a non-idempotent
    ``addEffect``.
    """
    return (isinstance(exc, XLightsConnectionError)
            and not isinstance(exc, XLightsTransportError))


class XLightsClient:
    """Async client (reads + write-locked mutations). Use as an async context manager
    or call ``aclose()``."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
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
        # Bounded transient-transport retry (0/1 disables — reproduces the pre-retry behavior).
        self._retry_attempts = retry_attempts

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
        timeout: float | None = None,
    ) -> Any:
        kw: dict[str, Any] = {} if timeout is None else {"timeout": timeout}
        try:
            # Encode spaces as %20, NOT '+': xLights does not decode '+' as a space, so
            # form-encoding silently corrupts spaced values ("Per Model Default" arrived as
            # "Per+Model+Default" → fell back to "Default"; "Rotate 180" stored as "Rotate+180").
            if params:
                qs = urllib.parse.urlencode(
                    {k: str(v) for k, v in params.items()}, quote_via=urllib.parse.quote)
                resp = await self._client.get(f"/{cmd}?{qs}", **kw)
            else:
                resp = await self._client.get(f"/{cmd}", **kw)
        except httpx.TimeoutException as exc:  # includes connect/read timeouts
            raise XLightsTimeout(f"Request to {cmd!r} timed out") from exc
        except httpx.ConnectError as exc:
            # Provably never sent — safe to retry even a non-idempotent mutation.
            raise XLightsConnectionError(
                f"Could not connect to xLights at {self.base_url}"
            ) from exc
        except httpx.HTTPError as exc:  # sent, but the response was lost (transport-level)
            raise XLightsTransportError(f"HTTP error talking to xLights: {exc}") from exc

        return self._handle(cmd, resp)

    async def _request_with_retry(
        self,
        cmd: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        *,
        retryable=xlights_transient,
    ) -> Any:
        """A ``_request`` wrapped in bounded transient-transport retry.

        Reads pass the default ``xlights_transient`` (connection error OR timeout). Mutations
        pass a connection-only predicate so a post-send timeout surfaces immediately (retrying
        an ``addEffect`` that may already have landed could double-place). The terminal failure
        keeps its original typed condition.
        """
        return await with_retry(
            lambda: self._request(cmd, params=params, timeout=timeout),
            retryable=retryable, attempts=self._retry_attempts, label=f"xlights:{cmd}",
        )

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
        return str(self._unwrap(await self._request_with_retry("getVersion"), "version") or "")

    async def get_show_folder(self) -> str:
        """Return the path of the currently loaded show folder."""
        return str(self._unwrap(await self._request_with_retry("getShowFolder"), "folder") or "")

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
        names = self._unwrap(await self._request_with_retry("getModels", params=params), "models")
        return list(names or [])

    async def get_model_names(self) -> list[str]:
        """Names of models only (no groups)."""
        return await self.get_models(include_groups=False)

    async def get_group_names(self) -> list[str]:
        """Names of groups only (no models)."""
        return await self.get_models(include_models=False)

    async def get_model(self, name: str) -> Model:
        """Return one model's full attributes. Unknown name -> ``XLightsResponseError``."""
        raw = self._unwrap(
            await self._request_with_retry("getModel", params={"model": name}), "model")
        return Model.model_validate(raw or {})

    async def get_controllers(self) -> list[Controller]:
        """Return the configured controllers."""
        raw = self._unwrap(await self._request_with_retry("getControllers"), "controllers") or []
        return [Controller.model_validate(c) for c in raw]

    # -- mutations (serialized through the write-lock) ----------------------------

    async def _mutate(self, cmd: str, params: dict[str, Any] | None = None,
                      *, retry: bool = True) -> Any:
        """Serialize a mutation on the write lock. Transient retry is **connection-only** and
        happens INSIDE the lock (holding it across the backoff), so ordering and the single
        open-sequence invariant are preserved — no other mutation can sneak a ``closeSequence``
        between a failed ``addEffect`` attempt and its retry. A post-send timeout surfaces
        immediately (retrying could double-apply). ``retry=False`` (renderAll/export) opts out:
        a timeout there means "still rendering", so re-issuing piles work on the app.
        """
        async with self._write_lock:
            if retry:
                # Connection-only: a plain XLightsConnectionError is "provably never sent";
                # XLightsTransportError (sent, response lost) and XLightsTimeout are NOT retried.
                return await self._request_with_retry(
                    cmd, params=params, timeout=self._write_timeout,
                    retryable=_mutation_transient)
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
            data = await self._request_with_retry("getOpenSequence")
            return data if isinstance(data, dict) else {}
        except XLightsResponseError as exc:
            # Only the "no sequence open" reply means an empty result; any other
            # operational error (busy, transient 503) must surface, not read as "none".
            if "no sequence" in (exc.message or "").lower():
                return {}
            raise

    async def export_video_preview(self, filename: str) -> str | None:
        """Export the house-preview video (REQUIRES a media-attached sequence — exporting a
        media-less sequence crashes xLights with a bitrate-0 null-deref). Returns the output name."""
        # No retry: a long-running export that times out is likely still running; re-issuing
        # would pile a second export on the app.
        data = await self._mutate("exportVideoPreview", {"filename": filename}, retry=False)
        return data.get("output") if isinstance(data, dict) else None

    async def render_all(self, *, highdef: bool = False) -> None:
        """Render the open sequence (requires one open)."""
        # No retry: a renderAll timeout means "still rendering", not a transport blip.
        params = {"highdef": "true"} if highdef else {}
        await self._mutate("renderAll", params, retry=False)
