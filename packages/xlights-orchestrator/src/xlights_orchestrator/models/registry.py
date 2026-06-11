"""Per-role model routing: role -> PydanticAI model string + settings.

Routing is data-driven (config.yaml), so a role can be re-pointed at a different
provider/model with no code change. Claude settings use adaptive thinking + effort;
sampling params (temperature/top_p/top_k) are never set (removed on Opus 4.8 → 400).
"""

from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic_ai import Agent

_CONFIG = Path(__file__).parent / "config.yaml"


@functools.lru_cache(maxsize=1)
def _cfg() -> dict[str, Any]:
    return yaml.safe_load(_CONFIG.read_text())


def active_provider() -> str:
    """Provider in effect: XLO_PROVIDER env override, else config default."""
    return os.environ.get("XLO_PROVIDER") or _cfg().get("default_provider", "anthropic")


def model_string(role: str, *, provider: str | None = None) -> str:
    cfg = _cfg()
    prov = provider or active_provider()
    spec = cfg["roles"][role][prov]
    return f"{cfg['providers'][prov]}{spec['model']}"


def model_snapshot() -> dict[str, str]:
    """role -> 'provider:model' for every configured role (for the revision log)."""
    prov = active_provider()
    out: dict[str, str] = {}
    for role, spec in _cfg().get("roles", {}).items():
        if prov in spec:
            out[role] = model_string(role)
    return out


def _settings(role: str, *, provider: str | None = None):
    prov = provider or active_provider()
    if prov != "anthropic":
        return None  # Gemini etc. use provider defaults for the skeleton
    from pydantic_ai.models.anthropic import AnthropicModelSettings

    spec = _cfg()["roles"][role]["anthropic"]
    kw: dict[str, Any] = {}
    if spec.get("thinking") == "adaptive":
        kw["anthropic_thinking"] = {"type": "adaptive"}
    if spec.get("effort"):
        kw["anthropic_effort"] = spec["effort"]
    # Deliberately never set temperature/top_p/top_k (removed on Opus → 400).
    return AnthropicModelSettings(**kw) if kw else None


def build_agent(role: str, *, output_type, system_prompt: str) -> Agent:
    """Construct a PydanticAI Agent for a role. Lazy: no API call at construction."""
    return Agent(
        model_string(role),
        output_type=output_type,
        system_prompt=system_prompt,
        model_settings=_settings(role),
    )
