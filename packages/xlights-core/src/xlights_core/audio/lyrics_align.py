"""Align fetched lyric TEXT against the separated VOCAL stem → timed lines + structure hints.

Whisper (MLX) transcribes the vocal stem with word timestamps; each lyric line is fuzzy-matched
against the transcript word stream (monotonic cursor). Output feeds SongAnalysis.lyrics:
{lines:[{text,start,end}], sections:[{label,start}], repeated:[{text,times}]}. Fully graceful —
any failure returns None and analysis proceeds without timed lyrics.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

log = logging.getLogger(__name__)

_MODEL = "mlx-community/whisper-small-mlx"
_MARKER = re.compile(r"^\[([^\]]+)\]\s*$")
_WORD = re.compile(r"[a-z0-9']+")


def _norm_words(s: str) -> list[str]:
    return _WORD.findall(s.lower())


def _parse_text(text: str) -> tuple[list[str], dict[int, str]]:
    """Lyric lines (non-empty, markers stripped) + {line_index: section label} for markers."""
    lines: list[str] = []
    markers: dict[int, str] = {}
    for raw in (text or "").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = _MARKER.match(raw)
        if m:
            markers[len(lines)] = m.group(1)      # labels the NEXT line
        else:
            lines.append(raw)
    return lines, markers


def _transcribe(vocal_path: str) -> list[tuple[str, float, float]]:
    import mlx_whisper  # heavy import deferred

    out = mlx_whisper.transcribe(str(vocal_path), path_or_hf_repo=_MODEL,
                                 word_timestamps=True, language="en")
    words: list[tuple[str, float, float]] = []
    for seg in out.get("segments", []):
        for w in seg.get("words", []):
            for token in _norm_words(w.get("word", "")):
                words.append((token, float(w["start"]), float(w["end"])))
    return words


def _match_lines(lines: list[str], words: list[tuple[str, float, float]],
                 min_ratio: float = 0.55) -> list[dict | None]:
    """Monotonic fuzzy match of each line's word-sequence into the transcript stream."""
    stream = [w[0] for w in words]
    spans: list[dict | None] = []
    cursor = 0
    for line in lines:
        target = _norm_words(line)
        if not target or not stream:
            spans.append(None)
            continue
        n = len(target)
        best, best_i = 0.0, None
        lo = max(0, cursor - n * 2)
        for i in range(lo, max(lo + 1, len(stream) - n + 1)):
            window = stream[i:i + n]
            r = SequenceMatcher(None, target, window).ratio()
            if r > best:
                best, best_i = r, i
                if r > 0.92:
                    break
        if best >= min_ratio and best_i is not None:
            j = min(best_i + n - 1, len(words) - 1)
            spans.append({"text": line, "start": round(words[best_i][1], 2),
                          "end": round(words[j][2], 2)})
            cursor = best_i + n
        else:
            spans.append(None)
    return spans


def align_lyrics(vocal_path: str, text: str) -> dict | None:
    """Timed lines + section/repetition hints, or None (graceful) on any failure."""
    try:
        lines, markers = _parse_text(text)
        if not lines:
            return None
        words = _transcribe(vocal_path)
        if len(words) < 10:
            return None                            # not enough sung content to align against
        spans = _match_lines(lines, words)
        timed = [s for s in spans if s]
        if len(timed) < max(3, len(lines) // 4):
            log.info("lyric alignment too weak (%d/%d lines)", len(timed), len(lines))
            return None
        sections = [{"label": lbl, "start": spans[i]["start"]}
                    for i, lbl in markers.items() if i < len(spans) and spans[i]]
        seen: dict[str, list[float]] = {}
        for s in timed:
            seen.setdefault(" ".join(_norm_words(s["text"])), []).append(s["start"])
        repeated = [{"text": k, "times": v} for k, v in seen.items() if len(v) >= 2]
        log.info("aligned %d/%d lyric lines (%d markers, %d repeated)",
                 len(timed), len(lines), len(sections), len(repeated))
        return {"lines": timed, "sections": sections, "repeated": repeated}
    except Exception as exc:  # noqa: BLE001 — lyrics are enrichment, never block analysis
        log.info("lyric alignment unavailable: %s", exc)
        return None
