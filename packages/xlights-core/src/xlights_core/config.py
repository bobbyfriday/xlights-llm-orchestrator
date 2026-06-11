"""Configuration for talking to the xLights automation API."""

from __future__ import annotations

import os

# xLights instance "A" listens here by default ("B" uses 49914).
DEFAULT_BASE_URL = "http://127.0.0.1:49913"

# Default per-request timeout (seconds). Reads are quick; renders are not (not used here).
DEFAULT_TIMEOUT = 30.0


def get_base_url() -> str:
    """Resolve the xLights endpoint from ``XLIGHTS_BASE_URL`` or the default."""
    return os.environ.get("XLIGHTS_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
