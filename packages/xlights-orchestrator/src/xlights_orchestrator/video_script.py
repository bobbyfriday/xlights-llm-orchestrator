"""Video script for the centerpiece matrix: a storyboard that tells the song's story.

Claude writes the STORY as `video_story.json` (logline, recurring motifs, one beat per brief
section — the `VideoStory` model; see the xlo-video skill) from the song's story material. The story
describes the film, never the lights, so it cannot replicate the house; the show palette and energy
arc are what tie the two together.

CODE owns every timestamp: beats are keyed by section index and resolved here against the cached
section boundaries (already downbeat-aligned), so a cut in the film lands where the lights change.
`split_long_shots` optionally cuts long beats on cached downbeats for clip-length-limited tools.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping

from pydantic import BaseModel, Field, ValidationError


# -- video_story.json (no time fields: a timestamp is unrepresentable) ---------

# Licences a photo plate may carry: free to reuse in a public show without asking. Matched
# case-insensitively as a prefix ("CC BY 4.0" passes on "cc by"). Film stills, stock under a paid
# licence and "found on Google" are deliberately absent.
PHOTO_LICENSES = ("cc0", "public domain", "pd", "cc by", "cc by-sa", "unsplash", "pexels",
                  "pixabay", "nasa", "own photo")


class PhotoPlate(BaseModel):
    """A real photograph under a procedural overlay: the third look between Veo film and pure code.
    Optional per beat — a beat without one stays as planned. Free (no Veo clips), any length."""
    subject: str = Field(description="what the photo shows — also the search for finding one "
                                     "(a place or object, no people or animals)")
    move: str = Field(default="slow push-in",
                      description="the camera move over the still (push-in, pan, parallax drift)")
    overlay: str = Field(description="the procedural layers composited over it, in the procedural "
                                     "vocabulary (fog, embers, falling leaves, candle flicker, a "
                                     "breathing colour wash)")
    file: str = Field(default="", description="the local image once found; blank = still to find")
    source_url: str = Field(default="", description="where it came from")
    license: str = Field(default="", description="its licence (CC0, public domain, CC BY, Unsplash…)")
    credit: str = Field(default="", description="the author/attribution line the licence asks for")


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
    procedural_stand_in: str = Field(
        default="",
        description="FILMED beats only: one sentence saying how this beat looks rendered procedurally "
                    "(snow, light, geometry, silhouettes of objects — no people, faces, hands or animals)")
    photo: PhotoPlate | None = Field(
        default=None,
        description="optional: render this beat as a real photo under a procedural overlay instead "
                    "of pure procedural (on a filmed beat it is the stand-in's plate)")


class VideoStory(BaseModel):
    """The written story (`video_story.json`): what `xlo video-plan` times into the script."""
    logline: str = Field(description="the film's story in one or two sentences")
    motifs: list[str] = Field(description="recurring visual elements that carry the story across beats")
    beats: list[Beat]


VideographerOut = VideoStory     # the pre-claude-driven name, kept as an alias


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
    inherited: bool = False          # the story gave no beat for this section; previous beat held
    lyrics: list[str] = []
    medium: str = "filmed"           # "filmed" (Veo) | "procedural" (code) | "photo" (a photo plate
                                     # under a procedural overlay); pre-plan scripts were all filmed
    asset: str = ""                  # media-plan asset id this shot renders (shared by repeated sections)
    clips: int = 0                   # Veo clips the asset needs (0 for procedural)
    promote_rank: int | None = None  # order in which filmed assets get rendered as quota allows
    beat: Beat


class MediaSummary(BaseModel):
    """What the media plan decided, for the script's readers (the full plan is media_plan.json)."""
    campaign_clips: int
    filmed_sections: int
    procedural_sections: int
    photo_sections: int = 0          # procedural sections the story upgraded to a photo plate
    assets_filmed: int
    clips_planned: int
    veo_seconds: float
    est_usd: float | None = None     # None = unpriced (never zero)
    ledger_remaining: int
    renderable_today: int


