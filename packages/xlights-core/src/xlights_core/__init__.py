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
    XLightsUnsavedChanges,
)
from .models import Controller, Model

__all__ = [
    "XLightsClient",
    "DEFAULT_BASE_URL",
    "get_base_url",
    "XLightsError",
    "XLightsConnectionError",
    "XLightsTimeout",
    "XLightsNotImplemented",
    "XLightsResponseError",
    "XLightsTargetMissing",
    "XLightsUnsavedChanges",
    "Model",
    "Controller",
]
