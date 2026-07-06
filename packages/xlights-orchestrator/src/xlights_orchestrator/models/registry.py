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


# -- pricing (prices are DATA in config.yaml; cost is a pure function) ---------

def pricing() -> dict[str, dict[str, float]]:
    """The per-model price table (USD per 1M tokens, keyed by bare model id)."""
    return _cfg().get("pricing", {}) or {}


def _bare_model_id(model: str) -> str:
    """`anthropic:claude-opus-4-8` / `google:gemini-...` -> the bare id used as a price key."""
    return model.split(":", 1)[1] if ":" in model else model


def price_for(model: str) -> dict[str, float] | None:
    """Per-1M-token rates for a model id (bare or provider-prefixed), or None if unpriced."""
    return pricing().get(_bare_model_id(model))


def estimate_cost(models: dict[str, str], usage: dict) -> float | None:
    """Sum over roles of token counts × that role's model rates (per 1M tokens).

    `usage` maps role -> a RoleUsage-like object (``.input_tokens``/``.output_tokens``/
    ``.cache_read_tokens``/``.cache_write_tokens``). Cache-read and cache-write tokens are
    priced at their own rates. Returns None if ANY role with nonzero usage runs on a model
    with no price row (unknown ≠ zero); 0.0 only when there was genuinely no priced spend.
    """
    total = 0.0
    for role, u in usage.items():
        toks = ((getattr(u, "input_tokens", 0) or 0) + (getattr(u, "output_tokens", 0) or 0)
                + (getattr(u, "cache_read_tokens", 0) or 0) + (getattr(u, "cache_write_tokens", 0) or 0))
        if not toks:
            continue                                   # a role with zero usage never forces unknown
        rates = price_for(models.get(role, "")) if models else None
        if rates is None:
            return None                                # a priced-run needs a rate for every used role
        total += ((getattr(u, "input_tokens", 0) or 0) * rates.get("input", 0.0)
                  + (getattr(u, "output_tokens", 0) or 0) * rates.get("output", 0.0)
                  + (getattr(u, "cache_read_tokens", 0) or 0) * rates.get("cache_read", 0.0)
                  + (getattr(u, "cache_write_tokens", 0) or 0) * rates.get("cache_write", 0.0))
    return total / 1_000_000


def active_provider() -> str:
    """Global provider in effect: XLO_PROVIDER env override, else config default."""
    return os.environ.get("XLO_PROVIDER") or _cfg().get("default_provider", "anthropic")


def provider_for(role: str) -> str:
    """The provider for ONE role: `XLO_PROVIDER_<ROLE>` > `XLO_PROVIDER` > config default.

    Per-role overrides let a mixed A/B arm route individual roles to different providers
    (`XLO_PROVIDER_JUDGE=gemini xlo run …`) with no code change, and make the logged model
    snapshot truthful for that mix."""
    return os.environ.get(f"XLO_PROVIDER_{role.upper()}") or active_provider()


def model_string(role: str, *, provider: str | None = None) -> str:
    cfg = _cfg()
    prov = provider or provider_for(role)
    spec = cfg["roles"][role][prov]
    return f"{cfg['providers'][prov]}{spec['model']}"


def model_snapshot() -> dict[str, str]:
    """role -> 'provider:model' for every configured role, resolved PER ROLE (for the revision
    log — so a mixed arm's snapshot reflects the true per-role provider mix)."""
    out: dict[str, str] = {}
    for role, spec in _cfg().get("roles", {}).items():
        if provider_for(role) in spec:
            out[role] = model_string(role)
    return out


def _settings(role: str, *, provider: str | None = None):
    prov = provider or provider_for(role)
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
