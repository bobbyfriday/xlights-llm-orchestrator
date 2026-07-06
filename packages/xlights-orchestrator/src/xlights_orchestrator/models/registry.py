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

import httpx
import yaml
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from xlights_core.retry import with_retry

_CONFIG = Path(__file__).parent / "config.yaml"

# Provider-overload / rate-limit / transient statuses worth a bounded retry. Deliberately NOT
# "5xx ⇒ retry": a 400/401/403/404/413/422 schema/auth/bad-request failure repeats identically
# at full input-token cost. 529 is Anthropic's overloaded_error; 408/429/500/502/503 cover the
# general provider-transient surface.
_TRANSIENT_HTTP = {408, 429, 500, 502, 503, 529}


def llm_transient(exc: BaseException) -> bool:
    """The LLM retry predicate — isolated in ONE function next to its taxonomy so a PydanticAI
    rename fails this unit test, not a run. Retries provider overload/rate-limit/timeout classes
    (HTTP 408/429/500/502/503/529 and escaping httpx transport/timeout errors); never retries
    validation (``UnexpectedModelBehavior``/``pydantic.ValidationError``), auth/bad-request
    (400/401/403/404/413/422), content-filter, or usage-limit errors.
    """
    if isinstance(exc, ModelHTTPError):
        return exc.status_code in _TRANSIENT_HTTP
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))


async def run_agent(agent: Any, prompt: Any, *, role: str = "", attempts: int = 3) -> Any:
    """Run ``agent.run(prompt)`` under bounded transient-only retry (the single LLM seam).

    Callable-wrapping keeps the retry visible and never wraps an injected fake invisibly: a
    hermetic TestModel fake never raises a transient class, so it is called exactly once and the
    golden snapshot / existing tests are byte-identical. PydanticAI's own output-validation
    ``retries`` (schema re-prompting) is a different mechanism and is untouched here.
    """
    return await with_retry(lambda: agent.run(prompt),
                            retryable=llm_transient, attempts=attempts, label=f"llm:{role}")


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
