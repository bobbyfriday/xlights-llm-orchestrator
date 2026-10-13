"""The scene/trigger cookbook loader the realization reads (pipeline/cookbook)."""

from __future__ import annotations

from xlights_orchestrator.pipeline import cookbook as C


def test_scene_recipe_isolates_the_named_scene():
    r = C.scene_recipe("SC-01")
    assert "SC-01" in r and 0 < len(r) < 4_000
    for other in ("SC-02", "SC-09", "SC-14"):       # ONLY the named scene's block
        assert other not in r


def test_scene_recipe_empty_or_unknown_id():
    assert C.scene_recipe("") == ""
    assert C.scene_recipe("SC-99") == ""


def test_scene_ids_lists_the_cookbook():
    ids = C.scene_ids()
    assert "SC-01" in ids and ids == sorted(set(ids))


def test_trigger_cookbook_loads():
    assert C.load_guide("triggers")


def test_cookbook_resolves_from_any_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                     # no cookbook in cwd → repo-root copy
    assert "SC-01" in C.scene_ids()


def test_cut_skips_document_titles():
    text = "# Title\n\n## A one\nbody a\n\n## B two\nbody b\n"
    assert C._cut(text, lambda t: "A" in t) == "## A one\nbody a"
    assert C._cut(text, lambda t: "Title" in t) == ""
