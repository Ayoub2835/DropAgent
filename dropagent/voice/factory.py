"""Factory that resolves the configured TTS provider into a concrete instance."""

from __future__ import annotations

from dropagent.config import Settings, get_settings
from dropagent.exceptions import ConfigurationError, ProviderNotAvailableError
from dropagent.logging_config import get_logger
from dropagent.voice.base import BaseTTSProvider

log = get_logger(__name__)

_FALLBACK_ORDER = ["gtts", "pyttsx3"]


def get_tts_provider(settings: Settings | None = None) -> BaseTTSProvider:
    """Instantiate the TTS provider selected by ``TTS_PROVIDER``.

    Falls back through ``gtts`` -> ``pyttsx3`` if the requested provider is
    unavailable (missing key/dependency), so a run never hard-fails purely
    because narration credentials are missing.
    """
    settings = settings or get_settings()
    return _build(settings.tts_provider, settings)


def _build(provider: str, settings: Settings) -> BaseTTSProvider:
    try:
        if provider == "elevenlabs":
            from dropagent.voice.elevenlabs_provider import ElevenLabsTTSProvider

            return ElevenLabsTTSProvider(settings)
        if provider == "openai":
            from dropagent.voice.openai_tts_provider import OpenAITTSProvider

            return OpenAITTSProvider(settings)
        if provider == "gtts":
            from dropagent.voice.gtts_provider import GTTSProvider

            return GTTSProvider(settings)
        if provider == "pyttsx3":
            from dropagent.voice.pyttsx3_provider import Pyttsx3Provider

            return Pyttsx3Provider(settings)
        raise ConfigurationError(
            f"Unknown TTS_PROVIDER '{provider}'. Use elevenlabs, openai, gtts or pyttsx3."
        )
    except ProviderNotAvailableError as exc:
        log.warning("%s -- trying fallback TTS providers.", exc)
        for fallback in _FALLBACK_ORDER:
            if fallback == provider:
                continue
            try:
                return _build(fallback, settings)
            except ProviderNotAvailableError:
                continue
        raise ProviderNotAvailableError(
            "No TTS provider could be initialized (tried "
            f"'{provider}' and fallbacks {_FALLBACK_ORDER})."
        ) from exc
