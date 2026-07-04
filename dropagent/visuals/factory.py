"""Factory that resolves the configured image provider into a concrete instance."""

from __future__ import annotations

from dropagent.config import Settings, get_settings
from dropagent.exceptions import ConfigurationError, ProviderNotAvailableError
from dropagent.logging_config import get_logger
from dropagent.visuals.base import BaseImageProvider

log = get_logger(__name__)


def get_image_provider(settings: Settings | None = None) -> BaseImageProvider:
    """Instantiate the image provider selected by ``IMAGE_PROVIDER``.

    Falls back to the offline ``placeholder`` provider if the requested
    provider is unavailable, so scene visuals are always produced.
    """
    settings = settings or get_settings()
    provider = settings.image_provider

    try:
        if provider == "openai":
            from dropagent.visuals.openai_image_provider import OpenAIImageProvider

            return OpenAIImageProvider(settings)
        if provider == "stability":
            from dropagent.visuals.stability_provider import StabilityImageProvider

            return StabilityImageProvider(settings)
        if provider == "placeholder":
            from dropagent.visuals.placeholder_provider import PlaceholderImageProvider

            return PlaceholderImageProvider()
        raise ConfigurationError(
            f"Unknown IMAGE_PROVIDER '{provider}'. Use openai, stability or placeholder."
        )
    except ProviderNotAvailableError as exc:
        log.warning("%s -- falling back to the offline placeholder image provider.", exc)
        from dropagent.visuals.placeholder_provider import PlaceholderImageProvider

        return PlaceholderImageProvider()
