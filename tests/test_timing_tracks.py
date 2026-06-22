"""Tests for reference timing tracks (builders + offline .xsq patcher)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from types import SimpleNamespace

from xlights_orchestrator.pipeline import timing as T


def _stem(name, onsets, energy=1.0):
    arc = [SimpleNamespace(time=0.0, rms=energy), SimpleNamespace(time=1.0, rms=energy)]
    return SimpleNamespace(stem=name, onsets=onsets, energy_arc=arc)


def _sa(*, beats=None, stems=None, chords=None, lyrics=None, duration_s=60.0):
    # stems = {name: (onsets, energy)} or {name: onsets}
    feats = []
    for k, v in (stems or {}).items():
        onsets, energy = v if isinstance(v, tuple) else (v, 1.0)
        feats.append(_stem(k, onsets, energy))
    return SimpleNamespace(
        beats=[SimpleNamespace(time=t) for t in (beats or [])],
        stems=feats,
        chords=[SimpleNamespace(time=t, label=l) for t, l in (chords or [])],
        lyrics=lyrics, duration_s=duration_s)


def _brief(sections):
    return SimpleNamespace(sections=[SimpleNamespace(label=l, start_ms=s, end_ms=e)
                                     for l, s, e in sections])


# -- builders -----------------------------------------------------------------

def test_section_beat_bar_tracks():
    sa = _sa(beats=[i * 0.5 for i in range(8)])      # 8 beats at 0,0.5,1.0,...
    brief = _brief([("intro", 0, 2000), ("verse", 2000, 4000)])
    tracks = {t.name: t for t in T.build_timing_tracks(sa, brief)}
    assert tracks["Sections"].marks[0].label == "intro"
    beat = tracks["Beats"]
    assert [m.label for m in beat.marks[:5]] == ["1", "2", "3", "4", "1"]   # beat-in-bar cycles
    assert len(tracks["Bars"].marks) == 2            # 8 beats / 4 = 2 bars


def test_section_falls_back_to_index_labels():
    sa = _sa(beats=[0.0, 0.5])
    plan = [SimpleNamespace(start_ms=0, end_ms=1000), SimpleNamespace(start_ms=1000, end_ms=2000)]
    tracks = {t.name: t for t in T.build_timing_tracks(sa, None, fallback_sections=plan)}
    assert [m.label for m in tracks["Sections"].marks] == ["Section 1", "Section 2"]


def test_onset_tracks_selective_exclude_other_and_silent_vocals():
    sa = _sa(beats=[0.0], stems={
        "drums": ([0.1, 0.2, 0.3], 0.5), "guitar": ([0.15, 0.25], 0.6),
        "bass": ([0.2, 0.4], 0.3), "other": ([0.1] * 50, 0.9),    # other excluded (catch-all)
        "vocals": ([0.1] * 80, 0.001)})                           # onset-noisy but SILENT → dropped by energy
    names = {t.name for t in T.build_timing_tracks(sa, None)}
    assert "Onsets (drums)" in names and "Onsets (guitar)" in names
    assert "Onsets (other)" not in names and "Onsets (vocals)" not in names   # both excluded
    assert len([n for n in names if n.startswith("Onsets")]) <= T.MAX_ONSET_STEMS


def test_chords_and_lyrics_conditional():
    instrumental = _sa(beats=[0.0], chords=[(0.0, "C"), (2.0, "G")])
    names = {t.name for t in T.build_timing_tracks(instrumental, None)}
    assert "Chords" in names and "Lyrics" not in names       # chords present, no lyrics
    vocal = _sa(beats=[0.0], lyrics={"lines": [{"text": "hi", "start": 1.0, "end": 2.0}]})
    assert "Lyrics" in {t.name for t in T.build_timing_tracks(vocal, None)}


def test_last_mark_clamped():
    sa = _sa(beats=[0.0, 1.0], duration_s=100.0)     # 2nd beat would tile to 100s without clamp
    beat = {t.name: t for t in T.build_timing_tracks(sa, None)}["Beats"]
    assert beat.marks[-1].end_ms - beat.marks[-1].start_ms <= T.LAST_MARK_MS


# -- patcher ------------------------------------------------------------------

_XSQ = ('<?xml version="1.0" encoding="UTF-8"?>\n<xsequence>'
        '<head><sequenceType>Animation</sequenceType></head>'
        '<DisplayElements><Element type="model" name="G1"/></DisplayElements>'
        '<ElementEffects><Element type="model" name="G1"><EffectLayer/></Element></ElementEffects>'
        '</xsequence>')


def test_patch_injects_into_both_sections(tmp_path):
    f = tmp_path / "s.xsq"; f.write_text(_XSQ)
    track = T.TimingTrack("Beats", [T.TimingMark("1", 0, 500), T.TimingMark("2", 500, 1000)])
    assert T.patch_xsq_timing_tracks(f, [track]) is True
    root = ET.parse(f).getroot()                     # re-parses → still valid XML
    de = [e.get("name") for e in root.find("DisplayElements") if e.get("type") == "timing"]
    ee = [e for e in root.find("ElementEffects") if e.get("type") == "timing"]
    assert de == ["Beats"] and len(ee) == 1
    marks = ee[0].find("EffectLayer").findall("Effect")
    assert [(m.get("label"), m.get("startTime"), m.get("endTime")) for m in marks] == \
           [("1", "0", "500"), ("2", "500", "1000")]


def test_patch_best_effort_on_bad_path_leaves_file(tmp_path):
    assert T.patch_xsq_timing_tracks(tmp_path / "missing.xsq", [T.TimingTrack("X", [T.TimingMark("", 0, 1)])]) is False


def test_patch_no_tracks_is_noop(tmp_path):
    f = tmp_path / "s.xsq"; f.write_text(_XSQ)
    assert T.patch_xsq_timing_tracks(f, []) is False
    assert f.read_text() == _XSQ                      # untouched


# -- overall-onset fallback (no stems) ----------------------------------------

def test_overall_onset_fallback_when_no_stems():
    sa = _sa(beats=[0.0, 0.5], stems={}, duration_s=10.0)
    sa = SimpleNamespace(**{**sa.__dict__, "onsets": [0.1, 0.4, 0.9, 1.5]})
    tracks = {t.name: t for t in T.build_timing_tracks(sa, _brief([("A", 0, 10000)]))}
    assert "Onsets" in tracks                                   # whole-mix fallback present
    assert len(tracks["Onsets"].marks) >= 3
    assert not any(n.startswith("Onsets (") for n in tracks)    # no per-stem tracks (no stems)


def test_per_stem_onsets_preferred_over_fallback():
    sa = _sa(beats=[0.0, 0.5], stems={"drums": ([0.1, 0.6, 1.1], 1.0)}, duration_s=10.0)
    sa = SimpleNamespace(**{**sa.__dict__, "onsets": [0.1, 0.4, 0.9]})
    names = {t.name for t in T.build_timing_tracks(sa, _brief([("A", 0, 10000)]))}
    assert "Onsets (drums)" in names and "Onsets" not in names  # stems win; no redundant fallback
