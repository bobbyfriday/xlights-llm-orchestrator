"""Audio-analysis errors."""

from __future__ import annotations


class AudioError(Exception):
    """Base class for audio-analysis errors."""


class AudioPluginsMissing(AudioError):
    """One or more required VAMP plugins are not installed."""

    def __init__(self, missing: set[str]) -> None:
        self.missing = sorted(missing)
        super().__init__(
            "Required VAMP plugins not found: "
            + ", ".join(self.missing)
            + ". They ship with xLights; install them to ~/Library/Audio/Plug-Ins/Vamp."
        )


class AudioDependencyMissing(AudioError):
    """The optional audio stack (vamp/librosa) is not installed."""
