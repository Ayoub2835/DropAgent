"""Anthropic (Claude) chat-completion provider."""

from __future__ import annotations

from dropagent.config import Settings
from dropagent.exceptions import LLMGenerationError, ProviderNotAvailableError
from dropagent.llm.base import BaseLLMProvider
from dropagent.logging_config import get_logger

log = get_logger(__name__)


class AnthropicLLMProvider(BaseLLMProvider):
    name = "anthropic"

    def __init__(self, settings: Settings):
        if not settings.anthropic_api_key:
            raise ProviderNotAvailableError(
                "ANTHROPIC_API_KEY is not set but LLM_PROVIDER=anthropic was requested."
            )
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderNotAvailableError(
                "The 'anthropic' package is required for AnthropicLLMProvider. Install it "
                "with `pip install anthropic`."
            ) from exc

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_text_model

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.9,
        max_tokens: int = 1500,
    ) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            log.exception("Anthropic completion failed")
            raise LLMGenerationError(f"Anthropic completion failed: {exc}") from exc

        text_blocks = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        content = "\n".join(text_blocks).strip()
        if not content:
            raise LLMGenerationError("Anthropic returned an empty completion")
        return content
