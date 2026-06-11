"""Tests for the climax white-flash (whole-display SEM_ALL)."""
from types import SimpleNamespace
from xlights_orchestrator.pipeline.beats import key_moment_flashes, FLASH_MS


def _plan(kinds_times):
    return SimpleNamespace(key_moments=[SimpleNamespace(at_ms=t, kind=k, treatment="") for k, t in kinds_times])


def test_flash_on_sem_all_at_climax_accents():
    acc = key_moment_flashes(_plan([("climax", 5000), ("lyric", 6000), ("accent", 7000)]),
                             ["SEM_ALL", "SEM_SIDE_LEFT"])
    assert {a.start_ms for a in acc} == {5000, 7000}                  # climax + accent, NOT lyric
    assert all(a.target == "SEM_ALL" and a.palette_colors == ["white"] for a in acc)   # whole display
    assert all(a.end_ms - a.start_ms == FLASH_MS for a in acc)
    assert all("C_SLIDER_Brightness" in a.extra_settings for a in acc)


def test_no_flash_without_sem_all_or_moments():
    assert key_moment_flashes(_plan([("climax", 1000)]), ["SEM_SIDE_LEFT"]) == []   # no SEM_ALL
    assert key_moment_flashes(_plan([]), ["SEM_ALL"]) == []
