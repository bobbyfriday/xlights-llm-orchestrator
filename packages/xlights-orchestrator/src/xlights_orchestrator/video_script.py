"""Video script for the centerpiece matrix: a storyboard that tells the song's story.

The Videographer agent writes the STORY (logline, recurring motifs, one beat per section) from the
song's story material — timed lyrics, narrative, themes, sentiment, mood, featured lines. It is
deliberately never shown the lights' per-section look/motion/effects, so the film cannot replicate
the house; it gets the show palette and energy arc so the two still read as one show.

CODE owns every timestamp: beats are keyed by section index and resolved here against the cached
section boundaries (already downbeat-aligned), so a cut in the film lands where the lights change.
`split_long_shots` optionally cuts long beats on cached downbeats for clip-length-limited tools.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


# -- what the agent fills (no time fields: a timestamp is unrepresentable) -----

class Beat(BaseModel):
    section_index: int = Field(description="index of the section this beat covers (given in the input)")
    title: str = Field(description="a short name for this story beat")
    imagery: str = Field(description="what we SEE: subject, setting, composition")
    action: str = Field(description="what HAPPENS during the beat — movement and change over its length")
    camera: str = Field(description="framing and camera movement")
    lighting: str = Field(description="light and colour of the frame")
    motifs: list[str] = Field(default=[], description="which recurring motifs appear in this beat")
    continuity: str = Field(default="", description="how this beat follows from the previous one")
    draws_on: str = Field(default="", description="the lyric, theme or narrative element this beat comes from")


class VideographerOut(BaseModel):
    logline: str = Field(description="the film's story in one or two sentences")
    motifs: list[str] = Field(description="recurring visual elements that carry the story across beats")
    beats: list[Beat]


# -- the resolved script -------------------------------------------------------

class ScriptConstraints(BaseModel):
    width: int
    height: int
    frame_ms: int
    fps: float
    total_ms: int
    total_frames: int
    full_frame_opaque: bool = True
    no_rendered_text: bool = True
    notes: list[str] = []


class Shot(BaseModel):
    index: int
    section_index: int
    part: int | None = None          # set when a long beat was split (1-based)
    label: str = ""                  # the song section (verse/chorus/...) it plays over
    start_ms: int
    end_ms: int
    frames: int
    energy: float = 0.0
    inherited: bool = False          # the agent gave no beat for this section; previous beat held
    lyrics: list[str] = []
    beat: Beat


class VideoScript(BaseModel):
    song: str
    source: str = ""                 # which cached artifacts the script was built from
    logline: str
    motifs: list[str]
    constraints: ScriptConstraints
    shots: list[Shot]


CONTRACT_NOTES = [
    "Full-frame, fully opaque footage: no chroma key, transparency or alpha.",
    "No rendered words — lyrics and titles are shown on a separate text matrix.",
    "This is the centerpiece of a light show: tell the story in pictures. Never depict the light "
    "display, the house, or lighting hardware.",
    "Each shot starts and ends exactly at its stated time; cuts land on the music's section changes.",
]


def frames_for(ms: int, frame_ms: int) -> int:
    return round(ms / frame_ms)


def constraints_for(width: int, height: int, frame_ms: int, total_ms: int) -> ScriptConstraints:
    if width <= 0 or height <= 0:
        raise ValueError(f"bad resolution {width}x{height}")
    if frame_ms <= 0:
        raise ValueError(f"bad frame interval {frame_ms}ms")
    return ScriptConstraints(width=width, height=height, frame_ms=frame_ms,
                             fps=round(1000 / frame_ms, 3), total_ms=total_ms,
                             total_frames=frames_for(total_ms, frame_ms), notes=list(CONTRACT_NOTES))


def labels_by_overlap(sections: list[tuple[int, int]], brief_sections: list[dict]) -> list[str]:
    """Label each plan section by the MusicBrief section it overlaps most.

    The two lists are not 1:1 — the Director consolidates (christmas canon: 8 plan sections vs 16
    brief sections) — so positional indexing would mislabel.
    """
    out = []
    for s, e in sections:
        best, best_ov = "", 0
        for b in brief_sections:
            ov = min(e, int(b.get("end_ms", 0))) - max(s, int(b.get("start_ms", 0)))
            if ov > best_ov:
                best, best_ov = str(b.get("label") or ""), ov
        out.append(best)
    return out


def lyric_lines(lines: list[dict]) -> list[tuple[int, str]]:
    """(start_ms, text) for each aligned lyric line, de-duplicated and sorted.

    Cached alignments repeat a line at the same timing (a chorus echo); keep one.
    """
    seen, out = set(), []
    for ln in lines or []:
        text, start = (ln.get("text") or "").strip(), ln.get("start")
        if not text or start is None:
            continue
        key = (text, round(float(start), 2))
        if key in seen:
            continue
        seen.add(key)
        out.append((int(round(float(start) * 1000)), text))
    return sorted(out)


def resolve_beats(out: VideographerOut, sections: list[tuple[int, int]], *, frame_ms: int,
                  labels: list[str] | None = None, energies: list[float] | None = None,
                  lyrics: list[tuple[int, str]] | None = None) -> list[Shot]:
    """One shot per section, timed from the cached boundaries.

    The first beat given for a section wins; out-of-range indexes are dropped; a section with no
    beat holds the previous one (or the next available, for a leading gap) and is marked inherited.
    """
    n = len(sections)
    by_idx: dict[int, Beat] = {}
    for b in out.beats:
        if 0 <= b.section_index < n and b.section_index not in by_idx:
            by_idx[b.section_index] = b
    if not by_idx:
        raise ValueError("the agent returned no beats for any given section")
    first = by_idx[min(by_idx)]
    shots: list[Shot] = []
    prev: Beat | None = None
    for i, (s, e) in enumerate(sections):
        beat, inherited = by_idx.get(i), False
        if beat is None:
            beat, inherited = (prev or first), True
        shots.append(Shot(
            index=i, section_index=i, label=(labels[i] if labels and i < len(labels) else ""),
            start_ms=s, end_ms=e, frames=frames_for(e - s, frame_ms),
            energy=(energies[i] if energies and i < len(energies) else 0.0),
            inherited=inherited,
            lyrics=[t for (ms, t) in (lyrics or []) if s <= ms < e],
            beat=beat.model_copy(update={"section_index": i}),
        ))
        prev = beat
    return shots


def split_long_shots(shots: list[Shot], *, max_shot_s: float | None, downbeats_ms: list[int],
                     frame_ms: int) -> list[Shot]:
    """Split shots longer than `max_shot_s` into parts no longer than it, cutting on downbeats.

    Each cut aims at an even share of the remaining span and takes the nearest downbeat inside the
    window that still respects the maximum; with no downbeat available it cuts at the even point.
    Identity when `max_shot_s` is None. Shot indexes are renumbered; call `assign_lyrics` after
    so each lyric line lands in the part it starts in.
    """
    if not max_shot_s:
        return shots
    max_ms = int(max_shot_s * 1000)
    if max_ms <= 0:
        raise ValueError(f"bad --max-shot-s {max_shot_s}")
    out: list[Shot] = []
    for sh in shots:
        if sh.end_ms - sh.start_ms <= max_ms:
            out.append(sh)
            continue
        cuts, cur = [], sh.start_ms
        while sh.end_ms - cur > max_ms:
            parts_left = math.ceil((sh.end_ms - cur) / max_ms)
            ideal = cur + (sh.end_ms - cur) / parts_left
            window = [d for d in downbeats_ms if cur < d <= cur + max_ms and d < sh.end_ms]
            cut = min(window, key=lambda d: abs(d - ideal)) if window else int(round(ideal))
            cuts.append(cut)
            cur = cut
        bounds = [sh.start_ms, *cuts, sh.end_ms]
        for p, (a, b) in enumerate(zip(bounds, bounds[1:]), start=1):
            out.append(sh.model_copy(update={
                "part": p, "start_ms": a, "end_ms": b, "frames": frames_for(b - a, frame_ms),
            }))
    for i, sh in enumerate(out):
        sh.index = i
    return out


def assign_lyrics(shots: list[Shot], lyrics: list[tuple[int, str]]) -> None:
    """(Re)attach lyric lines by start time — used after a split so lines land in their part."""
    for sh in shots:
        sh.lyrics = [t for (ms, t) in lyrics if sh.start_ms <= ms < sh.end_ms]


# -- rendering -----------------------------------------------------------------

def _clock(ms: int) -> str:
    s = ms / 1000
    return f"{int(s // 60)}:{s % 60:05.2f}"


def render_markdown(vs: VideoScript) -> str:
    c = vs.constraints
    L = [f"# {vs.song} — video script", "", f"> {vs.logline}", ""]
    if vs.motifs:
        L += ["**Recurring motifs:** " + " · ".join(vs.motifs), ""]
    L += ["## Technical contract", "",
          f"- **{c.width}×{c.height}** px · **{c.fps:g} fps** ({c.frame_ms} ms frames) · "
          f"**{_clock(c.total_ms)}** · {c.total_frames} frames · {len(vs.shots)} shots"]
    L += [f"- {n}" for n in c.notes]
    if vs.source:
        L += [f"- Built from: `{vs.source}`"]
    L += ["", "## Shots", ""]
    for sh in vs.shots:
        b = sh.beat
        part = f" (part {sh.part})" if sh.part else ""
        label = f" · {sh.label}" if sh.label else ""
        L.append(f"### {sh.index}. {b.title}{part}{label} — {_clock(sh.start_ms)} → {_clock(sh.end_ms)}")
        L.append(f"*{(sh.end_ms - sh.start_ms) / 1000:.1f}s · {sh.frames} frames · energy {sh.energy:.2f}"
                 + (" · holds the previous beat" if sh.inherited else "") + "*")
        L += ["", f"**See:** {b.imagery}", "", f"**Happens:** {b.action}", "",
              f"**Camera:** {b.camera}  ", f"**Light:** {b.lighting}"]
        if b.motifs:
            L.append(f"**Motifs:** {', '.join(b.motifs)}  ")
        if b.continuity:
            L.append(f"**From previous:** {b.continuity}  ")
        if b.draws_on:
            L.append(f"**Draws on:** {b.draws_on}  ")
        if sh.lyrics:
            L.append("**Lyrics over this shot:** " + " / ".join(f"“{t}”" for t in sh.lyrics))
        L.append("")
    return "\n".join(L)
