"""xlights-core: async client and typed models for the xLights automation REST API."""

from __future__ import annotations

from .client import XLightsClient
from .config import DEFAULT_BASE_URL, get_base_url
from .exceptions import (
    XLightsConnectionError,
    XLightsError,
    XLightsNotImplemented,
    XLightsResponseError,
    XLightsTargetMissing,
    XLightsTimeout,
    XLightsTransportError,
    XLightsUnsavedChanges,
)
from .models import Controller, Model
from .retry import with_retry, xlights_transient

__all__ = [
    "XLightsClient",
    "DEFAULT_BASE_URL",
    "get_base_url",
    "XLightsError",
    "XLightsConnectionError",
    "XLightsTransportError",
    "XLightsTimeout",
    "XLightsNotImplemented",
    "XLightsResponseError",
    "XLightsTargetMissing",
    "XLightsUnsavedChanges",
    "Model",
    "Controller",
    "with_retry",
    "xlights_transient",
]
