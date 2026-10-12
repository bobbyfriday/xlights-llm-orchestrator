"""The media plan for the centerpiece film: which sections are FILMED (Veo) and which PROCEDURAL.

Decided BEFORE the Videographer writes, from cached structure alone, by code — no LLM counts clips.
A beat written for Veo and downgraded to procedural loses its subject (people, faces, hands); a beat
written for procedural films fine. So the plan comes first and the storyboard is written for it.

Value: the climax, sections carrying featured lines, the opening, and energy. Repeated sections (the
choruses) share one filmed ASSET and spend its clips once. Filmed assets are chosen by value until the
next would exceed the CAMPAIGN budget (what the story may assume will eventually exist); the Veo
ledger's remaining quota decides only what is renderable TODAY, via the promote order. Pure functions
throughout: same cache + same budget ⇒ the same plan ⇒ a reproducible storyboard.
"""

from __future__ import annotations

import math
import re
from typing import Literal

from pydantic import BaseModel

from .video_script import MediaSummary, ScriptConstraints, Shot

Medium = Literal["filmed", "procedural"]

# Value-score weights (one place; the Markdown shows each section's score so a bad pick is visible).
W_CLIMAX = 3.0
W_FEATURED = 2.0          # per featured line the section carries …
FEATURED_CAP = 4.0        # … capped, so a chorus with five featured lines doesn't swamp the climax
W_OPENING = 1.0           # the film's first image
W_ENERGY = 1.0            # × the section's energy (0..1)


class MediaBudget(BaseModel):
    campaign_clips: int               # clips the STORY may assume will eventually be rendered
    clip_s: float = 8.0               # Veo clip length
    max_stretch: float = 1.2          # 24 fps clip played frame-for-frame at 20 fps ⇒ ×1.2
    pinned: list[int] = []            # section indexes the user insists are filmed

    @property
    def effective_clip_s(self) -> float:
        return self.clip_s * self.max_stretch


class Asset(BaseModel):
    id: str
    label: str
    sections: list[int]
    clips: int                        # clips to cover the LONGEST member section
    value: float
    medium: Medium = "procedural"
    promote_rank: int | None = None   # 1 = render first


class SectionMedia(BaseModel):
    index: int
    label: str
    medium: Medium
    asset: str
    value: float
    clips: int                        # the asset's clips (0 when procedural)


class ShotHandoff(BaseModel):
    """What a renderer gets per shot. Composed by CODE from beat fields: no renderer parses prose,
    and every number comes from the resolved shot, never the model."""
    shot_index: int
    section_index: int
    part: int | None = None
    medium: Medium
    asset: str
    start_ms: int
    end_ms: int
    frames: int
    veo_prompt: str = ""              # filmed shots
    procedural_brief: str             # every shot: the beat (procedural) or its stand-in (filmed)


class MediaPlan(BaseModel):
    budget: MediaBudget
    ledger_remaining: int             # clips left in today's quota when the plan was made
    sections: list[SectionMedia]
    assets: list[Asset]
    clips_planned: int
    veo_seconds: float
    est_usd: float | None = None      # None = unpriced, never zero
    renderable_today: int             # planned assets (in promote order) that fit today's remainder
    handoff: list[ShotHandoff] = []

    def medium_of(self, section_index: int) -> Medium:
        return self.sections[section_index].medium

    def asset_of(self, section_index: int) -> str:
        return self.sections[section_index].asset

    def filmed_assets(self) -> list[Asset]:
        return sorted((a for a in self.assets if a.medium == "filmed"),
                      key=lambda a: a.promote_rank or 0)


# -- scoring, grouping, clip math -------------------------------------------------

def value_scores(energies: list[float], featured_hits: dict[int, int]) -> list[float]:
    """Per-section value. `featured_hits` maps section index → number of featured lines sung in it."""
    if not energies:
        return []
    climax = max(range(len(energies)), key=lambda i: energies[i])
    out = []
    for i, en in enumerate(energies):
        v = W_ENERGY * float(en)
        if i == climax:
            v += W_CLIMAX
        if i == 0:
            v += W_OPENING
        v += min(FEATURED_CAP, W_FEATURED * featured_hits.get(i, 0))
        out.append(round(v, 4))
    return out


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (text or "").casefold())).strip()


