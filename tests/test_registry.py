"""Tests for the model registry — per-role provider overrides + pricing (F-H, I1).

Hermetic: no API key, no network (model_string/model_snapshot are pure config lookups)."""

from __future__ import annotations

import pytest

from xlights_orchestrator.models import registry


@pytest.fixture(autouse=True)
def _clear_cfg_cache():
    """`_cfg` is `lru_cache`d; a test that monkeypatches the config path (or env that a cached
    read already baked in) would leak into the next. Clear on entry AND exit."""
    registry._cfg.cache_clear()
    yield
    registry._cfg.cache_clear()


def test_per_role_override_beats_global(monkeypatch):
    monkeypatch.setenv("XLO_PROVIDER", "anthropic")
    monkeypatch.setenv("XLO_PROVIDER_JUDGE", "gemini")
    assert registry.model_string("judge").startswith("google:")       # role override wins
    assert registry.model_string("director").startswith("anthropic:")  # others follow the global


def test_model_snapshot_reflects_the_mix(monkeypatch):
    monkeypatch.setenv("XLO_PROVIDER", "gemini")
    monkeypatch.setenv("XLO_PROVIDER_JUDGE", "anthropic")
    snap = registry.model_snapshot()
    assert snap["judge"].startswith("anthropic:")
    assert snap["generator"].startswith("google:")


def test_provider_for_precedence(monkeypatch):
    monkeypatch.delenv("XLO_PROVIDER", raising=False)
    monkeypatch.delenv("XLO_PROVIDER_JUDGE", raising=False)
    assert registry.provider_for("judge") == "anthropic"              # config default
    monkeypatch.setenv("XLO_PROVIDER", "gemini")
    assert registry.provider_for("judge") == "gemini"                 # global override
    monkeypatch.setenv("XLO_PROVIDER_JUDGE", "anthropic")
    assert registry.provider_for("judge") == "anthropic"              # role override tops both


def test_unknown_role_raises(monkeypatch):
    monkeypatch.delenv("XLO_PROVIDER", raising=False)
    with pytest.raises(KeyError):
        registry.model_string("not_a_role")


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("XLO_PROVIDER_JUDGE", "not_a_provider")
    with pytest.raises(KeyError):
        registry.model_string("judge")


def test_every_role_has_every_provider():
    """Invariant: each role must resolve under each configured provider (guards a new role like
    visual_critic_lite being added without a provider row → runtime KeyError in an arm)."""
    cfg = registry._cfg()
    providers = list(cfg["providers"])
    for role, spec in cfg["roles"].items():
        for prov in providers:
            assert prov in spec, f"role {role!r} is missing provider {prov!r}"
            assert registry.model_string(role, provider=prov)         # resolves without error


def test_pricing_table_present():
    p = registry.pricing()
    assert "claude-opus-4-8" in p and "claude-sonnet-4-6" in p
    assert registry.price_for("anthropic:claude-opus-4-8")["input"] == 5.00
    # Gemini now priced from Google's published rates (ai.google.dev/gemini-api/docs/pricing, 2026)
    assert registry.price_for("google:gemini-3.5-flash")["input"] == 1.50
    assert registry.price_for("google:gemini-3.1-flash-lite")["output"] == 1.50
    assert registry.price_for("google:gemini-3.1-pro-preview")["input"] == 2.00


# -- model strings are provider-prefixed --------------------------------------

def test_model_strings_are_provider_prefixed():
    """Every role/provider pair resolves to a `<provider>:<model>` string (guards a config row
    that forgot the provider prefix or a stray model id)."""
    cfg = registry._cfg()
    for role in cfg["roles"]:
        for prov in cfg["providers"]:
            s = registry.model_string(role, provider=prov)
            assert s.startswith("anthropic:" if prov == "anthropic" else "google:")


def test_model_snapshot_covers_all_roles_both_providers(monkeypatch):
    all_roles = set(registry._cfg()["roles"])
    monkeypatch.setenv("XLO_PROVIDER", "anthropic")
    snap_a = registry.model_snapshot()
    assert set(snap_a) == all_roles
    assert all(v.startswith("anthropic:") for v in snap_a.values())
    registry._cfg.cache_clear()
    monkeypatch.setenv("XLO_PROVIDER", "gemini")
    snap_g = registry.model_snapshot()
    assert set(snap_g) == all_roles
    assert all(v.startswith("google:") for v in snap_g.values())


# -- _settings: the Opus-400 invariant + the TypedDict restyle (I4) -----------

_SAMPLING_KEYS = ("temperature", "top_p", "top_k")


def _as_dict(settings):
    return settings.__dict__ if hasattr(settings, "__dict__") else dict(settings)


def test_settings_thinking_and_effort_for_director():
    s = registry._settings("director")            # opus + thinking:adaptive + effort:high
    d = _as_dict(s)
    assert d.get("anthropic_thinking") == {"type": "adaptive"}
    assert d.get("anthropic_effort") == "high"
    assert not any(k in d for k in _SAMPLING_KEYS)   # Opus-400 invariant (registry.py:60)


def test_settings_thinking_without_effort_for_generator():
    s = registry._settings("generator")           # sonnet + thinking:adaptive, no effort row
    d = _as_dict(s)
    assert d.get("anthropic_thinking") == {"type": "adaptive"}
    assert "anthropic_effort" not in d
    assert not any(k in d for k in _SAMPLING_KEYS)


def test_settings_none_for_gemini_role():
    assert registry._settings("director", provider="gemini") is None
    assert registry._settings("judge", provider="gemini") is None


def test_build_agent_constructs_without_network(monkeypatch):
    from xlights_orchestrator.refine import JudgeVerdict
    # A dummy key lets the Anthropic provider instantiate; construction is still LAZY (no run,
    # so no network) — the point is `build_agent` wires model+output_type without an API call.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-real-key")
    agent = registry.build_agent("judge", output_type=JudgeVerdict, system_prompt="x")
    assert agent.model.model_name == "claude-opus-4-8"    # carries the resolved model
    assert agent.model.system == "anthropic"
    assert agent.output_type is JudgeVerdict
