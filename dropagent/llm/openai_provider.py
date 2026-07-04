"""OpenAI chat-completion provider."""

from __future__ import annotations

from dropagent.config import Settings
from dropagent.exceptions import LLMGenerationError, ProviderNotAvailableError
from dropagent.llm.base import BaseLLMProvider
from dropagent.logging_config import get_logger

log = get_logger(__name__)


class OpenAILLMProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ProviderNotAvailableError(
                "OPENAI_API_KEY is not set but LLM_PROVIDER=openai was requested."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderNotAvailableError(
                "The 'openai' package is required for OpenAILLMProvider. Install it with "
                "`pip install openai`."
            ) from exc

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_text_model

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.9,
        max_tokens: int = 1500,
    ) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            log.exception("OpenAI completion failed")
            raise LLMGenerationError(f"OpenAI completion failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMGenerationError("OpenAI returned an empty completion")
        return content.strip()