class VideoScript(BaseModel):
    song: str
    source: str = ""                 # which cached artifacts the script was built from
    logline: str
    motifs: list[str]
    constraints: ScriptConstraints
    shots: list[Shot]
    media: MediaSummary | None = None


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


def resolve_beats(out: VideoStory, sections: list[tuple[int, int]], *, frame_ms: int,
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
        raise ValueError("the story has no beats for any given section")
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
    """Split FILMED shots longer than `max_shot_s` into parts no longer than it, cutting on downbeats.

    Each cut aims at an even share of the remaining span and takes the nearest downbeat inside the
    window that still respects the maximum; with no downbeat available it cuts at the even point.
    Identity when `max_shot_s` is None. Procedural and photo shots are never split — they render any length,
    frame-exact — so the maximum is a filmed clip length. Shot indexes are renumbered; call
    `assign_lyrics` after so each lyric line lands in the part it starts in.
    """
    if not max_shot_s:
        return shots
    max_ms = int(max_shot_s * 1000)
    if max_ms <= 0:
        raise ValueError(f"bad --max-shot-s {max_shot_s}")
    out: list[Shot] = []
    for sh in shots:
        if sh.medium != "filmed" or sh.end_ms - sh.start_ms <= max_ms:
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


# -- the written story (video_story.json) → a timed, media-planned script ---------

# Keys a story beat must NOT carry: every timestamp is code-owned (resolved from the brief's
# section cuts), so a time field in the story is a contract violation, not a hint.
TIME_KEYS = frozenset({"start_ms", "end_ms", "start", "end", "at_ms", "time", "time_ms",
                       "duration", "duration_ms", "frames"})


def validate_story(raw: dict, n_sections: int, *, allow_inherit: bool = False) -> list[str]:
    """Why a `video_story.json` can't be planned, as plain messages (empty = valid): it must parse
    as `VideoStory`, carry no time fields anywhere, and give exactly one beat per brief
    section (`section_index` 0..n-1, each once). Strict by default — a section without a beat is
    an error naming it; `allow_inherit=True` accepts gaps (`resolve_beats` then holds the previous
    beat, the old behavior). Mirrors `xlo validate-brief`'s posture — every problem in one pass,
    each naming the section or path."""
    problems: list[str] = []
    if not isinstance(raw, dict):
        return ["the story must be a JSON object"]
    for k in sorted(set(raw) & TIME_KEYS):
        problems.append(f"story carries a time field {k!r}; timestamps are code-owned, remove it")
    beats = raw.get("beats")
    if not isinstance(beats, list):
        problems.append("beats must be a list (one per brief section)")
        beats = []
    for j, b in enumerate(beats):
        if not isinstance(b, dict):
            problems.append(f"beats[{j}] must be an object")
            continue
        for k in sorted(set(b) & TIME_KEYS):
            problems.append(f"beats[{j}] carries a time field {k!r}; timestamps are code-owned, remove it")
    try:
        story = VideoStory.model_validate(raw)
    except ValidationError as exc:              # pydantic's message names the path
        problems.append(f"story does not parse as VideoStory: {exc}")
        return problems
    seen: dict[int, int] = {}
    for j, b in enumerate(story.beats):
        if not 0 <= b.section_index < n_sections:
            problems.append(f"beats[{j}].section_index {b.section_index} is out of range "
                            f"(the brief has sections 0..{n_sections - 1})")
        elif b.section_index in seen:
            problems.append(f"beats[{j}] repeats section {b.section_index} "
                            f"(already given by beats[{seen[b.section_index]}])")
        else:
            seen[b.section_index] = j
    missing = [i for i in range(n_sections) if i not in seen]
    if missing and not allow_inherit:
        problems.append("no beat for section" + ("s " if len(missing) > 1 else " ")
                        + ", ".join(str(i) for i in missing) + " (one beat per brief section; "
                        "pass --allow-inherit to hold the previous beat instead)")
    return problems


# -- the medium contract (what procedural rendering cannot draw) ------------------------------

# Things procedural rendering cannot draw. A word list in ONE place (a false positive is a one-line
# fix). Matched on word boundaries, case-insensitive, singular/plural where it matters.
PERSON_TERMS = (
    "person", "people", "man", "men", "woman", "women", "child", "children", "kid", "kids", "boy",
    "girl", "baby", "mother", "father", "grandmother", "grandfather", "family", "crowd", "dancer",
    "dancers", "traveler", "traveller", "figure", "figures", "silhouette of a person", "stranger",
    "investigator", "soldier", "singer", "couple", "lovers",
    "face", "faces", "eyes", "hand", "hands", "fingers", "arm", "arms", "feet", "footsteps",
    "animal", "animals", "dog", "cat", "horse", "deer", "reindeer", "bird", "birds", "wolf", "owl",
)
_TERM_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted(PERSON_TERMS, key=len, reverse=True))
                      + r")\b", re.IGNORECASE)


