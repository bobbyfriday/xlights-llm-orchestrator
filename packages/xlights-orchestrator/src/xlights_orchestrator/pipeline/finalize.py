"""Finalize: save the sequence, then patch the .xsq OFFLINE.

Audio, render order and timing tracks are patched into the saved .xsq with the file
released — attaching media / reordering via the live API crashes xLights. Best-effort:
a patch failure logs and never fails the run.
"""

from __future__ import annotations

import logging

from xlights_core.knowledge.layout_semantics import patch_xsq_render_order

from .media import patch_xsq_media, resolve_xsq
from .state import State
from .timing import build_timing_tracks, patch_xsq_timing_tracks

log = logging.getLogger(__name__)


async def finalize_sequence(st: State, *, client, save_as: str, media, show_folder,
                            duration_s: float, timing_tracks: bool) -> None:
    await client.save_sequence(save_as)
    if media is None and not timing_tracks:
        return
    try:    # patch the .xsq OFFLINE (live edits crash xLights)
        await client.close_sequence(force=True, quiet=True)   # release the file before patching
        xsq = resolve_xsq(save_as, show_folder)
        if xsq and media is not None and patch_xsq_media(xsq, media, duration_s):
            log.info("audio attached to %s — open '%s' in xLights to play with sound", xsq, save_as)
        if xsq and not patch_xsq_render_order(xsq):   # beds under, features/accents over
            from ..degradations import note            # observe the discarded bool at the seam
            note("finalize:xsq-patch", f"render-order patch reported no change for {xsq}",
                 stage="finalize", level=logging.DEBUG)
        if xsq and timing_tracks:             # reference grid for hand-editing (best-effort)
            tracks = build_timing_tracks(
                st.song_analysis, st.music_brief,
                fallback_sections=st.show_plan.sections if st.show_plan else None)
            if patch_xsq_timing_tracks(xsq, tracks):
                log.info("added %d reference timing tracks to %s", len(tracks), xsq)
    except Exception as exc:  # noqa: BLE001 — patch is best-effort, never fails the run
        from ..degradations import note
        note("finalize:xsq-patch", exc, stage="finalize")
