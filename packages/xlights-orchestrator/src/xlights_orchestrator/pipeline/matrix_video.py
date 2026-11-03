"""Place the song's film on its video matrix as one full-length xLights **Video** effect.

Opt-in per song: `<song dir>/matrix_video.json` names the matrix model and the rendered mp4
(`{"target": "Panel Matrix", "file": "/Users/me/xlights/song_matrix.mp4"}`). The file must sit
where the sandboxed xLights can read it (the show folder). Video is asset-bound, so the emitter
places it from the explicit settings built here, not the preset library. The target is a MODEL,
normally one that layout_overrides.json `exclude`s from every SEM_ group so no light effect paints
over the film.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from xlights_core.knowledge.direct_settings import serialize_settings

from ..show_plan import EffectInstruction

log = logging.getLogger(__name__)

MATRIX_VIDEO_NAME = "matrix_video.json"


def build_video_settings(file: str) -> str:
    """The Video effect settings string (the keys xLights writes for a plain full-frame clip)."""
    if "," in file or "=" in file:
        raise ValueError(f"video path may not contain ',' or '=': {file!r}")
    return serialize_settings([
        ("E_CHECKBOX_SynchroniseWithAudio", "0"),
        ("E_CHECKBOX_Video_AspectRatio", "0"),
        ("E_CHECKBOX_Video_TransparentBlack", "0"),
        ("E_CHOICE_Video_DurationTreatment", "Normal"),
        ("E_FILEPICKERCTRL_Video_Filename", file),
        ("E_TEXTCTRL_Video_CropBottom", "0"),
        ("E_TEXTCTRL_Video_CropLeft", "0"),
        ("E_TEXTCTRL_Video_CropRight", "100"),
        ("E_TEXTCTRL_Video_CropTop", "100"),
        ("E_TEXTCTRL_Video_Starttime", "0.00"),
        ("E_TEXTCTRL_Video_TransparentBlack", "0"),
    ])


def place_matrix_video(song_dir: str | Path, duration_ms: int) -> list[EffectInstruction]:
    """One Video instruction spanning the song, or [] when the song has no matrix_video.json."""
    p = Path(song_dir) / MATRIX_VIDEO_NAME
    if not p.exists():
        return []
    spec = json.loads(p.read_text())
    target, file = spec.get("target", ""), spec.get("file", "")
    if not target or not file:
        log.warning("%s needs both 'target' and 'file'; no video placed", MATRIX_VIDEO_NAME)
        return []
    if not Path(file).exists():
        log.warning("%s: %s does not exist; no video placed", MATRIX_VIDEO_NAME, file)
        return []
    return [EffectInstruction(target=target, effect_type="Video", look_id="",
                              direct_settings=build_video_settings(file),
                              start_ms=0, end_ms=int(duration_ms))]