def _lint_photo(b: Beat) -> list[str]:
    """A photo plate shows a place or object (no people or animals, same as procedural), names its
    subject and overlay, and once a file or source is given, carries a reusable licence."""
    out: list[str] = []
    ph, i = b.photo, b.section_index
    if ph is None:
        return out
    if not ph.subject.strip():
        out.append(f"the photo for section {i} has no subject — say what the photo shows")
    if not ph.overlay.strip():
        out.append(f"the photo for section {i} has no overlay — name the procedural layers over it")
    hit = _TERM_RE.search(f"{ph.subject} {ph.overlay}")
    if hit:
        out.append(f"the photo for section {i} depicts '{hit.group(0)}' — a photo plate shows places "
                   f"and objects only (no people, faces, hands or animals)")
    if (ph.file.strip() or ph.source_url.strip()):
        lic = ph.license.strip().casefold()
        if not lic:
            out.append(f"the photo for section {i} has a file/source but no licence — record it "
                       f"(CC0, public domain, CC BY, Unsplash, Pexels…)")
        elif not any(lic.startswith(ok) for ok in PHOTO_LICENSES):
            out.append(f"the photo for section {i} is licensed {ph.license!r}, which isn't free to "
                       f"reuse — pick one under {', '.join(PHOTO_LICENSES)}")
        elif lic.startswith("cc by") and not ph.credit.strip():
            out.append(f"the photo for section {i} is {ph.license} — add the credit line it requires")
    return out


def lint_media(story: VideoStory, media: Mapping[int, str]) -> list[str]:
    """Violations of the medium contract, as messages the story's author can act on: procedural
    beats' imagery/action and EVERY stand-in must be free of PERSON_TERMS; filmed beats need a
    stand-in; a photo plate (any beat) must show no people and carry a reusable licence once
    sourced. `media` maps section index → "filmed" | "procedural" (the media plan)."""
    problems: list[str] = []
    for b in story.beats:
        med = media.get(b.section_index)
        if med is None:
            continue
        if b.photo is not None:
            problems += _lint_photo(b)
        if med == "procedural":
            hit = _TERM_RE.search(f"{b.imagery} {b.action}")
            if hit:
                problems.append(f"beat for section {b.section_index} is PROCEDURAL but depicts "
                                f"'{hit.group(0)}' — rewrite it with the procedural vocabulary "
                                f"(no people, faces, hands or animals); carry any character with a "
                                f"proxy object motif")
        else:
            if not b.procedural_stand_in.strip():
                problems.append(f"beat for section {b.section_index} is FILMED but has no "
                                f"procedural_stand_in — add one sentence in the procedural vocabulary")
            else:
                hit = _TERM_RE.search(b.procedural_stand_in)
                if hit:
                    problems.append(f"the procedural_stand_in for section {b.section_index} depicts "
                                    f"'{hit.group(0)}' — a stand-in must use only the procedural "
                                    f"vocabulary")
    return problems


