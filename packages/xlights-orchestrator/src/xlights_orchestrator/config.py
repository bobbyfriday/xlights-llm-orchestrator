"""Environment/config loading for the orchestrator."""

from __future__ import annotations

import os
from pathlib import Path


def load_env() -> None:
    """Load a .env from the repo root (or cwd) if present. No-op if absent."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # walk up from cwd looking for a .env
    here = Path.cwd()
    for d in [here, *here.parents]:
        env = d / ".env"
        if env.exists():
            load_dotenv(env)
            return
    load_dotenv()  # fallback to default search


def has_llm_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY"))
