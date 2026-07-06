"""Tests for the model registry — per-role provider overrides + pricing (F-H, I1).

Hermetic: no API key, no network (model_string/model_snapshot are pure config lookups)."""

from __future__ import annotations

import pytest

from xlights_orchestrator.models import registry


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
