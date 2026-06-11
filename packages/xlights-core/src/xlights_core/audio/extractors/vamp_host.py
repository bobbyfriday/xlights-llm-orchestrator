"""VAMP plugin host: audio loading, plugin discovery, required-plugin check, and run.

The `vamp` module auto-discovers the system plugin dir (~/Library/Audio/Plug-Ins/Vamp).
Plugins are REQUIRED — a missing required plugin raises (no librosa fallback).
"""

from __future__ import annotations

from ..exceptions import AudioDependencyMissing, AudioPluginsMissing

# Plugin libraries we depend on (by library id, the part before ':').
REQUIRED_PLUGIN_LIBS = {"qm-vamp-plugins", "nnls-chroma", "segmentino"}

DEFAULT_SR = 44100


def _imports():
    try:
        import librosa
        import vamp
    except ImportError as exc:  # pragma: no cover - exercised when extra absent
        raise AudioDependencyMissing(
            "audio extra not installed: pip install 'xlights-core[audio]'"
        ) from exc
    return vamp, librosa


def list_plugins() -> list[str]:
    vamp, _ = _imports()
    return list(vamp.list_plugins())


def check_required_plugins() -> None:
    """Raise AudioPluginsMissing if any required plugin library is unavailable."""
    have = {p.split(":", 1)[0] for p in list_plugins()}
    missing = REQUIRED_PLUGIN_LIBS - have
    if missing:
        raise AudioPluginsMissing(missing)


def load_audio(path: str, sr: int = DEFAULT_SR):
    """Load audio as mono float32 + sample rate."""
    _, librosa = _imports()
    y, sr = librosa.load(path, sr=sr, mono=True)
    return y, sr


def run(key: str, output: str, y, sr: int):
    """Run a VAMP plugin output; returns the `vamp.collect` result dict."""
    vamp, _ = _imports()
    return vamp.collect(y, sr, key, output=output)


def items(result: dict) -> list[dict]:
    """Normalize a collect() result to a list of feature dicts."""
    return list(result.get("list") or [])


def ts(item: dict) -> float:
    """Coerce a feature timestamp to float seconds."""
    return float(item["timestamp"])
