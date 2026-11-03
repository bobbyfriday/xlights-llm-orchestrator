"""The song's film is placed as one full-length Video effect on its matrix model."""

from __future__ import annotations

import json

from xlights_orchestrator.pipeline.matrix_video import build_video_settings, place_matrix_video


def test_no_spec_places_nothing(tmp_path):
    assert place_matrix_video(tmp_path, 60_000) == []


def test_spec_places_one_full_length_video(tmp_path):
    mp4 = tmp_path / "film.mp4"
    mp4.write_bytes(b"\0")
    (tmp_path / "matrix_video.json").write_text(json.dumps({"target": "Panel Matrix", "file": str(mp4)}))
    (ins,) = place_matrix_video(tmp_path, 431_100)
    assert (ins.target, ins.effect_type, ins.start_ms, ins.end_ms) == ("Panel Matrix", "Video", 0, 431_100)
    assert f"E_FILEPICKERCTRL_Video_Filename={mp4}" in ins.direct_settings


def test_missing_file_places_nothing(tmp_path):
    (tmp_path / "matrix_video.json").write_text(json.dumps({"target": "Panel Matrix", "file": "/nope.mp4"}))
    assert place_matrix_video(tmp_path, 1000) == []


def test_settings_refuse_a_path_that_would_break_the_string():
    import pytest
    with pytest.raises(ValueError):
        build_video_settings("/a,b.mp4")
