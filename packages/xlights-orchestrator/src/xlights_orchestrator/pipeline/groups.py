"""Determine which prop groups xLights will actually accept effects on.

`get_group_names()` returns every layout group, but many (nested groups, empty/stale
members) raise `XLightsTargetMissing` on `addEffect` → skipped effects → black sections.
Targetability isn't reliably derivable from the layout file, so we probe it empirically
(a trivial effect per group on a disposable sequence) and cache it per layout.
See [[sequence-elements-vs-groups]].
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

from xlights_core.editing import place_preset
from xlights_core.exceptions import XLightsTargetMissing

from .. import degradations
from ..agents.generator import candidate_look_ids

log = logging.getLogger(__name__)

_SETTLE_SECS = 0.8     # let sequence elements populate before probing (racy — mirrors the emitter)


def _fingerprint(groups: list[str], models: list[str]) -> str:
    # Group names AND model names: a membership-affecting layout edit (models
    # added/removed/renamed under unchanged group names) must invalidate the cache.
    key = ",".join(sorted(groups)) + "|" + ",".join(sorted(models))
    return hashlib.sha1(key.encode()).hexdigest()[:16]


async def targetable_groups(client, *, cache_root: Path) -> list[str]:
    """The subset of prop groups xLights accepts effects on (cached per layout).

    A failed *listing* (``get_group_names``) FAILS FAST — it re-raises rather than limping on an
    empty list. An empty ``available_groups`` has no useful degraded mode: it poisons the Director
    prompt ("choose from: nothing") and produces a garbage cached brief AFTER paying for analysis +
    panel + director tokens, so raising early fails before any LLM spend. A failed *probe* (below)
    keeps its sane full-list fallback; only the listing itself is fatal. A genuinely empty layout
    that lists successfully returns ``[]`` normally.
    """
    names = await client.get_group_names()   # a failed listing propagates — see the docstring
    if not names:
        return names
    try:
        model_names = await client.get_model_names()
    except Exception as exc:  # noqa: BLE001 — fingerprint enrichment only; group names still key
        log.debug("targetable_groups: get_model_names for fingerprint failed: %s", exc)
        model_names = []

    cache_file = Path(cache_root) / f"targetable_groups_{_fingerprint(names, model_names)}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except Exception as exc:  # noqa: BLE001 — corrupt cache → re-probe
            log.debug("targetable_groups: corrupt cache, re-probing: %s", exc)

    try:
        targetable = await _probe(client, names)
    except Exception as exc:  # noqa: BLE001 — non-target error / setup failure → full list, no cache
        degradations.note("groups:probe", exc, stage="groups")
        return names
    if not targetable:                       # empty → don't trust it; fall back, don't cache
        log.warning("targetable_groups: probe found none targetable; using all groups")
        return names

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(targetable))
    log.info("targetable_groups: %d/%d groups are addEffect-able (cached)", len(targetable), len(names))
    return targetable


async def _probe(client, names: list[str]) -> list[str]:
    """Place a trivial effect on each group on a disposable sequence; keep the ones xLights
    accepts. Raises (→ caller falls back) on any non-`XLightsTargetMissing` error."""
    look = candidate_look_ids("On")[0]
    await client.close_sequence(force=True, quiet=True)
    await client.new_sequence(duration_secs=10, frame_ms=50, force=True)
    await asyncio.sleep(_SETTLE_SECS)        # elements populate (racy) — load-bearing
    ok: list[str] = []
    try:
        for name in names:
            try:
                await place_preset(client, name, "On", look, layer=0, start_ms=0, end_ms=500)
                ok.append(name)
            except XLightsTargetMissing:
                continue                     # this group isn't targetable — the ONLY exclusion reason
    finally:
        try:
            await client.close_sequence(force=True, quiet=True)   # discard the disposable sequence
        except Exception as exc:  # noqa: BLE001 — cleanup only; the probe result already stands
            log.debug("targetable_groups: probe cleanup close failed: %s", exc)
    return ok
