"""Demo: build a visible multi-effect xLights sequence from the preset library.

Creates a NEW sequence (your saved shows are untouched), places a variety of preset
effects on real models across the timeline, renders, saves it, and LEAVES IT OPEN so
you can watch it in the xLights sequencer and press play.

Run (with the venv active, xLights running, no unsaved sequence open):
    python scripts/demo_build_sequence.py
"""

from __future__ import annotations

import asyncio

from xlights_core import (
    XLightsClient,
    XLightsResponseError,
    XLightsTargetMissing,
    XLightsUnsavedChanges,
)
from xlights_core.editing import PresetPlacementError, place_preset
from xlights_core.knowledge import get_library

DURATION_S = 20
WINDOW_MS = DURATION_S * 1000
SAVE_AS = "LLM_ORCH_DEMO"

# A varied, visual mix of self-contained effect types.
EFFECT_TYPES = ["On", "Bars", "Butterfly", "Spirals", "Color Wash",
                "Shockwave", "Pinwheel", "SingleStrand", "Ripple", "Fan"]


async def ensure_clean_slate(c: XLightsClient) -> None:
    try:
        await c.new_sequence(duration_secs=DURATION_S, frame_ms=50)
        return
    except XLightsResponseError as exc:
        if "already open" not in (exc.message or "").lower():
            raise
    # something is open — close it only if it has no unsaved changes
    try:
        await c.close_sequence(quiet=True)
    except XLightsUnsavedChanges:
        raise SystemExit("xLights has an unsaved sequence open — save/close it first, then re-run.")
    await c.new_sequence(duration_secs=DURATION_S, frame_ms=50)


async def main() -> None:
    lib = get_library()
    # a colorful palette if available, else any
    palettes = lib.get_palettes(tag="count:6") or lib.get_palettes(limit=1)
    palette_id = palettes[0].palette_id if palettes else None

    async with XLightsClient() as c:
        print(f"xLights {await c.get_version()} — building demo sequence…")
        await ensure_clean_slate(c)
        await asyncio.sleep(3.0)  # let the sequencer finish populating elements (racy/variable)

        # A fresh API-created sequence contains GROUPS as elements (most of them) but
        # not standalone models — so we target groups (which also drive many props at once).
        targets = await c.get_group_names()
        if not targets:
            raise SystemExit("no groups in layout")

        # Assign each effect type to a distinct group. Skip groups that aren't elements
        # of this sequence (XLightsTargetMissing), and skip effect types that xLights
        # won't place by name (PresetPlacementError, e.g. "Color Wash").
        placed, rejected_types, gi = [], [], 0
        for etype in EFFECT_TYPES:
            looks = lib.get_looks(etype)
            if not looks:
                continue
            placed_this = False
            while gi < len(targets):
                target = targets[gi]; gi += 1
                try:
                    await place_preset(c, target, etype, looks[0].look_id,
                                       palette_id=palette_id, start_ms=0, end_ms=WINDOW_MS)
                    placed.append((etype, target))
                    print(f"  + {etype:<12} on  {target}")
                    await asyncio.sleep(0.4)  # watch them appear one-by-one in xLights
                    placed_this = True
                    break
                except XLightsTargetMissing:
                    continue  # group not an element here — try the next group
                except PresetPlacementError:
                    rejected_types.append(etype)  # xLights won't place this type by name
                    break
            if not placed_this and etype not in rejected_types:
                break  # ran out of usable groups

        if rejected_types:
            print(f"  (skipped effect types xLights rejected: {', '.join(rejected_types)})")
        print("rendering…")
        await c.render_all()
        await c.save_sequence(SAVE_AS)
        print(f"\n✓ placed {len(placed)} effects; saved as '{SAVE_AS}.xsq' and left OPEN in xLights.")
        print("  Look at the xLights sequencer grid, scrub the timeline, or press play.")


if __name__ == "__main__":
    asyncio.run(main())
