"""Tests for the model provider factory."""

import pytest

from miminions.agent.provider import ModelFactory


def test_openrouter_fails_fast_without_api_key(monkeypatch):
    """Missing OPENROUTER_API_KEY should raise a clear error, not default to ''."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        ModelFactory.create("openrouter")


def test_openrouter_builds_model_with_api_key(monkeypatch):
    """With the key set, the openrouter provider builds a model object."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    model = ModelFactory.create("openrouter")

    assert model is not None


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        ModelFactory.create("nope")
