"""Offline xLights preview renderer (no xLights): .fseq + layout → still/clip images.

Optional — requires the `[preview]` extra (numpy, zstandard, pillow) and, for clips,
the `ffmpeg` system binary. Ported from the proven xlight-autosequencer video pipeline.
"""

from __future__ import annotations

from .fseq import FseqHeader, load_fseq
from .layout import Controller, Model, model_world_pixels, parse_controllers, parse_models
from .render import PreviewRenderer

__all__ = [
    "PreviewRenderer",
    "load_fseq",
    "FseqHeader",
    "parse_controllers",
    "parse_models",
    "model_world_pixels",
    "Controller",
    "Model",
]
