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
    assert (f.start_ms, f.end_ms) == (2500, 6500)           # the vocals, padded 1.5 s for the fade
    assert f.extra_settings["E_CHOICE_Faces_FaceDefinition"] == "Bulb"
    assert f.extra_settings["E_CHOICE_Faces_TimingTrack"] == "Faces"
    assert "E_CHOICE_Faces_Phoneme" not in f.extra_settings   # xLights reads the track only when unset
    assert f.extra_settings["E_SPINCTRL_Faces_LeadFrames"] == "30"     # no blinking in short pauses
    assert f.extra_settings["E_CHECKBOX_Faces_Fade"] == "1"
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


# -- opt-in image face on a matrix (matrix_face.json) ---------------------------

def test_matrix_face_opt_in_sings_an_image_face(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_RGB)
    (tmp_path / "matrix_face.json").write_text('{"target": "ImgOnly", "face": "matrix"}')
    out = place_faces(SimpleNamespace(lyrics=_LYRICS), rgb, song_dir=tmp_path)
    by = {f.target: f for f in out}
    assert set(by) == {"Face1", "ImgOnly"}                  # node face as before + the opt-in
    assert by["ImgOnly"].extra_settings["E_CHOICE_Faces_FaceDefinition"] == "Matrix"


def test_matrix_face_without_opt_in_skips_image_faces(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_RGB)
    out = place_faces(SimpleNamespace(lyrics=_LYRICS), rgb, song_dir=tmp_path)
    assert [f.target for f in out] == ["Face1"]


def test_matrix_face_unknown_face_or_model_places_nothing(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_RGB)
    for spec in ('{"target": "ImgOnly", "face": "Slimer"}', '{"target": "Nope", "face": "Matrix"}',
                 'not json'):
        (tmp_path / "matrix_face.json").write_text(spec)
        out = place_faces(SimpleNamespace(lyrics=_LYRICS), rgb, song_dir=tmp_path)
        assert [f.target for f in out] == ["Face1"]


_DUET_RGB = ("<xrgb><models><model name='Panel'>"
             "<faceInfo Type='Matrix' Name='Slimer'/><faceInfo Type='Matrix' Name='Logo'/>"
             "</model></models></xrgb>")


def _line(text, s, e):
    return {"text": text, "start": s, "end": e, "words": [{"word": text, "start": s, "end": e}]}


def test_hook_face_sings_the_repeated_lines(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_DUET_RGB)
    (tmp_path / "matrix_face.json").write_text(
        '{"target": "Panel", "face": "slimer", "hook_face": "logo"}')
    lyrics = {"lines": [_line("If there's something strange", 1.0, 3.0),
                        _line("Who you gonna call?", 3.5, 4.5),
                        _line("If there's something weird", 6.0, 8.0),
                        _line("Who you gonna call", 8.5, 9.5)]}     # punctuation ignored
    out = place_faces(SimpleNamespace(lyrics=lyrics), rgb, song_dir=tmp_path)
    spans = [(f.extra_settings["E_CHOICE_Faces_FaceDefinition"], f.start_ms, f.end_ms) for f in out]
    assert spans == [("Slimer", 0, 3500), ("Logo", 3500, 6000),
                     ("Slimer", 6000, 8500), ("Logo", 8500, 11000)]  # tiled; ends padded for the fade


def test_unknown_hook_face_leaves_every_line_to_the_main_face(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_DUET_RGB)
    (tmp_path / "matrix_face.json").write_text(
        '{"target": "Panel", "face": "Slimer", "hook_face": "Nope"}')
    out = place_faces(SimpleNamespace(lyrics=_LYRICS), rgb, song_dir=tmp_path)
    assert [(f.extra_settings["E_CHOICE_Faces_FaceDefinition"], f.start_ms, f.end_ms)
            for f in out] == [("Slimer", 2500, 6500)]


def test_a_line_carrying_a_hook_after_a_lead_in_is_still_the_hook(tmp_path):
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_DUET_RGB)
    (tmp_path / "matrix_face.json").write_text(
        '{"target": "Panel", "face": "Slimer", "hook_face": "Logo"}')
    lyrics = {"lines": [_line("Who you gonna call", 1.0, 2.0),
                        _line("A verse line here", 3.0, 4.0),
                        _line("Who you gonna call", 5.0, 6.0),
                        _line("Oh, who you gonna call", 7.0, 8.0)]}
    out = place_faces(SimpleNamespace(lyrics=lyrics), rgb, song_dir=tmp_path)
    assert [f.extra_settings["E_CHOICE_Faces_FaceDefinition"] for f in out] == ["Logo", "Slimer", "Logo"]


# -- a hand-made lyric track (faces.xtiming) ------------------------------------

