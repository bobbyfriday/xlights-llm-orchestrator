"""Typed error taxonomy for xLights automation calls.

Callers branch on the exception *type* to distinguish failure modes:

- ``XLightsConnectionError`` — nothing listening / network failure.
- ``XLightsTimeout``         — request did not complete in time.
- ``XLightsNotImplemented``  — xLights reported the command as unimplemented (HTTP 504).
- ``XLightsResponseError``   — any other operational error from xLights (e.g. HTTP 503
                               "Unknown model." / "No sequence open."); carries status + message.
"""

from __future__ import annotations


class XLightsError(Exception):
    """Base class for all xLights client errors."""


class XLightsConnectionError(XLightsError):
    """Could not reach an xLights automation endpoint."""


class XLightsTimeout(XLightsError):
    """A request to xLights timed out."""


class XLightsNotImplemented(XLightsError):
    """xLights reported the command as not implemented (HTTP 504)."""

    def __init__(self, message: str, *, command: str | None = None) -> None:
        super().__init__(message)
        self.command = command


class XLightsResponseError(XLightsError):
    """xLights returned an operational error status (non-200, non-504).

    ``status_code`` is xLights' generic operational code (commonly 503); the
    distinguishing detail is in ``message`` (e.g. "Unknown model.").
    """

    def __init__(self, *, status_code: int, message: str, command: str | None = None) -> None:
        super().__init__(f"xLights returned {status_code} for {command!r}: {message}"
                         if command else f"xLights returned {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.command = command


class XLightsTargetMissing(XLightsResponseError):
    """The target model/group is not an element of the open sequence (503)."""


class XLightsUnsavedChanges(XLightsResponseError):
    """A close was refused because the sequence has unsaved changes (504).

    Note: xLights overloads 504 for both "not implemented" and "unsaved changes";
    these are disambiguated by message.
    """
