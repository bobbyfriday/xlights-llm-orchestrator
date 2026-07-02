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

from ..effect_emitter import apply_instructions, clamp_layer_budget
from ..agents.catalog import placeable_effect_types
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
from .state import State

log = logging.getLogger(__name__)


def _ms(t: int) -> str:
    s = max(0, int(t)) // 1000
    return f"{s // 60}:{s % 60:02d}"


def _section_label(section) -> str:
    """A short human label for a section (no section name exists in the plan)."""
    look = (getattr(section, "look", "") or "").strip()
    if look:
        return look[:40]
    return getattr(section, "effect_family", "") or "section"


def list_sections(song: str) -> list[tuple[int, str, int, int]]:
    """`(index, label, start_ms, end_ms)` per section from the cached plan (for `--list`)."""
    sp_path = cache_path(song_key(song), "creative_brief")
    if not sp_path.exists():
        raise FileNotFoundError("no cached show for this song — run `xlo run` first")
    plan = ShowPlan.model_validate_json(sp_path.read_text())
    return [(i, _section_label(s), s.start_ms, s.end_ms) for i, s in enumerate(plan.sections)]


def format_sections(song: str) -> str:
    rows = list_sections(song)
    return "\n".join(f"  {i:>2}  {_ms(a)}–{_ms(b)}  {label}" for i, label, a, b in rows)


def load_cached_state(song: str) -> tuple[str, State]:
    """Rehydrate a `State` from the per-song stage cache. Raises if the show was never generated."""
    key = song_key(song)
    ins_path = cache_path(key, "instructions")
    sp_path = cache_path(key, "creative_brief")
    if not ins_path.exists() or not sp_path.exists():
        raise FileNotFoundError("no cached show for this song — run `xlo run` first")
    st = State(song_path=song)
    st.instructions = [EffectInstruction.model_validate(x)
                       for x in json.loads(ins_path.read_text())]
    st.show_plan = ShowPlan.model_validate_json(sp_path.read_text())
    mb_path = cache_path(key, "song_description")
    st.music_brief = MusicBrief.model_validate_json(mb_path.read_text()) if mb_path.exists() else None
    sa_path = cache_path(key, "song_analysis")
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


async def regenerate_into(st: State, section_index: int, note: str, *, gen_agent) -> list[EffectInstruction]:
    """Splice a freshly regenerated section into `st.instructions`; other sections untouched.

    Section structure (start/end/target groups) stays pinned; `note` steers the generator via the
    same RevisionBrief path the refine loop uses. Returns (and sets) the new full instruction list.
    """
    _validate_index(st, section_index)
    section = st.show_plan.sections[section_index]
    rev = RevisionBrief(section_index=section_index, groups=list(section.target_groups),
                        issue=note or "manual regenerate", suggested_fix=note or "")
    new = await regenerate_section(st, rev, gen_agent=gen_agent)
    st.instructions = replace_section(st.instructions, section_index, new)
    st.instructions, _ = clamp_layer_budget(st.instructions)
    return st.instructions


async def regen_section(song: str, *, client, section_index: int, note: str = "",
                        save_as: str | None = None, generator=None, emitter=None) -> State:
    """Regenerate one section of a cached show in place and re-emit/re-save the sequence."""
    key, st = load_cached_state(song)
    _validate_index(st, section_index)
    st.available_groups = await targetable_groups(client, cache_root=cache_root())
    st.placeable_types = placeable_effect_types()
    gen_agent = generator or generator_mod.generator_agent()

    before = sum(1 for i in st.instructions if i.section_index == section_index)
    await regenerate_into(st, section_index, note, gen_agent=gen_agent)
    # whole-list passes after the splice (idempotent): occlusion guard, sub-frame stretch,
    # and the song-end stop+fade (a regenerated FINAL section runs out to the section end).
    st.instructions = finalize_effects(st, st.instructions)
    after = sum(1 for i in st.instructions if i.section_index == section_index)
    log.info("regenerated section %d: %d → %d effects", section_index, before, after)

    emit = emitter or apply_instructions
    dur = max(1, math.ceil(getattr(st.song_analysis, "duration_s", 0) or 1))
    st.applied = await emit(client, st.instructions, duration_secs=dur)
    cache_path(key, "instructions").write_text(
        json.dumps([i.model_dump() for i in st.instructions], indent=1))

    if save_as:
        try:
            show_folder = await client.get_show_folder()
        except Exception:  # noqa: BLE001
            show_folder = None
        media = prepare_media(song, show_folder)
        await finalize_sequence(st, client=client, save_as=save_as, media=media,
                                show_folder=show_folder,
                                duration_s=st.song_analysis.duration_s, timing_tracks=True)
    return st
