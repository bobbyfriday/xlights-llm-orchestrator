"""Music Synthesizer: fuses the analysts' outputs into one de-conflicted MusicBrief."""

from __future__ import annotations

import json

from xlights_core.audio import SongAnalysis

from ..models import build_agent
from ..music_brief import MusicBrief

_PROMPT = (
    "You are the Music Synthesizer. Fuse the analysts' findings into ONE deep, accurate"
    " description of the song — the foundation everything downstream depends on, so be RICH and"
    " specific, never generic. Anchor section times to the structure analyst's labeled sections"
    " (do not invent boundaries). For EACH section write a vivid 2-4 sentence `musical_description`"
    " of what actually happens (texture, what enters/drops, the feel). Fill `identity`"
    " (title/artist/genre/bpm/time_signature/key_mode + a one-paragraph `character`), `dynamic_arc`"
    " (climax_ms, builds_ms, drops_ms, a `range_note` on the dynamic shape) from the rhythm analyst,"
    " `harmony_summary` + `transition_cues_ms` from the harmony analyst, and `narrative_or_journey`:"
    " for a VOCAL song the lyric narrative; for an INSTRUMENTAL the EMOTIONAL JOURNEY the music"
    " tells — describe what the MUSIC does, and do NOT invent lyrics, characters, or a story not"
    " supported by the analysis. Use the lyric analyst (only if present) for"
    " narrative_summary/sentiment/featured_lines. Do NOT fill intensity, dominant_instruments, or"
    " stem_shares — those are computed in code from the audio. Ground every claim in the analysis.\n"
    "HARD RULES: If `instrumental` is true (no lyrics/vocals detected), there are NO words — do NOT"
    " invent lyrics, rap, vocals, a story, characters, or any lyrical narrative; narrative_or_journey"
    " describes ONLY what the MUSIC does emotionally. The TITLE and filename are NOT evidence of"
    " content or genre — never infer a story/genre from them. For `identity`: report bpm, key_mode,"
    " and time_signature from the analysis, but only set title/artist/genre if track_id/genre are"
    " PROVIDED — otherwise leave them blank (do not guess)."
)


def synthesizer_agent():
    return build_agent("synthesizer", output_type=MusicBrief, system_prompt=_PROMPT)


def render_input(outputs: dict, sa: SongAnalysis) -> str:
    payload = {k: v.model_dump() for k, v in outputs.items()}
    # A song is instrumental only when NO lyric evidence exists: neither aligned lyrics
    # on the analysis nor a lyric analyst in the panel (fetched text can be present even
    # when alignment failed, and the header must not contradict that analyst's output).
    instrumental = "lyric" not in outputs and not getattr(sa, "lyrics", None)
    header = {"duration_s": round(sa.duration_s, 1), "tempo_bpm": sa.tempo_overall,
              "key": sa.key_overall, "n_segments": len(sa.segments),
              "instrumental": instrumental,   # no lyrics → no fabricated narrative
              "track_id": getattr(sa, "track_id", None),
              "genre": getattr(sa, "genre", None)}
    return ("ANALYSIS HEADER:\n" + json.dumps(header)
            + "\n\nANALYST OUTPUTS:\n" + json.dumps(payload, default=str)
            + "\n\nProduce the fused MusicBrief.")
