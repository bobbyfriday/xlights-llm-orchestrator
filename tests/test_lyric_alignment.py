"""Tests for lyric alignment (matching, markers, graceful paths)."""
from xlights_core.audio.lyrics_align import _match_lines, _parse_text


def _words(text, t0=0.0, step=0.4):
    out=[]; t=t0
    for w in text.lower().split():
        out.append((w, t, t+step)); t+=step
    return out


def test_parse_text_markers():
    lines, markers = _parse_text("[Verse 1]\nhello world\n\n[Chorus]\ntake a trip\n")
    assert lines == ["hello world", "take a trip"]
    assert markers == {0: "Verse 1", 1: "Chorus"}


def test_match_lines_monotonic():
    words = _words("la la take a trip down candy cane lane with me oh oh it's the best so get dressed")
    spans = _match_lines(["Take a trip down Candy Cane Lane with me",
                          "It's the best, so get dressed"], words)
    assert spans[0] and spans[1]
    assert spans[0]["start"] < spans[1]["start"]                    # monotonic
    assert abs(spans[0]["start"] - 0.8) < 0.5                       # near 'take' (3rd word)


def test_unmatched_line_is_none():
    spans = _match_lines(["completely different sentence entirely"], _words("take a trip down candy cane lane"))
    assert spans == [None]
