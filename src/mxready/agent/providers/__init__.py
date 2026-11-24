"""Build a provider from non-secret configuration and an in-memory API key."""

from __future__ import annotations

from mxready.agent.config import ProviderConfig
from mxready.agent.providers.base import ChatProvider, ProviderError


def build_provider(config: ProviderConfig, api_key: str) -> ChatProvider:
    if not api_key.strip():
        raise ProviderError("missing-key", "No API key is configured for this provider")
    if config.protocol == "openai":
        from mxready.agent.providers.openai import OpenAIProvider

        return OpenAIProvider(config, api_key)
    if config.protocol == "anthropic":
        from mxready.agent.providers.anthropic import AnthropicProvider

        return AnthropicProvider(config, api_key)
    raise ProviderError("unsupported-protocol", f"Unsupported protocol: {config.protocol}")
