"""Grapheme→phoneme→viseme for singing-face lip-sync (deterministic, offline)."""

from __future__ import annotations

from xlights_core.audio.phonemes import (
    ARPABET_TO_VISEME,
    VISEMES,
    arpabet_to_visemes,
    word_to_visemes,
)

# a tiny injected pronunciation dict so the test runs without the optional `cmudict` extra
_DICT = {
    "red": ["R", "EH1", "D"],
    "go": ["G", "OW1"],
    "we": ["W", "IY1"],
    "my": ["M", "AY1"],
}


def _lookup(w):
    return _DICT.get(w)


def test_arpabet_maps_to_mouth_shapes():
    # 'red' R EH D -> etc, E, etc  (stress digit stripped)
    assert arpabet_to_visemes(["R", "EH1", "D"]) == ["etc", "E", "etc"]
    # 'my' M AY -> MBP, AI
    assert arpabet_to_visemes(["M", "AY1"]) == ["MBP", "AI"]


def test_collapses_consecutive_duplicates():
    # T and S both map to 'etc' → collapse to a single 'etc'
    assert arpabet_to_visemes(["T", "S"]) == ["etc"]


def test_only_emits_known_visemes():
    for w in ("red", "go", "we", "my"):
        assert set(word_to_visemes(w, lookup=_lookup)) <= set(VISEMES)


def test_known_word_uses_dictionary():
    assert word_to_visemes("we", lookup=_lookup) == ["WQ", "E"]   # W->WQ, IY->E


def test_oov_word_uses_fallback():
    vis = word_to_visemes("zzgrxx", lookup=_lookup)               # not in the dict
    assert vis and set(vis) <= set(VISEMES)                       # non-empty, valid shapes


def test_punctuation_and_empty():
    assert word_to_visemes("red!", lookup=_lookup) == ["etc", "E", "etc"]
    assert word_to_visemes("", lookup=_lookup) == []
    assert word_to_visemes("...", lookup=_lookup) == []


def test_no_lookup_falls_back_not_raises():
    # lookup returns None for everything → letter fallback, never raises
    vis = word_to_visemes("hello", lookup=lambda w: None)
    assert vis and set(vis) <= set(VISEMES)


def test_viseme_table_values_are_valid():
    assert set(ARPABET_TO_VISEME.values()) <= set(VISEMES)
