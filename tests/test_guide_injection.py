"""Tests for sequencing-guide injection into the decision/critique agents."""

from __future__ import annotations

import importlib

import pytest

from xlights_orchestrator.agents import guide as G


@pytest.fixture(autouse=True)
def _clear_cache():
    G._cache.clear()
    yield
    G._cache.clear()


def test_loads_from_env_and_caches(tmp_path, monkeypatch):
    f = tmp_path / "guide.md"
    f.write_text("# House rules\nDarkness is a tool.")
    monkeypatch.setenv("XLO_SEQUENCING_GUIDE", str(f))
    assert "Darkness is a tool" in G.sequencing_guide()
    f.write_text("CHANGED")                                  # cached by path → not re-read
    assert "Darkness is a tool" in G.sequencing_guide()


def test_missing_guide_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_SEQUENCING_GUIDE", str(tmp_path / "nope.md"))
    assert G.sequencing_guide() == ""                        # no raise


def test_with_guide_appends_when_present(tmp_path, monkeypatch):
    f = tmp_path / "g.md"; f.write_text("RULE ONE")
    monkeypatch.setenv("XLO_SEQUENCING_GUIDE", str(f))
    out = G.with_guide("ROLE PROMPT")
    assert out.startswith("ROLE PROMPT") and "BEST-PRACTICES" in out and "RULE ONE" in out


def test_with_guide_noop_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_SEQUENCING_GUIDE", str(tmp_path / "nope.md"))
    assert G.with_guide("ROLE PROMPT") == "ROLE PROMPT"      # unchanged


def test_decision_agents_include_guide_interpretation_excluded(tmp_path, monkeypatch):
    f = tmp_path / "g.md"; f.write_text("SEQ_GUIDE_MARKER_XYZ")
    monkeypatch.setenv("XLO_SEQUENCING_GUIDE", str(f))
    G._cache.clear()
    # the 4 decision/critique prompts compose the guide; interpretation prompts do not
    from xlights_orchestrator.agents import director, generator, judge, visual_critic
    for mod in (director, generator, visual_critic, judge):
        assert "SEQ_GUIDE_MARKER_XYZ" in G.with_guide(mod._PROMPT)
    from xlights_orchestrator.agents import synthesizer
    assert "with_guide" not in open(synthesizer.__file__).read()      # synthesizer not wired


def test_multiple_named_guides(tmp_path, monkeypatch):
    seq = tmp_path / "seq.md"; seq.write_text("SEQ_RULES")
    fx = tmp_path / "fx.md"; fx.write_text("FX_CATALOG")
    monkeypatch.setenv("XLO_SEQUENCING_GUIDE", str(seq))
    monkeypatch.setenv("XLO_EFFECTS_CATALOG", str(fx))
    G._cache.clear()
    out = G.with_guides("ROLE", "sequencing", "effects")
    assert out.startswith("ROLE") and "SEQ_RULES" in out and "FX_CATALOG" in out
    assert "LAYERING" not in out                                  # layering not requested


def test_real_guides_present_and_routed():
    G._cache.clear()
    # all four real guides load from repo root
    assert G.load_guide("sequencing") and G.load_guide("effects") and G.load_guide("layering")
    assert G.load_guide("scenes")
    from xlights_orchestrator.agents import director, generator, visual_critic
    gen = G.with_guides(generator._PROMPT, "sequencing", "effects", "layering", "scenes")
    assert "EFFECTS CATALOG" in gen and "LAYERING" in gen and "SEQUENCING" in gen   # generator: all
    assert "SCENE COOKBOOK" in gen
    crit = G.with_guides(visual_critic._PROMPT, "sequencing", "layering")
    assert "LAYERING" in crit and "EFFECTS CATALOG" not in crit                     # critic: no catalog


def test_scene_cookbook_routed_to_director_and_generator(tmp_path, monkeypatch):
    f = tmp_path / "scenes.md"; f.write_text("SC_COOKBOOK_MARKER_XYZ")
    monkeypatch.setenv("XLO_SCENE_COOKBOOK", str(f))
    G._cache.clear()
    from xlights_orchestrator.agents import director, generator, judge, visual_critic
    assert "SC_COOKBOOK_MARKER_XYZ" in G.with_guides(director._PROMPT, "scenes")
    # the director & generator factories actually request the scenes guide; critic/judge do not
    for mod, wired in ((director, True), (generator, True), (visual_critic, False), (judge, False)):
        assert ('"scenes"' in open(mod.__file__).read()) is wired
