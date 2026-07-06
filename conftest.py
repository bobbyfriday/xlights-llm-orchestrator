"""Repo-root pytest config: make top-level `scripts/` importable from tests.

`scripts/measure_fabric.py` is the fabric-measurement tool (new capability `fabric-measurement`);
its `stats_from_instructions`/`stats_from_xsq`/`FabricStats` are unit-tested and the golden canary
imports them, so the repo root goes on `sys.path` for the test session.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SCRIPTS = _ROOT / "scripts"
for _p in (_ROOT, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
