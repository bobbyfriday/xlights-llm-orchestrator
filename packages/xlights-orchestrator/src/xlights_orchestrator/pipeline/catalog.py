"""Views over the preset library for the agents (placeable types, look menus) and the LOOK PICKER.

The catalog holds a thousand-odd community-mined looks, but until 2026-11 every placement path
took the FIRST look of each type in corpus order — `Spirals#0`, four corpus occurrences, while
`Spirals#99` had 166. Every show looked alike. Now:

- `candidate_look_ids` ranks a type's looks by corpus count (most-used first), so "the first
  look" is the community's default rather than an accident of file order.
- `pick_look(effect_type, seed)` rotates deterministically among the `PICK_POOL` most-used
  *neutral* looks — a look that bakes a layer blend, a mask or a sub-buffer quadrant into its
  frozen settings or knob defaults is not a neutral default (a lone `Brightness` layer over
  nothing is black), so those are left for an authored `stack` layer to name explicitly.
"""

from __future__ import annotations

from functools import lru_cache

from xlights_core.knowledge import get_library

# Effect-type names xLights' addEffect genuinely rejects despite being in the corpus.
# Empty as of 2026-06-14: "Color Wash" was here, but a live re-test shows it now places
# (addEffect worked=true) and renders — its old worked=false was a casualty of the +-vs-%20
# GET-encoding bug (fixed 2026-06-10), which sent "Color Wash" as "Color+Wash". The set stays
# as the mechanism for any type that is ever confirmed truly unplaceable.
# Catalog types that are not PLACEABLE from a preset: "Text" needs its string and is placed by
# `matrix_text` from direct settings; "Moving Head" drives DMX hardware. Both entered the catalog
# with the 2024–2025 community files (2026-11-02 re-mine); they stay out of the brief vocabulary.
KNOWN_REJECTED_TYPES: set[str] = {"Text", "Moving Head"}

PICK_POOL = 6                     # rotate among this many of the most-used neutral looks
# A look carrying one of these in its frozen base, or as a knob whose default is not neutral,
# is a *designed* look (a blend, a mask, a quadrant, a locked preset), never a default pick.
_NON_NEUTRAL_KEYS = ("T_CHOICE_LayerMethod", "B_CUSTOM_SubBuffer", "X_Effect_Locked")
_NEUTRAL_VALUES = {"", "Normal", "0.00x0.00x100.00x100.00x0.00x0.00"}


def placeable_effect_types() -> list[str]:
    lib = get_library()
    return sorted(t for t in lib.list_effect_types() if t not in KNOWN_REJECTED_TYPES)


def _index(look_id: str) -> int:
    try:
        return int(look_id.rsplit("#", 1)[1])
    except (IndexError, ValueError):
        return 0


@lru_cache(maxsize=None)
def ranked_look_ids(effect_type: str) -> tuple[str, ...]:
    """A type's look ids, most corpus occurrences first (ties by id index — stable)."""
    looks = get_library().get_looks(effect_type)
    return tuple(lk.look_id for lk in sorted(looks, key=lambda lk: (-lk.count, _index(lk.look_id))))


def candidate_look_ids(effect_type: str, *, limit: int = 12) -> list[str]:
    return list(ranked_look_ids(effect_type)[:limit])


def _neutral(look) -> bool:
    for key in _NON_NEUTRAL_KEYS:
        if key in look.frozen_base and look.frozen_base[key] not in _NEUTRAL_VALUES:
            return False
    for knob in look.knobs:
        if knob.key in _NON_NEUTRAL_KEYS and (knob.default or "") not in _NEUTRAL_VALUES:
            return False
    return True


@lru_cache(maxsize=None)
def pick_pool(effect_type: str) -> tuple[str, ...]:
    """The looks `pick_look` rotates among: the `PICK_POOL` most-used neutral looks (every
    ranked look when none is neutral; empty for an unknown type)."""
    lib = get_library()
    ranked = [lib.get_look(effect_type, lid) for lid in ranked_look_ids(effect_type)]
    neutral = [lk.look_id for lk in ranked if _neutral(lk)]
    pool = neutral or [lk.look_id for lk in ranked]
    return tuple(pool[:PICK_POOL])


def pick_look(effect_type: str, seed: int = 0) -> str:
    """A deterministic look for `effect_type`: the pool entry at `seed` (mod pool size).
    `""` when the type has no looks. Callers seed with the section's label seed (recurring
    sections rhyme) plus a per-row offset (concurrent rows differ)."""
    pool = pick_pool(effect_type)
    return pool[seed % len(pool)] if pool else ""


def look_ids_by_type() -> dict[str, list[str]]:
    """Every placeable type's look ids, ranked — the brief vocabulary's `looks` entry."""
    return {t: list(ranked_look_ids(t)) for t in placeable_effect_types()}
