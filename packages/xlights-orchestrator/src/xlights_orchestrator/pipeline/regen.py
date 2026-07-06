"""Targeted single-section regeneration — `xlo regen`.

Reloads a song's cached artifacts (analysis, brief, plan, instructions), regenerates ONE
user-chosen section through the same per-section realization the refine loop uses
(`regenerate_section`), splices it back in, and re-emits/re-saves — leaving every other section's
instructions byte-identical. The manual counterpart to the automatic `--refine` loop, for
targeted fixes.
"""

from __future__ import annotations

import json
import logging
import math

from xlights_core.audio import SongAnalysis

from .. import degradations, telemetry
from .._fmt import mmss
from ..effect_emitter import apply_instructions, clamp_layer_budget
from ..agents.catalog import placeable_effect_types
from ..agents import director as director_mod
from ..agents import generator as generator_mod
from ..music_brief import MusicBrief
from ..refine import RevisionBrief, replace_section
from ..show_plan import EffectInstruction, ShowPlan
from .cache import cache_path, cache_root, song_key
from .finalize import finalize_sequence
from .generate import finalize_effects
from .groups import targetable_groups
from .media import prepare_media
from .run import regenerate_section
from .state import State, require

log = logging.getLogger(__name__)


def _section_label(section) -> str:
    """A short human label for a section (no section name exists in the plan)."""
    look = (getattr(section, "look", "") or "").strip()
    if look:
        return look[:40]
    return getattr(section, "effect_family", "") or "section"


def list_sections(song: str) -> list[tuple[int, str, int, int]]:
    """`(index, label, start_ms, end_ms)` per section from the cached plan (for `--list`)."""
    sp_path = cache_path(song_key(song), "creative_brief", models=True)
    if not sp_path.exists():
        raise FileNotFoundError("no cached show for this song — run `xlo run` first")
    plan = ShowPlan.model_validate_json(sp_path.read_text())
    return [(i, _section_label(s), s.start_ms, s.end_ms) for i, s in enumerate(plan.sections)]


def format_sections(song: str) -> str:
    rows = list_sections(song)
    return "\n".join(f"  {i:>2}  {mmss(a)}–{mmss(b)}  {label}" for i, label, a, b in rows)


def load_cached_state(song: str) -> tuple[str, State]:
    """Rehydrate a `State` from the per-song stage cache. Raises if the show was never generated."""
    key = song_key(song)
    ins_path = cache_path(key, "instructions", models=True)
    sp_path = cache_path(key, "creative_brief", models=True)
    if not ins_path.exists() or not sp_path.exists():
        raise FileNotFoundError("no cached show for this song — run `xlo run` first")
    st = State(song_path=song)
    st.instructions = [EffectInstruction.model_validate(x)
                       for x in json.loads(ins_path.read_text())]
    st.show_plan = ShowPlan.model_validate_json(sp_path.read_text())
    mb_path = cache_path(key, "song_description", models=True)
    st.music_brief = MusicBrief.model_validate_json(mb_path.read_text()) if mb_path.exists() else None
    sa_path = cache_path(key, "song_analysis")           # shared: deterministic audio analysis
    if sa_path.exists():
        st.song_analysis = SongAnalysis.model_validate_json(sa_path.read_text())
    else:                                           # older cache: re-analyze the audio (needs deps)
        from xlights_core.audio import AudioAnalyzer
        st.song_analysis = AudioAnalyzer().analyze(song)
    return key, st


def _validate_index(st: State, section_index: int) -> None:
    n = len(st.show_plan.sections) if st.show_plan else 0
    if not (0 <= section_index < n):
        raise IndexError(f"section {section_index} out of range (show has {n} sections: 0..{n - 1})")