def featured_hits(featured_lines: list[str], lyrics: list[tuple[int, str]],
                  sections: list[tuple[int, int]]) -> dict[int, int]:
    """Which sections carry a featured line: a featured line matches an aligned lyric line when
    either normalized text contains the other (min 4 chars); the lyric's time picks the section."""
    hits: dict[int, int] = {}
    for fl in featured_lines or []:
        f = _norm(fl)
        if len(f) < 4:
            continue
        for ms, text in lyrics:
            t = _norm(text)
            if len(t) >= 4 and (f in t or t in f):
                idx = next((i for i, (s, e) in enumerate(sections) if s <= ms < e), None)
                if idx is not None:
                    hits[idx] = hits.get(idx, 0) + 1
                    break                                  # one section per featured line
    return hits


# Labels whose repeats are the SAME music returning (so one filmed shot can return with them). Verses
# and bridges repeat a label without repeating content — four sections labeled "verse" are four
# different verses — so they are never grouped (observed on Christmas Canon: one "verse" asset got
# four different beats).
REPEAT_LABEL_RE = re.compile(r"\b(chorus|refrain|hook|drop)\b", re.IGNORECASE)


def asset_groups(labels: list[str]) -> list[list[int]]:
    """Sections with the same chorus-family label (chorus / pre-chorus / post-chorus / refrain / hook /
    drop) share an asset; every other section is its own group. Ordered by first appearance."""
    by_label: dict[str, list[int]] = {}
    groups: list[list[int]] = []
    for i, lab in enumerate(labels):
        key = _norm(lab)
        if not key or not REPEAT_LABEL_RE.search(key):
            groups.append([i])
            continue
        if key not in by_label:
            by_label[key] = []
            groups.append(by_label[key])
        by_label[key].append(i)
    return groups


def clips_for(duration_ms: int, clip_s: float, max_stretch: float = 1.0) -> int:
    """Clips to cover a span at `clip_s` seconds each, allowing a frame-for-frame retime of up to
    `max_stretch` (a 24 fps clip at 20 fps). Always at least one for a positive span."""
    eff_ms = clip_s * max_stretch * 1000
    if eff_ms <= 0:
        raise ValueError(f"bad clip length {clip_s}s × {max_stretch}")
    if duration_ms <= 0:
        return 0
    return max(1, math.ceil(duration_ms / eff_ms - 1e-9))


# -- the plan ------------------------------------------------------------------

def plan(sections: list[tuple[int, int]], labels: list[str], energies: list[float],
         featured: dict[int, int], budget: MediaBudget, ledger_remaining: int, *,
         per_second_usd: float | None = None) -> MediaPlan:
    """Filmed assets by value until the next would exceed the campaign budget; everything else is
    procedural. Pinned sections' assets come first and must fit (else ValueError — the user asked
    for more film than the budget allows). `ledger_remaining` never changes WHICH assets are filmed,
    only how many are renderable today."""
    n = len(sections)
    if not (len(labels) == len(energies) == n):
        raise ValueError(f"sections/labels/energies lengths differ: {n}/{len(labels)}/{len(energies)}")
    bad = [i for i in budget.pinned if not 0 <= i < n]
    if bad:
        raise ValueError(f"pinned section(s) out of range: {bad} (sections are 0..{n - 1})")

    values = value_scores(energies, featured)
    assets: list[Asset] = []
    for gi, members in enumerate(asset_groups(labels), start=1):
        longest = max(sections[i][1] - sections[i][0] for i in members)
        assets.append(Asset(id=f"A{gi}", label=labels[members[0]], sections=list(members),
                            clips=clips_for(longest, budget.clip_s, budget.max_stretch),
                            value=max(values[i] for i in members)))
    by_section = {i: a for a in assets for i in a.sections}

    remaining = budget.campaign_clips
    filmed: list[Asset] = []
    for i in budget.pinned:                                 # pinned first, in the user's order
        a = by_section[i]
        if a in filmed:
            continue
        if a.clips > remaining:
            raise ValueError(f"pinned section {i} ({a.label or 'unlabeled'}, asset {a.id}) needs "
                             f"{a.clips} clip(s) but only {remaining} of the {budget.campaign_clips}"
                             f"-clip budget remain")
        remaining -= a.clips
        filmed.append(a)
    ranked = sorted((a for a in assets if a not in filmed),
                    key=lambda a: (-a.value, min(a.sections)))
    for a in ranked:                                        # by value until the next doesn't fit
        if a.clips > remaining:
            break
        remaining -= a.clips
        filmed.append(a)
    for rank, a in enumerate(filmed, start=1):
        a.medium, a.promote_rank = "filmed", rank

    clips_planned = sum(a.clips for a in filmed)
    renderable, left = 0, ledger_remaining
    for a in filmed:                                        # promote order, stop at the first miss
        if a.clips > left:
            break
        left -= a.clips
        renderable += 1
    veo_seconds = clips_planned * budget.clip_s
    return MediaPlan(
        budget=budget, ledger_remaining=ledger_remaining,
        sections=[SectionMedia(index=i, label=labels[i], medium=by_section[i].medium,
                               asset=by_section[i].id, value=values[i],
                               clips=by_section[i].clips if by_section[i].medium == "filmed" else 0)
                  for i in range(n)],
        assets=assets, clips_planned=clips_planned, veo_seconds=veo_seconds,
        est_usd=None if per_second_usd is None else round(veo_seconds * per_second_usd, 4),
        renderable_today=renderable)


