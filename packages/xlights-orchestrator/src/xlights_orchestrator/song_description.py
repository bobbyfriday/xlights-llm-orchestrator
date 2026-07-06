"""Deterministic surfacing + rendering for the rich song description (Stage 1).

Code-owned facts (so the model can't flatten or fabricate them): per-section intensity
normalized to the song's own dynamic range, stem shares over time, and featured lyric moments
paired with timestamps. Plus a pure Markdown render of the whole description for human review.
"""

from __future__ import annotations

import re
import statistics

from ._fmt import mmss
from .music_brief import FeaturedLyricMoment, MusicBrief


# -- dynamics: normalize per-section intensity to THIS song's range (overwrites) ----

def _section_energy(sec, points) -> float:
    vals = [p.rms for p in points if sec.start_ms <= p.time * 1000 < sec.end_ms]
    return statistics.fmean(vals) if vals else 0.0


def normalize_intensities(brief: MusicBrief, sa) -> None:
    """Overwrite each section's intensity with its energy normalized to 0..1 across the song
    (robust 5th-95th percentile min/max). Relative, not absolute loudness."""
    points = getattr(sa, "energy_arc", None) or []
    secs = brief.sections
    if not secs or not points:
        return
    energies = [_section_energy(s, points) for s in secs]
    ordered = sorted(energies)
    n = len(ordered)
    lo = ordered[max(0, int(0.05 * (n - 1)))]
    hi = ordered[min(n - 1, round(0.95 * (n - 1)))]
    span = hi - lo
    for s, e in zip(secs, energies):
        s.intensity = 0.5 if span <= 1e-9 else round(max(0.0, min(1.0, (e - lo) / span)), 3)


# -- featured lyric moments: pair powerful lines with timestamps (defensive) --------

def _timed_lines(lyrics: dict) -> list[tuple[str, int, int]]:
    """Best-effort extraction of (text, start_ms, end_ms) from the untyped lyrics dict."""
    out: list[tuple[str, int, int]] = []
    if not isinstance(lyrics, dict):
        return out

    def _ms(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        return int(v * 1000) if v < 10000 else int(v)   # seconds vs already-ms heuristic

    lines = lyrics.get("lines") or lyrics.get("synced") or []
    for ln in lines if isinstance(lines, list) else []:
        if not isinstance(ln, dict):
            continue
        text = ln.get("text") or ln.get("line") or ln.get("words")
        start = _ms(ln.get("start", ln.get("start_ms", ln.get("time"))))
        end = _ms(ln.get("end", ln.get("end_ms")))
        if isinstance(text, str) and start is not None:
            out.append((text.strip(), start, end if end is not None else start + 2000))
    return out


def _norm(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", s.lower()))


# A trailing "(start-end)" numeric time-range an analyst may append to a featured line
# (e.g. "Who you gon' call? (32.96-34.36)"). Purely numeric, so real lyric parentheticals
# like "(Ghostbusters!)" are left intact.
_TIME_RANGE_RE = re.compile(r"\s*\(\s*\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*\)\s*$")


def featured_lyric_moments(brief: MusicBrief, sa) -> list[FeaturedLyricMoment]:
    """Match the analyst's featured_lines to timed lines → moments. Empty when no lyrics."""
    lyrics = getattr(sa, "lyrics", None)
    feats = brief.featured_lines or []
    timed = _timed_lines(lyrics) if lyrics else []
    if not feats or not timed:
        return []
    out: list[FeaturedLyricMoment] = []
    for f in feats:
        f = _TIME_RANGE_RE.sub("", f).strip()           # analysts may still append "(start-end)";
        ftok = _norm(f)                                 # drop it (redundant, and its digits hurt the match)
        if not ftok:
            continue
        best, score = None, 0.0
        for text, a, b in timed:
            ov = len(ftok & _norm(text))
            sc = ov / max(1, len(ftok))
            if sc > score:
                best, score = (text, a, b), sc
        if best and score >= 0.5:                       # majority token overlap → confident match
            out.append(FeaturedLyricMoment(line=f, start_ms=best[1], end_ms=best[2]))
    return out


# -- pure Markdown render of the whole description (human review) -------------------



def render_description(brief: MusicBrief) -> str:
    L: list[str] = ["# Song description\n"]
    idn = brief.identity
    if idn:
        bits = [b for b in [idn.title, idn.artist, idn.genre,
                            f"{idn.bpm:.0f} BPM" if idn.bpm else "", idn.time_signature,
                            idn.key_mode] if b]
        L.append("**" + " · ".join(bits) + "**\n" if bits else "")
        if idn.character:
            L.append(f"{idn.character}\n")
    da = brief.dynamic_arc
    if da:
        clim = f"climax ~{mmss(da.climax_ms)}" if da.climax_ms is not None else ""
        L.append(f"\n**Dynamic arc:** {da.range_note} {clim}\n".rstrip() + "\n")
    if brief.harmony_summary:
        L.append(f"**Harmony:** {brief.harmony_summary}\n")
    if brief.narrative_or_journey:
        L.append(f"**Journey:** {brief.narrative_or_journey}\n")

    L.append("\n## Sections\n")
    for i, s in enumerate(brief.sections):
        L.append(f"\n### {i}. {s.label} · {mmss(s.start_ms)}–{mmss(s.end_ms)} · intensity {s.intensity:.2f}\n")
        if s.musical_description:
            L.append(f"{s.musical_description}\n")
        if s.stem_shares:
            shares = ", ".join(f"{k} {v*100:.0f}%" for k, v in
                               sorted(s.stem_shares.items(), key=lambda kv: -kv[1]))
            L.append(f"- instrumentation: {shares}"
                     + (f" — {s.instrumentation_phrase}" if s.instrumentation_phrase else "") + "\n")
        elif s.instrumentation_phrase:
            L.append(f"- instrumentation: {s.instrumentation_phrase}\n")
        if s.accents_ms:
            L.append(f"- accents: {', '.join(mmss(a) for a in s.accents_ms[:8])}\n")

    if brief.featured_lyric_moments:
        L.append("\n## Featured lyric moments\n")
        for m in brief.featured_lyric_moments:
            L.append(f"- **{mmss(m.start_ms)}** “{m.line}”" + (f" — {m.why}" if m.why else "") + "\n")
    return "".join(L)