async def regenerate_into(st: State, section_index: int, note: str, *, gen_agent,
                          redesign=None) -> list[EffectInstruction]:
    """Splice a freshly regenerated section into `st.instructions`; other sections untouched.

    By default the section's PLAN is pinned (start/end/target-groups/look) and `note` only steers
    the generator — the same RevisionBrief path the refine loop uses. When `redesign` (a
    section-redesigner agent) is given, the Director RE-PLANS the section first (with `note` as the
    steer; only start/end pinned), then the generator realizes the new plan — for when a section's
    plan, not just its effects, is the problem. Returns (and sets) the new full instruction list.
    """
    _validate_index(st, section_index)
    if redesign is not None:                              # re-plan the SECTION, then realize it
        plan = require(st.show_plan, "show_plan")
        old = plan.sections[section_index]
        new_sec = (await redesign.run(
            director_mod.redesign_input(old, plan, [note or "redesign this section"]))).output
        if new_sec is not None:
            new_sec.start_ms, new_sec.end_ms = old.start_ms, old.end_ms   # structure pinned
            if not new_sec.target_groups:                                 # keep the old targets if none
                new_sec.target_groups = list(old.target_groups)
            plan.sections[section_index] = new_sec
    section = require(st.show_plan, "show_plan").sections[section_index]
    rev = RevisionBrief(section_index=section_index, groups=list(section.target_groups),
                        issue=note or "manual regenerate", suggested_fix=note or "")
    new = await regenerate_section(st, rev, gen_agent=gen_agent)
    st.instructions = replace_section(st.instructions, section_index, new)
    st.instructions, _ = clamp_layer_budget(st.instructions)
    return st.instructions


async def regen_section(song: str, *, client, section_index: int, note: str = "",
                        redesign: bool = False, save_as: str | None = None,
                        generator=None, emitter=None) -> State:
    """Regenerate one section of a cached show in place and re-emit/re-save the sequence.

    `redesign=True` re-PLANS the section via the Director first (for when the section's plan — its
    treatment/target-groups/look — is the problem, which the generator alone can't fix), then
    persists the new plan so it sticks; otherwise only the effects are regenerated within the plan.
    """
    telemetry.start_run()          # measure manual regens too
    dl = degradations.start_run()               # per-run degradations collector (best-effort)
    key, st = load_cached_state(song)
    _validate_index(st, section_index)
    st.available_groups = await targetable_groups(client, cache_root=cache_root())
    st.placeable_types = placeable_effect_types()
    gen_agent = generator or generator_mod.generator_agent()
    rd_agent = director_mod.section_redesigner() if redesign else None

    before = sum(1 for i in st.instructions if i.section_index == section_index)
    await regenerate_into(st, section_index, note, gen_agent=gen_agent, redesign=rd_agent)
    if redesign:                    # persist the re-planned section so a later load/regen keeps it
        cache_path(key, "creative_brief", models=True).write_text(
            require(st.show_plan, "show_plan").model_dump_json(indent=1))
    # whole-list passes after the splice (idempotent): occlusion guard, sub-frame stretch,
    # and the song-end stop+fade (a regenerated FINAL section runs out to the section end).
    st.instructions = finalize_effects(st, st.instructions)
    after = sum(1 for i in st.instructions if i.section_index == section_index)
    log.info("regenerated section %d: %d → %d effects", section_index, before, after)

    emit = emitter or apply_instructions
    dur = max(1, math.ceil(getattr(st.song_analysis, "duration_s", 0) or 1))
    st.applied = await emit(client, st.instructions, duration_secs=dur)
    cache_path(key, "instructions", models=True).write_text(
        json.dumps([i.model_dump() for i in st.instructions], indent=1))

    if save_as:
        try:
            show_folder = await client.get_show_folder()
        except Exception as exc:  # noqa: BLE001 — no show folder → media/faces enrichment lost
            degradations.note("finalize:media", exc, stage="finalize")
            show_folder = None
        media = prepare_media(song, show_folder)
        await finalize_sequence(st, client=client, save_as=save_as, media=media,
                                show_folder=show_folder,
                                duration_s=require(st.song_analysis, "song_analysis").duration_s,
                                timing_tracks=True)
    degradations.emit_summary(dl)
    if dl.summary():
        degradations.write_json(dl, cache_root() / key / "degradations.json")
    return st
