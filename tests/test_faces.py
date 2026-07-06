"""Singing-face detection + Faces effect placement + the asset-bound emitter path."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xlights_orchestrator.effect_emitter import apply_instructions
from xlights_orchestrator.pipeline.faces import place_faces, singing_face_props
from xlights_orchestrator.show_plan import EffectInstruction

_RGB = (
    "<xrgb><models>"
    '<model name="Face1" DisplayAs="Custom">'
    '<faceInfo Type="NodeRange" Name="Bulb"/><faceInfo Type="Matrix" Name="Matrix"/></model>'
    '<model name="ImgOnly"><faceInfo Type="Matrix" Name="Matrix"/></model>'
    '<model name="Plain"/>'
    "</models></xrgb>"
)

_LYRICS = {"lines": [{"text": "red go", "start": 4.0, "end": 5.0, "words": [
    {"word": "red", "start": 4.0, "end": 4.5},
    {"word": "go", "start": 4.6, "end": 5.0}]}]}


def run(c):
    return asyncio.run(c)


# -- detection ----------------------------------------------------------------

def test_singing_face_props_picks_node_def(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_RGB)
    assert singing_face_props(rgb) == [("Face1", "Bulb")]   # Matrix-only + plain models excluded


def test_singing_face_props_missing_file():
    assert singing_face_props("/no/such/rgb.xml") == []     # best-effort, never raises


# -- placement ----------------------------------------------------------------

def test_place_faces_builds_instruction(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_RGB)
    out = place_faces(SimpleNamespace(lyrics=_LYRICS), rgb)
    assert len(out) == 1
    f = out[0]
    assert f.target == "Face1" and f.effect_type == "Faces" and f.on_top
    assert (f.start_ms, f.end_ms) == (4000, 5000)           # first word start .. last word end
    assert f.extra_settings["E_CHOICE_Faces_FaceDefinition"] == "Bulb"
    assert f.extra_settings["E_CHOICE_Faces_TimingTrack"] == "Faces"
    assert f.extra_settings["E_CHOICE_Faces_Phoneme"] == "(Auto)"
    assert f.extra_settings["E_CHECKBOX_Faces_SuppressWhenNotSinging"] == "1"


def test_place_faces_none_without_lyrics(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_RGB)
    assert place_faces(SimpleNamespace(lyrics=None), rgb) == []


def test_place_faces_none_without_face_props(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text("<xrgb><models><model name='Plain'/></models></xrgb>")
    assert place_faces(SimpleNamespace(lyrics=_LYRICS), rgb) == []


# -- asset-bound emitter path -------------------------------------------------

class _FakeClient:
    def __init__(self, worked=True):
        self.worked, self.added = worked, []

    async def close_sequence(self, *, force=False, quiet=False):
        pass

    async def new_sequence(self, *, duration_secs, frame_ms, force, view=None):
        pass

    async def add_effect(self, target, effect, settings="", palette="", *, layer, start_ms, end_ms):
        self.added.append((target, effect, settings, layer, start_ms, end_ms))
        return self.worked

    async def render_all(self):
        pass


def _faces_ins():
    return EffectInstruction(
        target="Face1", effect_type="Faces", look_id="", start_ms=1000, end_ms=2000, on_top=True,
        extra_settings={"E_CHOICE_Faces_TimingTrack": "Faces", "E_CHOICE_Faces_Phoneme": "(Auto)"})


def test_emitter_places_faces_via_add_effect():
    fc = _FakeClient(worked=True)
    rep = run(apply_instructions(fc, [_faces_ins()], duration_secs=3, settle_secs=0))
    assert len(fc.added) == 1                                # placed via add_effect, not place_preset
    tgt, eff, settings, layer, s, e = fc.added[0]
    assert (tgt, eff, s, e) == ("Face1", "Faces", 1000, 2000)
    assert "E_CHOICE_Faces_TimingTrack=Faces" in settings
    assert rep["placed"] and rep["placed"][0]["effect"] == "Faces"


def test_emitter_faces_worked_false_is_skipped():
    fc = _FakeClient(worked=False)
    rep = run(apply_instructions(fc, [_faces_ins()], duration_secs=3, settle_secs=0))
    assert rep["placed"] == [] and rep["skipped"] and rep["skipped"][0]["effect"] == "Faces"