def summary(p: MediaPlan) -> MediaSummary:
    filmed = [s for s in p.sections if s.medium == "filmed"]
    return MediaSummary(campaign_clips=p.budget.campaign_clips, filmed_sections=len(filmed),
                        procedural_sections=len(p.sections) - len(filmed),
                        assets_filmed=len(p.filmed_assets()), clips_planned=p.clips_planned,
                        veo_seconds=p.veo_seconds, est_usd=p.est_usd,
                        ledger_remaining=p.ledger_remaining, renderable_today=p.renderable_today)


# -- applying the plan to resolved shots ------------------------------------------

def apply_media(shots: list[Shot], p: MediaPlan) -> None:
    """Stamp each shot (by section) with its medium, asset, clips and promote rank."""
    by_asset = {a.id: a for a in p.assets}
    for sh in shots:
        sm = p.sections[sh.section_index]
        a = by_asset[sm.asset]
        sh.medium, sh.asset, sh.clips = sm.medium, sm.asset, sm.clips
        sh.promote_rank = a.promote_rank if sm.medium == "filmed" else None


# -- the renderer hand-off (text composed by code) ---------------------------------

def _aspect(w: int, h: int) -> str:
    g = math.gcd(w, h)
    return f"{w // g}:{h // g}"


def veo_prompt(shot: Shot, c: ScriptConstraints) -> str:
    b = shot.beat
    return " ".join(part for part in (
        f"{b.imagery.rstrip('.')}. {b.action.rstrip('.')}.",
        f"Camera: {b.camera.rstrip('.')}.",
        f"Light: {b.lighting.rstrip('.')}.",
        "Cinematic, one continuous shot, full-frame and opaque. No text, captions, titles or logos. "
        "No Christmas light displays, houses covered in lights, or lighting hardware.",
        f"Framed for a {c.width}×{c.height} ({_aspect(c.width, c.height)}) screen; keep the subject "
        "safe for center-crop.",
    ) if part)


def procedural_brief(shot: Shot, palette: list[str], c: ScriptConstraints) -> str:
    b = shot.beat
    if shot.medium == "filmed" and b.procedural_stand_in:
        what = b.procedural_stand_in.rstrip(".") + "."
    else:
        what = f"{b.imagery.rstrip('.')}. {b.action.rstrip('.')}."
    dur = (shot.end_ms - shot.start_ms) / 1000
    pal = f" Palette: {', '.join(palette)}." if palette else ""
    return (f"{what} Light: {b.lighting.rstrip('.')}.{pal} Render {shot.frames} frames at {c.fps:g} fps "
            f"({dur:.2f} s), {c.width}×{c.height}, opaque, no text. No people, faces, hands or animals.")


def build_handoff(shots: list[Shot], palette: list[str], c: ScriptConstraints) -> list[ShotHandoff]:
    return [ShotHandoff(shot_index=sh.index, section_index=sh.section_index, part=sh.part,
                        medium="filmed" if sh.medium == "filmed" else "procedural", asset=sh.asset,
                        start_ms=sh.start_ms, end_ms=sh.end_ms, frames=sh.frames,
                        veo_prompt=veo_prompt(sh, c) if sh.medium == "filmed" else "",
                        procedural_brief=procedural_brief(sh, palette, c))
            for sh in shots]
