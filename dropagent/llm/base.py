"""Abstract interface every LLM text-generation provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """A minimal chat-completion contract.

    Every concrete provider (OpenAI, Anthropic, ...) only needs to implement
    ``complete``. Keeping the interface to a single method makes it trivial
    to add new providers or a deterministic offline stub for tests.
    """

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.9,
        max_tokens: int = 1500,
    ) -> str:
        """Return the raw text completion for the given prompts."""
        raise NotImplementedError
