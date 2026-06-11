"""Tests for LLM-chosen render style + safety fallback."""
from xlights_orchestrator.pipeline.render_style import resolve_buffer_style, fallback_style, KNOWN_STYLES


def test_llm_choice_honored_when_valid():
    assert resolve_buffer_style("Per Preview", "Pinwheel") == "Per Preview"     # LLM leads
    assert resolve_buffer_style("Per Model Default", "Bars") == "Per Model Default"


def test_fallback_when_unset_or_invalid():
    assert resolve_buffer_style("", "Pinwheel") == "Per Model Default"          # fill → per-model
    assert resolve_buffer_style("Nonsense", "Pinwheel") == "Per Model Default"  # invalid → fallback
    assert resolve_buffer_style("", "Shockwave") == "Per Preview"               # sweep → travels
    assert resolve_buffer_style("", "On") == "Default"                          # simple


def test_fallback_never_sparse_default_for_fill():
    # an unknown effect falls back to per-model fill, never the unset sparse default
    assert fallback_style("SomeNewEffect") == "Per Model Default"
    assert resolve_buffer_style("", "Butterfly") in KNOWN_STYLES
