"""The parallel analysis panel: analysts run concurrently, a synthesizer fuses them.

This is the first genuinely multi-agent stage. Analysts each read a focused slice of
the SongAnalysis (+ lyric text) and run concurrently under a Semaphore cap (free-tier
safe). A failed analyst is dropped, not fatal. The synthesizer fuses the survivors into
one MusicBrief; per-section dominant instruments are then merged in deterministically
from stem analysis (not trusted to the LLM).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Callable

from xlights_core.audio import SongAnalysis

from ..models import build_agent
from ..song_description import featured_lyric_moments, normalize_intensities
from ..music_brief import (
    HarmonyOut,
    LyricOut,
    MusicBrief,
    RhythmOut,
    StructureOut,
)

log = logging.getLogger(__name__)


@dataclass
class AnalystSpec:
    key: str
    agent: object                       # pydantic_ai.Agent (output_type set)
    render: Callable[[SongAnalysis, object], str]


# -- compact, focused slices --------------------------------------------------

def _sample(seq, n=24):
    if len(seq) <= n:
        return list(seq)
    step = len(seq) / n
    return [seq[int(i * step)] for i in range(n)]


def _energy(sa: SongAnalysis):
    return [round(p.rms, 3) for p in _sample(sa.energy_arc)]


def _segments(sa: SongAnalysis):
    return [{"start_ms": int(s.start * 1000), "end_ms": int(s.end * 1000), "id": s.segment_id}
            for s in sa.segments]


def _structure_render(sa, lyrics):
    return ("SEGMENTS (anchor your section times to these):\n" + json.dumps(_segments(sa))
            + f"\nENERGY (sampled): {_energy(sa)}"
            + f"\nKEY: {sa.key_overall}   #CHORDS: {len(sa.chords)}"
            + "\nLabel each segment (intro/verse/chorus/bridge/drop/outro), group recurring"
              " labels in repetition_map, and propose candidate show themes.")


def _rhythm_render(sa, lyrics):
    return (f"TEMPO: {sa.tempo_overall} bpm   #BEATS: {len(sa.beats)}   #ONSETS: {len(sa.onsets)}"
            f"\nENERGY (sampled): {_energy(sa)}"
            + "\nDescribe the groove, give the energy envelope, the climax time (ms), and"
              " a few accent moments (ms) worth punctuating.")


def _harmony_render(sa, lyrics):
    chords = [c.label for c in _sample(sa.chords, 16)] if sa.chords else []
    return (f"KEY: {sa.key_overall}\nCHORDS (sampled): {json.dumps(chords)}"
            f"\nHARMONIC CHANGES (s): {[round(t,1) for t in _sample(sa.harmonic_changes,12)]}"
            + "\nGive the emotional arc, a key/mood phrase, and a color-temperature/palette hint.")


def _lyric_render(sa, lyrics):
    text = getattr(lyrics, "text", "") or ""
    if len(text) > 6000:
        text = text[:6000]
    return ("LYRICS:\n" + text + "\n\nSECTION TIMES:\n" + json.dumps(_segments(sa))
            + "\nSummarize the narrative, give overall sentiment, list a few featured"
              " 'money lines', and name lyric themes.")


_ANALYSTS = [
    ("structure", StructureOut, "You are a music structure analyst. Label sections and find repetition.", _structure_render),
    ("rhythm", RhythmOut, "You are a rhythm & dynamics analyst.", _rhythm_render),
    ("harmony", HarmonyOut, "You are a harmony & mood analyst.", _harmony_render),
]

_LYRIC = ("lyric", LyricOut, "You are a lyric & narrative analyst.", _lyric_render)

_MUSICOLOGIST_PROMPT = (
    "You are a musicologist. From the analysis, produce a complete MusicBrief: labeled"
    " sections (times anchored to the provided segments), repetition map, energy arc,"
    " key/mood, candidate themes, transition points, and lyric narrative if lyrics are given."
)


def build_panel(*, lyrics_present: bool, mode: str = "full"):
    """Return (analysts, synthesizer). mode='single' collapses to one musicologist."""
    if mode == "single":
        agent = build_agent("synthesizer", output_type=MusicBrief, system_prompt=_MUSICOLOGIST_PROMPT)

        def render(sa, lyrics):
            base = _structure_render(sa, lyrics) + "\n\n" + _harmony_render(sa, lyrics)
            return base + (("\n\n" + _lyric_render(sa, lyrics)) if lyrics else "")

        return [AnalystSpec("musicologist", agent, render)], None

    specs = [AnalystSpec(k, build_agent("analyst", output_type=ot, system_prompt=sp), rnd)
             for (k, ot, sp, rnd) in _ANALYSTS]
    if lyrics_present:
        k, ot, sp, rnd = _LYRIC
        specs.append(AnalystSpec(k, build_agent("analyst", output_type=ot, system_prompt=sp), rnd))
    from .synthesizer import synthesizer_agent
    return specs, synthesizer_agent()


# -- run ----------------------------------------------------------------------

async def run_panel(sa: SongAnalysis, lyrics, *, analysts, synthesizer, max_concurrency: int = 3) -> MusicBrief:
    sem = asyncio.Semaphore(max_concurrency)

    async def _run(spec: AnalystSpec):
        async with sem:
            res = await spec.agent.run(spec.render(sa, lyrics))
            return spec.key, res.output

    results = await asyncio.gather(*[_run(s) for s in analysts], return_exceptions=True)
    outputs: dict[str, object] = {}
    for r in results:
        if isinstance(r, Exception):
            log.warning("analyst failed, dropping: %s", r)
            continue
        key, out = r
        outputs[key] = out

    if synthesizer is None:  # single-musicologist mode → the one output IS the brief
        brief = next(iter(outputs.values()))
        if not isinstance(brief, MusicBrief):
            raise RuntimeError("single-mode analyst did not return a MusicBrief")
    else:
        from .synthesizer import render_input as synth_render
        brief = (await synthesizer.run(synth_render(outputs, sa))).output

    merge_dominant_instruments(brief, sa)
    normalize_intensities(brief, sa)                       # code-owned dynamics (overwrites the model)
    brief.featured_lyric_moments = featured_lyric_moments(brief, sa)
    return brief


def merge_dominant_instruments(brief: MusicBrief, sa: SongAnalysis) -> None:
    """Attach per-section dominant instruments from stem analysis by time overlap (in code)."""
    si = sa.section_instrumentation
    if not si:
        return
    for sec in brief.sections:
        best, best_ov = None, 0
        for inst in si:
            ov = min(sec.end_ms, inst.end_ms) - max(sec.start_ms, inst.start_ms)
            if ov > best_ov:
                best, best_ov = inst, ov
        if best is not None:
            sec.dominant_instruments = list(best.dominant)
            sec.stem_shares = dict(best.shares)               # surface prevalence OVER TIME, not just dominant
            if best.shares:
                top = sorted(best.shares.items(), key=lambda kv: -kv[1])[:2]
                sec.instrumentation_phrase = "led by " + " + ".join(k for k, _ in top)