def featured_lines_for(plan, sa) -> list[str]:
    """The lyric lines the media plan values as 'featured' hits: the brief's `key_moments` of
    kind `lyric` that carry a `text` (read via getattr — the field is additive), else the
    analysis's repeated lyric lines (`sa.lyrics["repeated"]`). Order preserved, blanks dropped."""
    out: list[str] = []
    for km in getattr(plan, "key_moments", None) or []:
        if (getattr(km, "kind", "") or "").strip().lower() == "lyric":
            text = (getattr(km, "text", "") or "").strip()
            if text:
                out.append(text)
    if out:
        return out
    lyrics = getattr(sa, "lyrics", None)
    for rep in (lyrics.get("repeated") if isinstance(lyrics, dict) else None) or []:
        text = (rep.get("text") if isinstance(rep, dict) else rep) if rep else ""
        if isinstance(text, str) and text.strip():
            out.append(text.strip())
    return out


def _pad(values: list, n: int, fill) -> list:
    values = list(values)
    return values + [fill] * (n - len(values)) if len(values) < n else values[:n]


def plan_media_for(*, sections: list[tuple[int, int]], labels: list[str], energies: list[float],
                   featured: dict[int, int] | None = None, budget=None,
                   ledger_remaining: int | None = None, per_second_usd: float | None = None):
    """The media plan BEFORE any story exists (`xlo video-plan --plan-only`): which sections are
    filmed vs procedural, from structure + energy + the clip budget — so the story can be written
    for each section's medium. Returns a `media_plan.MediaPlan`. `budget` is a
    `media_plan.MediaBudget` (default: an 8 s-clip, 10-clip campaign, nothing pinned);
    `ledger_remaining` defaults to the whole campaign. Imports `media_plan` lazily (it imports
    this module's `Shot`)."""
    from .media_plan import MediaBudget, plan as plan_media
    n = len(sections)
    if n == 0:
        raise ValueError("the brief has no sections to plan over")
    budget = budget or MediaBudget(campaign_clips=10, clip_s=8.0, max_stretch=1.2, pinned=[])
    remaining = budget.campaign_clips if ledger_remaining is None else int(ledger_remaining)
    return plan_media(sections, _pad(labels, n, ""), _pad(energies, n, 0.0), dict(featured or {}),
                      budget, remaining, per_second_usd=per_second_usd)