_XT = """<?xml version="1.0"?><timings><timing name="x"><EffectLayer>
<Effect label="whole lyric" starttime="1000" endtime="9500"/></EffectLayer><EffectLayer>
<Effect label="WHO" starttime="1000" endtime="1200"/><Effect label="CALL" starttime="1200" endtime="1500"/>
<Effect label="BREATH*" starttime="1600" endtime="1650"/>
<Effect label="A" starttime="3000" endtime="3400"/><Effect label="VERSE" starttime="3400" endtime="3800"/>
<Effect label="WHO" starttime="6000" endtime="6200"/><Effect label="CALL" starttime="6200" endtime="6500"/>
</EffectLayer><EffectLayer>
<Effect label="etc" starttime="1000" endtime="1100.4"/><Effect label="U" starttime="1080" endtime="1200"/>
</EffectLayer></timing></timings>"""


def test_load_xtiming_rounds_and_trims_overlaps(tmp_path):
    from xlights_orchestrator.pipeline.timing import load_xtiming, xtiming_lines
    p = tmp_path / "faces.xtiming"; p.write_text(_XT)
    t = load_xtiming(p)
    assert t.name == "Faces" and len(t.layer_list()) == 3
    assert [(m.label, m.start_ms, m.end_ms) for m in t.layer_list()[2]] == [("etc", 1000, 1100), ("U", 1100, 1200)]
    assert xtiming_lines(t) == [("WHO CALL", 1000, 1500), ("A VERSE", 3000, 3800), ("WHO CALL", 6000, 6500)]


def test_hand_made_track_drives_the_duet_and_wins_at_finalize(tmp_path):
    from xlights_orchestrator.pipeline.timing import build_timing_tracks
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_DUET_RGB)
    (tmp_path / "faces.xtiming").write_text(_XT)
    (tmp_path / "matrix_face.json").write_text(
        '{"target": "Panel", "face": "Slimer", "hook_face": "Logo"}')
    out = place_faces(SimpleNamespace(lyrics=_LYRICS), rgb, song_dir=tmp_path)   # _LYRICS ignored
    assert [(f.extra_settings["E_CHOICE_Faces_FaceDefinition"], f.start_ms, f.end_ms) for f in out] == [
        ("Logo", 0, 3000), ("Slimer", 3000, 6000), ("Logo", 6000, 8000)]
    from xlights_orchestrator.pipeline.faces import song_faces_track
    sa = SimpleNamespace(lyrics=_LYRICS, duration_s=10, beats=[], onsets=[], chords=[], stems=[])
    tracks = build_timing_tracks(sa, faces_track=song_faces_track(tmp_path, sa)[0])
    faces = next(t for t in tracks if t.name == "Faces")
    assert faces.layer_list()[0][0].label == "whole lyric"


def test_shouted_answer_goes_to_the_hook_face_and_the_call_to_the_main_face(tmp_path):
    from xlights_orchestrator.pipeline.faces import song_faces_track
    rgb = tmp_path / "rgb.xml"; rgb.write_text(_DUET_RGB)
    (tmp_path / "faces.xtiming").write_text(_XT)
    (tmp_path / "matrix_face.json").write_text(
        '{"target": "Panel", "face": "Slimer", "hook_face": "Logo",'
        ' "shout": {"word": "Ghostbusters", "after": "call"}}')
    arc = [{"time": t / 10, "rms": 0.0} for t in range(0, 100)]
    arc[22]["rms"] = 0.9                         # a loud burst at 2.2 s, after the first "call"
    arc[70]["rms"] = 0.1                         # too quiet after the second: no answer
    sa = SimpleNamespace(lyrics=None, duration_s=10, stems=[{"stem": "vocals", "energy_arc": arc}])
    track, shouts = song_faces_track(tmp_path, sa)
    assert shouts == [(1600, 2800)]
    assert ("GHOSTBUSTERS", 1600, 2800) in [(m.label, m.start_ms, m.end_ms) for m in track.layer_list()[1]]
    assert any(1600 <= m.start_ms < 2800 for m in track.layer_list()[2])   # the mouth moves
    out = place_faces(sa, rgb, song_dir=tmp_path)
    assert [(f.extra_settings["E_CHOICE_Faces_FaceDefinition"], f.start_ms, f.end_ms) for f in out] == [
        ("Slimer", 0, 1600), ("Logo", 1600, 3000), ("Slimer", 3000, 6000), ("Logo", 6000, 8000)]


def test_shout_edges_come_from_the_fine_vocal_envelope():
    from xlights_orchestrator.pipeline.faces import shout_spans
    from xlights_orchestrator.pipeline.timing import TimingMark
    env = [0.0] * 200                            # 10 s at 50 ms
    for i in range(41, 45):                      # the tail of "call" (2.05-2.25 s): weaker
        env[i] = 0.3
    for a, b in ((50, 57), (59, 63), (65, 72)):  # "ghost - bus - ters" at 2.5-3.6 s
        for i in range(a, b):
            env[i] = 0.9
    words = [TimingMark("CALL", 1500, 2000), TimingMark("NEXT", 6000, 6500)]
    sa = SimpleNamespace(stems=[])
    assert shout_spans(sa, words, "call", envelope=env) == [(2500, 3600)]
