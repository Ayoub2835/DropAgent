"""Factory that resolves the configured LLM provider into a concrete instance."""

from __future__ import annotations

from dropagent.config import Settings, get_settings
from dropagent.exceptions import ConfigurationError, ProviderNotAvailableError
from dropagent.llm.base import BaseLLMProvider
from dropagent.logging_config import get_logger

log = get_logger(__name__)


def get_llm_provider(settings: Settings | None = None) -> BaseLLMProvider:
    """Instantiate the LLM provider selected by ``LLM_PROVIDER``.

    Falls back to the deterministic ``mock`` provider (with a warning) if the
    requested provider is misconfigured, so the pipeline never hard-crashes
    during local experimentation without API keys.
    """
    settings = settings or get_settings()
    provider = settings.llm_provider

    try:
        if provider == "openai":
            from dropagent.llm.openai_provider import OpenAILLMProvider

            return OpenAILLMProvider(settings)
        if provider == "anthropic":
            from dropagent.llm.anthropic_provider import AnthropicLLMProvider

            return AnthropicLLMProvider(settings)
        if provider == "mock":
            from dropagent.llm.mock_provider import MockLLMProvider

            return MockLLMProvider()
        raise ConfigurationError(f"Unknown LLM_PROVIDER '{provider}'. Use openai, anthropic or mock.")
    except ProviderNotAvailableError as exc:
        log.warning("%s -- falling back to the offline mock LLM provider.", exc)
        from dropagent.llm.mock_provider import MockLLMProvider

        return MockLLMProvider()
