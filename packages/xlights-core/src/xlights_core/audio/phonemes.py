"""Grapheme→phoneme→viseme for singing-face lip-sync.

Turns a lyric word into a sequence of xLights mouth shapes (the 10-shape Preston-Blair/Papagayo set
the Faces effect uses). Deterministic and offline: a word's ARPABET pronunciation comes from the CMU
Pronouncing Dictionary when the optional `cmudict` package is installed, else a letter-based fallback;
either way the output is drawn only from the mouth-shape set. No network, no model download.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Callable, Optional

# The xLights / Papagayo mouth shapes (a `faceInfo` carries Mouth-<shape>); `rest` = closed mouth.
VISEMES = ("AI", "E", "FV", "L", "MBP", "O", "U", "WQ", "etc", "rest")

# ARPABET phone → mouth shape (mirrors the Papagayo Preston-Blair mapping xLights ships). Vowel stress
# digits are stripped before lookup. Any phone not listed falls through to "etc" (a generic consonant).
ARPABET_TO_VISEME: dict[str, str] = {
    "AA": "AI", "AE": "AI", "AH": "AI", "AY": "AI",
    "AO": "O", "AW": "O", "OW": "O", "OY": "O",
    "EH": "E", "ER": "E", "EY": "E", "IH": "E", "IY": "E", "Y": "E",
    "UH": "U", "UW": "U",
    "W": "WQ",
    "F": "FV", "V": "FV",
    "L": "L",
    "B": "MBP", "M": "MBP", "P": "MBP",
    "CH": "etc", "D": "etc", "DH": "etc", "G": "etc", "HH": "etc", "JH": "etc",
    "K": "etc", "N": "etc", "NG": "etc", "R": "etc", "S": "etc", "SH": "etc",
    "T": "etc", "TH": "etc", "Z": "etc", "ZH": "etc",
}

# Letter-based fallback for out-of-vocabulary words (proper nouns, made-up words). Crude but
# deterministic — enough mouth movement to read as singing.
_LETTER_TO_VISEME: dict[str, str] = {
    "a": "AI", "e": "E", "i": "E", "o": "O", "u": "U", "y": "E",
    "b": "MBP", "p": "MBP", "m": "MBP", "f": "FV", "v": "FV", "w": "WQ", "l": "L",
}
_WORD_RE = re.compile(r"[a-z']+")


def _strip_stress(phone: str) -> str:
    return phone.rstrip("0123456789").upper()


def _collapse(seq: list[str]) -> list[str]:
    """Drop consecutive duplicate visemes so the mouth doesn't re-trigger the same shape."""
    out: list[str] = []
    for v in seq:
        if not out or out[-1] != v:
            out.append(v)
    return out


def arpabet_to_visemes(phones: list[str]) -> list[str]:
    """Map an ARPABET pronunciation (stress digits allowed) to mouth shapes."""
    return _collapse([ARPABET_TO_VISEME.get(_strip_stress(p), "etc") for p in phones if p.strip()])


def _fallback_visemes(word: str) -> list[str]:
    return _collapse([_LETTER_TO_VISEME.get(c, "etc") for c in word])


@lru_cache(maxsize=1)
def _cmudict_lookup() -> Optional[Callable[[str], Optional[list[str]]]]:
    """A `word -> ARPABET | None` lookup backed by the `cmudict` package, or None if unavailable."""
    try:
        import cmudict  # optional `lyrics` extra
    except ImportError:  # absent extra → fall back to the letter heuristic (a valid state)
        return None
    table = cmudict.dict()

    def lookup(w: str) -> Optional[list[str]]:
        prons = table.get(w)
        return list(prons[0]) if prons else None

    return lookup


def word_to_visemes(word: str, *, lookup: Optional[Callable[[str], Optional[list[str]]]] = None) -> list[str]:
    """A lyric word → mouth-shape sequence (drawn only from VISEMES; never raises).

    `lookup(word) -> ARPABET phones | None` is injectable (tests pass a fake dict); by default it wraps
    the CMU dictionary when installed. Out-of-vocabulary words use the letter-based fallback.
    """
    m = _WORD_RE.findall((word or "").lower())
    norm = "".join(m)
    if not norm:
        return []
    fn = lookup if lookup is not None else _cmudict_lookup()
    phones = fn(norm) if fn else None
    visemes = arpabet_to_visemes(phones) if phones else _fallback_visemes(norm)
    return visemes or ["rest"]
