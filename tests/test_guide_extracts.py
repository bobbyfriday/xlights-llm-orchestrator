"""Tests for per-purpose guide extracts (the generator's slim system prompt)."""

from __future__ import annotations

import pytest

from xlights_orchestrator.agents import guide as G
from xlights_orchestrator.agents import guide_extracts as X


@pytest.fixture(autouse=True)
def _clear_cache():
    G._cache.clear()
    yield
    G._cache.clear()


def test_catalog_essentials_sentinels_and_bounds():
    s = X.catalog_essentials()
    assert "Quick Reference Table" in s and "Placement Decision Rules" in s
    assert "Duration Classes" in s                  # the 2.1 subsection rides along
    assert 0 < len(s) < 10_000                      # an extract, not the 33KB catalog


def test_layering_essentials_render_styles_only():
    s = X.layering_essentials()
    assert "Render Styles" in s and "Per Model" in s
    assert 0 < len(s) < 6_000                       # one section, not the 20KB guide
    assert "Blending Modes" not in s                # neighbors stay out


def test_sequencing_essentials_bounded_philosophy_plus_rhythm():
    s = X.sequencing_essentials()
    assert "Core Philosophy" in s and "rhythm" in s.lower()
    assert 0 < len(s) <= 3_072                      # hard bound (prompt budget)


def test_scene_recipe_isolates_the_named_scene():
    r = X.scene_recipe("SC-01")
    assert "SC-01" in r and 0 < len(r) < 4_000
    for other in ("SC-02", "SC-09", "SC-14"):       # ONLY the named scene's block
        assert other not in r


def test_scene_recipe_empty_or_unknown_id():
    assert X.scene_recipe("") == ""
    assert X.scene_recipe("SC-99") == ""


def test_missing_guide_degrades_to_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_EFFECTS_CATALOG", str(tmp_path / "nope.md"))
    G._cache.clear()
    assert X.catalog_essentials() == ""             # no raise — thinner prompt is valid


def test_composed_generator_prompt_under_budget():
    from xlights_orchestrator.agents import generator
    sp = generator._system_prompt()
    assert len(sp) < 16 * 1024                      # extracts, not the ~100KB corpus
    assert "Quick Reference Table" in sp and "Render Styles" in sp and "Core Philosophy" in sp
    assert "SC-01" not in sp                        # scene recipes are per-section input


def test_render_input_carries_only_the_sections_scene():
    from xlights_orchestrator.agents import generator
    from xlights_orchestrator.show_plan import SectionPlan
    sec = SectionPlan(start_ms=0, end_ms=1000, target_groups=["SEM_FOCAL"],
                      effect_family="On", intensity=0.5, scene_id="SC-01")
    txt = generator.render_input(sec)
    assert "SCENE RECIPE" in txt and "Standard Stack" in txt   # SC-01's block inlined
    assert "SC-14" not in txt
    plain = generator.render_input(sec.model_copy(update={"scene_id": ""}))
    assert "SCENE RECIPE" not in plain
