"""Per-song stage cache paths. Resume = cached stage artifacts keyed by song content hash.

LLM-stage artifacts (song_description, creative_brief, instructions, visual_review) are
additionally namespaced under a fingerprint of the active per-role model routing (`models=True`),
so two provider routings never read each other's artifacts — this turns
`XLO_PROVIDER=gemini xlo run` from silently-wrong into correct, and lets an A/B keep two arms'
caches apart. Deterministic, provider-independent artifacts (song_analysis, the
layout-fingerprinted targetable-groups probe, the revision log) stay shared. There is NO
legacy-path read fallback (it would re-open the cross-provider reuse bug); pre-change caches go
cold once and regenerate on the next run.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def cache_root() -> Path:
    return Path(os.environ.get("XLO_CACHE_DIR", "data")) / "orchestrator"


def song_key(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def models_fingerprint() -> str:
    """A stable 8-hex fingerprint of the whole per-role model snapshot. Over-invalidates slightly
    (any role change re-namespaces all LLM stages) but is impossible to get wrong, and the stage
    inputs are transitively coupled anyway."""
    from ..models.registry import model_snapshot
    snap = model_snapshot()
    blob = json.dumps(snap, sort_keys=True).encode()
    return "m-" + hashlib.sha1(blob).hexdigest()[:8]


def cache_path(key: str, stage: str, *, models: bool = False) -> Path:
    """Path for a per-song stage artifact. `models=True` namespaces it under the active model
    routing's fingerprint (LLM stages); `models=False` (default) is the shared, un-namespaced
    location (deterministic stages, the revision log)."""
    base = cache_root() / key
    if models:
        base = base / models_fingerprint()
    return base / f"{stage}.json"
