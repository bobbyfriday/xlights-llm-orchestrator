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
# is a *designed* look (a blend, a mask, a quadrant, a locked preset, a pulsing or shimmering
# On), never a default pick. Key → the values that still count as neutral.
_NEUTRAL_BY_KEY: dict[str, frozenset[str]] = {
    "T_CHOICE_LayerMethod": frozenset({"", "Normal"}),
    "B_CUSTOM_SubBuffer": frozenset({"", "0.00x0.00x100.00x100.00x0.00x0.00"}),
    "X_Effect_Locked": frozenset({""}),
    # A baked buffer transform is a sequencer's answer to THEIR prop's orientation (Danger
    # Zone's star pops are all Rotate CC 90); on ours it is arbitrary. A stack names it on purpose.
    "B_CHOICE_BufferTransform": frozenset({"", "None"}),
    # On with Cycles > 1 pulses and Shimmer flickers: fine when a brief asks, never as the
    # default bed (effect_meta gives On no speed row for the same reason).
    "E_TEXTCTRL_On_Cycles": frozenset({"", "1", "1.0", "1.00"}),
    "E_CHECKBOX_On_Shimmer": frozenset({"", "0"}),
    # Compositing nodes and designed exits: an Off with Canvas on and a layer selection is a
    # blend node in its author's stack; a wipe-out is a gesture.
    "T_CHECKBOX_Canvas": frozenset({"", "0"}),
    "T_LayersSelected": frozenset({""}),
    "T_CHOICE_In_Transition_Type": frozenset({"", "None"}),
    "T_CHOICE_Out_Transition_Type": frozenset({"", "None"}),
}


def _look_value(look, key: str) -> str | None:
    if key in look.frozen_base:
        return look.frozen_base[key]
    for knob in look.knobs:
        if knob.key == key:
            return knob.default or ""
    return None


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


def _neutral(look, keys: dict[str, frozenset[str]] = _NEUTRAL_BY_KEY) -> bool:
    for key, allowed in keys.items():
        if key in look.frozen_base and look.frozen_base[key] not in allowed:
            return False
    for knob in look.knobs:
        knob_allowed = keys.get(knob.key)
        if knob_allowed is not None and (knob.default or "") not in knob_allowed:
            return False
    return True


def _informative_keys(looks) -> dict[str, frozenset[str]]:
    """The neutrality keys that actually vary across a type's looks. Where every look of a
    type carries the same value (Warp and Kaleidoscope all need `Canvas` on), the key says
    nothing about design and is ignored for that type."""
    out: dict[str, frozenset[str]] = {}
    for key, allowed in _NEUTRAL_BY_KEY.items():
        if len({_look_value(lk, key) for lk in looks}) > 1:
            out[key] = allowed
    return out


@lru_cache(maxsize=None)
def pick_pool(effect_type: str) -> tuple[str, ...]:
    """The looks `pick_look` rotates among: the `PICK_POOL` most-used neutral looks (every
    ranked look when none is neutral; empty for an unknown type)."""
    lib = get_library()
    ranked = [lib.get_look(effect_type, lid) for lid in ranked_look_ids(effect_type)]
    keys = _informative_keys(ranked)
    neutral = [lk.look_id for lk in ranked if _neutral(lk, keys)]
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
