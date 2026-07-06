"""Structural audit: ban silent best-effort swallows (I5's no-silent-pass convention).

Walks every source file in both packages and fails any ``except`` handler whose body neither
logs (a ``log.*`` / ``logging.*`` call), records a degradation (a ``note(`` / ``note_once(``
call), nor re-raises. This is the going-forward guard so a new best-effort block can't sneak in
a bare ``pass``. The stdlib-browser servers (``server.py``/``brief_editor.py``) that re-raise as
HTTP errors are auto-skipped.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = [
    ROOT / "packages" / "xlights-core" / "src" / "xlights_core",
    ROOT / "packages" / "xlights-orchestrator" / "src" / "xlights_orchestrator",
]
# These implement HTTP handlers that translate exceptions into responses (out of scope):
# a malformed request is answered with a 4xx status, which IS the report.
SKIP_NAMES = {"server.py", "brief_editor.py", "live_server.py"}


def _handler_is_ok(handler: ast.ExceptHandler) -> bool:
    """True if the handler body logs, records a degradation, or re-raises (anywhere in it)."""
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            # log.<level>(...) / logging.<level>(...)
            if isinstance(func, ast.Attribute):
                if func.attr in {"debug", "info", "warning", "warn", "error",
                                 "exception", "critical", "log"}:
                    return True
            # note(...) / note_once(...) — the degradations collector
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name in {"note", "note_once"}:
                return True
    return False


def _offenders_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        # only broad `except Exception`/bare `except:` handlers are in scope (specific
        # exception types like `except ImportError: continue` are legitimate control flow).
        exc = node.type
        broad = exc is None or (isinstance(exc, ast.Name) and exc.id in {"Exception", "BaseException"})
        if not broad:
            continue
        if not _handler_is_ok(node):
            bad.append(f"{path.name}:{node.lineno}")
    return bad


def test_no_silent_best_effort_swallows():
    offenders: list[str] = []
    for base in SRC_DIRS:
        for py in base.rglob("*.py"):
            if py.name in SKIP_NAMES:
                continue
            offenders.extend(_offenders_in(py))
    assert not offenders, (
        "silent best-effort handlers (no log/note/raise) — every best-effort `except Exception` "
        "must log at least at debug, record a degradation, or re-raise:\n  " + "\n  ".join(offenders)
    )
