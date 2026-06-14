"""Views over the preset library for the agents (placeable types, look/palette menus)."""

from __future__ import annotations

from xlights_core.knowledge import get_library

# Effect-type names xLights' addEffect genuinely rejects despite being in the corpus.
# Empty as of 2026-06-14: "Color Wash" was here, but a live re-test shows it now places
# (addEffect worked=true) and renders — its old worked=false was a casualty of the +-vs-%20
# GET-encoding bug (fixed 2026-06-10), which sent "Color Wash" as "Color+Wash". The set stays
# as the mechanism for any type that is ever confirmed truly unplaceable.
KNOWN_REJECTED_TYPES: set[str] = set()


def placeable_effect_types() -> list[str]:
    lib = get_library()
    return sorted(t for t in lib.list_effect_types() if t not in KNOWN_REJECTED_TYPES)


def candidate_look_ids(effect_type: str, *, limit: int = 12) -> list[str]:
    return [lk.look_id for lk in get_library().get_looks(effect_type, limit=limit)]


def palette_menu(*, limit: int = 12) -> list[dict]:
    return [{"palette_id": p.palette_id, "tags": p.tags}
            for p in get_library().get_palettes(limit=limit)]
