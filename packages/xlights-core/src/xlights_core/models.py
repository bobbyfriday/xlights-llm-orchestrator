"""Typed, lenient models for xLights read responses.

xLights' JSON is broad and version-dependent, so these models allow (and retain)
unknown fields rather than failing. Only the fields we actively rely on are declared;
everything else is preserved as extras and reachable via ``model_dump()``.

Note: ``getModels`` returns a flat list of *name strings* (models and groups mixed),
so there is no ``Group`` body model here — group details, if needed, come from
``getModel`` on the group name, same shape as ``Model``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """A single xLights model's attributes, as returned by ``getModel``."""

    model_config = ConfigDict(extra="allow")

    name: str | None = None


class Controller(BaseModel):
    """A controller, as returned by ``getControllers``."""

    model_config = ConfigDict(extra="allow")

    name: str | None = None
