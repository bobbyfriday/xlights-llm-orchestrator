"""Auto-place an xLights Faces effect on singing-face props so they lip-sync to the vocals.

Deterministic (not LLM-driven): for each face prop in the layout, one `Faces` effect spanning the
vocal region, reading the phoneme timing track the pipeline writes (see `timing._phoneme_track`). The
face rests during instrumental passages natively (`SuppressWhenNotSinging`). `Faces` is asset-bound,
so the emitter places it from these explicit settings, not the preset library.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from ..show_plan import EffectInstruction
from .timing import _timed_words

log = logging.getLogger(__name__)

FACES_TIMING_TRACK = "Faces"          # MUST match timing._phoneme_track's track name
_IMAGE_FACE_TYPES = {"Matrix", "Rendered"}   # image-based defs; we drive the node defs


def singing_face_props(rgb_path: str | Path) -> list[tuple[str, str]]:
    """`(model_name, face_definition_name)` for every prop with a node-based face definition.

    A model that carries a `faceInfo` is a singing face; we pick its first node-based definition
    (skip image `Matrix`/`Rendered` defs) so the Faces effect drives the actual pixels.
    """
    out: list[tuple[str, str]] = []
    try:
        root = ET.parse(rgb_path).getroot()
    except Exception as exc:  # noqa: BLE001 — no/short layout → no faces, never fatal
        log.info("singing_face_props: could not read %s: %s", rgb_path, exc)
        return out
    for m in root.iter("model"):
        name = m.get("name") or ""
        defs = [f for f in m.findall("faceInfo") if (f.get("Type") or "") not in _IMAGE_FACE_TYPES]
        if name and defs:
            out.append((name, defs[0].get("Name") or "Default"))
    return out


def _faces_settings(face_def: str, track: str) -> dict[str, str]:
    return {
        "E_CHOICE_Faces_Phoneme": "(Auto)",                  # read phonemes from the timing track
        "E_CHOICE_Faces_TimingTrack": track,
        "E_CHOICE_Faces_FaceDefinition": face_def,
        "E_CHOICE_Faces_Eyes": "Auto",                       # natural blinking
        "E_CHECKBOX_Faces_SuppressWhenNotSinging": "1",      # rest during instrumental passages
        "E_CHECKBOX_Faces_Outline": "0",
    }


def place_faces(sa, rgb_path: str | Path, *, track: str = FACES_TIMING_TRACK) -> list[EffectInstruction]:
    """One Faces `EffectInstruction` per singing-face prop, spanning the vocal region.

    Empty when the song has no timed lyric words or the layout has no usable face prop.
    """
    words = _timed_words(getattr(sa, "lyrics", None)) if getattr(sa, "lyrics", None) else []
    faces = singing_face_props(rgb_path) if words else []
    if not words or not faces:
        return []
    start_ms, end_ms = words[0][1], max(e for _, _, e in words)
    out: list[EffectInstruction] = []
    for model, face_def in faces:
        out.append(EffectInstruction(
            target=model, effect_type="Faces", look_id="",
            start_ms=start_ms, end_ms=end_ms,
            extra_settings=_faces_settings(face_def, track), on_top=True))
    log.info("singing faces: placed %d Faces effect(s) [%d-%dms] on %s",
             len(out), start_ms, end_ms, ", ".join(m for m, _ in faces))
    return out
