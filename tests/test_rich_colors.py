"""Tests for rich section colors: vocabulary, expansion, per-effect assignment."""
from xlights_core.knowledge.colors import _resolve, expand_palette
from xlights_orchestrator.pipeline.beats import effect_palette


def test_new_vocabulary_resolves():
    for name in ("Copper", "Midnight Blue", "Sunburst Orange", "Burgundy", "Champagne"):
        assert _resolve(name), name


def test_expand_palette_grows_thin_brief():
    out = expand_palette(["Gold", "Deep Blue"], 5)
    assert len(out) == 5 and len(set(out)) == 5
    assert out[0] == "#FFD700" and out[1] == "#00008B"          # bases first, anchored
    assert all(len(h) == 7 and h.startswith("#") for h in out)
    assert expand_palette(["bogus"], 5) == []                   # nothing resolvable → empty (caller falls back)


def test_multicolor_effects_get_depth_simple_stay_lean():
    plasma = effect_palette(["Gold", "Deep Blue"], "Plasma", 0)
    on = effect_palette(["Gold", "Deep Blue"], "On", 0)
    assert len(plasma) >= 3                                     # Plasma needs colors
    assert len(on) == 2                                         # On reads best lean


def test_concurrent_effects_differ():
    a = effect_palette(["Gold", "Deep Blue"], "Spirals", 0)
    b = effect_palette(["Gold", "Deep Blue"], "Spirals", 1)
    assert a != b and set(a) == set(b)                          # same family, rotated start
