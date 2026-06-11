"""Views over the preset library for the agents (placeable types, look/palette menus)."""

from __future__ import annotations

from xlights_core.knowledge import get_library

# Effect-type names xLights' addEffect rejects despite being in the corpus (see memory).
KNOWN_REJECTED_TYPES = {"Color Wash"}


def placeable_effect_types() -> list[str]:
    lib = get_library()
    return sorted(t for t in lib.list_effect_types() if t not in KNOWN_REJECTED_TYPES)


def candidate_look_ids(effect_type: str, *, limit: int = 12) -> list[str]:
    return [lk.look_id for lk in get_library().get_looks(effect_type, limit=limit)]


def palette_menu(*, limit: int = 12) -> list[dict]:
    return [{"palette_id": p.palette_id, "tags": p.tags}
            for p in get_library().get_palettes(limit=limit)]