def plan_story(story: VideoStory, *, song: str, sections: list[tuple[int, int]],
               labels: list[str], energies: list[float], lyrics: list[tuple[int, str]],
               downbeats_ms: list[int], width: int, height: int, frame_ms: int = 50,
               max_shot_s: float | None = None, budget=None, ledger_remaining: int | None = None,
               per_second_usd: float | None = None, palette: list[str] | None = None,
               featured: dict[int, int] | None = None, source: str = "", media=None):
    """The deterministic tail after the story is written: the media plan (`media` when the
    `--plan-only` pass already wrote one, else computed now from structure + budget), beats
    resolved to the brief's section cuts, long filmed shots split on downbeats, lyrics assigned,
    the renderer hand-off composed. Returns `(VideoScript, MediaPlan)`."""
    from .media_plan import apply_media, build_handoff, summary
    n = len(sections)
    if n == 0:
        raise ValueError("the brief has no sections to plan a story over")
    labels, energies = _pad(labels, n, ""), _pad(energies, n, 0.0)
    if media is None or len(media.sections) != n:
        media = plan_media_for(sections=sections, labels=labels, energies=energies,
                               featured=featured, budget=budget, ledger_remaining=ledger_remaining,
                               per_second_usd=per_second_usd)
    budget = media.budget
    constraints = constraints_for(width, height, frame_ms, sections[-1][1])
    shots = resolve_beats(story, sections, frame_ms=frame_ms, labels=labels,
                          energies=energies, lyrics=lyrics)
    apply_media(shots, media)
    for sh in shots:                         # the story's choice, inside the plan's procedural budget
        if sh.medium == "procedural" and sh.beat.photo is not None:
            sh.medium = "photo"
    shots = split_long_shots(shots, max_shot_s=max_shot_s or budget.effective_clip_s,
                             downbeats_ms=list(downbeats_ms), frame_ms=frame_ms)
    assign_lyrics(shots, lyrics)
    media.handoff = build_handoff(shots, list(palette or []), constraints)
    ms = summary(media)
    photos = len({sh.section_index for sh in shots if sh.medium == "photo"})
    ms = ms.model_copy(update={"photo_sections": photos,
                               "procedural_sections": ms.procedural_sections - photos})
    vs = VideoScript(song=song, source=source, logline=story.logline, motifs=list(story.motifs),
                     constraints=constraints, shots=shots, media=ms)
    return vs, media


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
    if vs.media:
        m = vs.media
        est = "unpriced" if m.est_usd is None else f"~${m.est_usd:.2f}"
        L += ["", "## Media", "",
              f"- **{m.filmed_sections} filmed** section(s) in {m.assets_filmed} asset(s) · "
              f"**{m.procedural_sections} procedural**"
              + (f" · **{m.photo_sections} photo + overlay**" if m.photo_sections else ""),
              f"- Veo: {m.clips_planned} clip(s) of the {m.campaign_clips}-clip campaign budget · "
              f"{m.veo_seconds:g} s · {est}",
              f"- Today: {m.ledger_remaining} clip(s) left in the daily quota → "
              f"{m.renderable_today} planned asset(s) renderable now; the rest play their "
              f"procedural stand-in until promoted"]
    L += ["", "## Shots", ""]
    for sh in vs.shots:
        b = sh.beat
        part = f" (part {sh.part})" if sh.part else ""
        label = f" · {sh.label}" if sh.label else ""
        L.append(f"### {sh.index}. {b.title}{part}{label} — {_clock(sh.start_ms)} → {_clock(sh.end_ms)}")
        media = (f"FILMED · {sh.asset} · {sh.clips} clip(s) · promote #{sh.promote_rank}"
                 if sh.medium == "filmed" and sh.asset else sh.medium.upper())
        L.append(f"*{(sh.end_ms - sh.start_ms) / 1000:.1f}s · {sh.frames} frames · energy {sh.energy:.2f}"
                 f" · {media}" + (" · holds the previous beat" if sh.inherited else "") + "*")
        L += ["", f"**See:** {b.imagery}", "", f"**Happens:** {b.action}", "",
              f"**Camera:** {b.camera}  ", f"**Light:** {b.lighting}"]
        if sh.medium == "filmed" and b.procedural_stand_in:
            L.append(f"**Procedural stand-in:** {b.procedural_stand_in}  ")
        if b.photo is not None:
            ph = b.photo
            L.append(f"**Photo plate:** {ph.subject} ({ph.move}) · "
                     + (f"`{ph.file}`" if ph.file else "*still to find*") + "  ")
            L.append(f"**Overlay:** {ph.overlay}  ")
        if b.motifs:
            L.append(f"**Motifs:** {', '.join(b.motifs)}  ")
        if b.continuity:
            L.append(f"**From previous:** {b.continuity}  ")
        if b.draws_on:
            L.append(f"**Draws on:** {b.draws_on}  ")
        if sh.lyrics:
            L.append("**Lyrics over this shot:** " + " / ".join(f"“{t}”" for t in sh.lyrics))
        L.append("")
    plates: dict[int, Beat] = {}
    for sh in vs.shots:
        if sh.beat.photo is not None:
            plates.setdefault(sh.section_index, sh.beat)
    if plates:
        L += ["## Photo plates", "",
              "Free-to-reuse images only (CC0, public domain, CC BY with credit, Unsplash, Pexels): "
              "never film stills or images of unknown licence.", ""]
        for i, b in plates.items():
            plate = b.photo
            if plate is None:
                continue
            src = f" · <{plate.source_url}>" if plate.source_url else ""
            lic = " · ".join(x for x in (plate.license, plate.credit) if x) or "licence not yet recorded"
            L.append(f"- **{b.title}** (section {i}): {plate.subject} — "
                     + (f"`{plate.file}`" if plate.file else "still to find") + f"{src} · {lic}")
        L.append("")
    return "\n".join(L)
