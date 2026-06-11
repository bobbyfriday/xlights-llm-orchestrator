"""xlights-mcp: an MCP server exposing xLights read operations as tools."""

from __future__ import annotations

from .server import main, mcp

__all__ = ["main", "mcp"]
