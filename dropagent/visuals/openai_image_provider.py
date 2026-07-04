"""OpenAI (DALL-E) image generation provider."""

from __future__ import annotations

import base64
from pathlib import Path

from dropagent.config import Settings
from dropagent.exceptions import ProviderNotAvailableError, VisualGenerationError
from dropagent.logging_config import get_logger
from dropagent.visuals.base import BaseImageProvider

log = get_logger(__name__)

_SUPPORTED_SIZES = {
    (1024, 1024): "1024x1024",
    (1024, 1792): "1024x1792",
    (1792, 1024): "1792x1024",
}


class OpenAIImageProvider(BaseImageProvider):
    name = "openai"

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ProviderNotAvailableError(
                "OPENAI_API_KEY is not set but IMAGE_PROVIDER=openai was requested."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderNotAvailableError(
                "The 'openai' package is required for OpenAIImageProvider."
            ) from exc

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_image_model

    def generate(self, prompt: str, output_path: Path, width: int, height: int) -> Path:
        size = _SUPPORTED_SIZES.get((width, height), "1024x1792")
        try:
            response = self._client.images.generate(
                model=self._model,
                prompt=prompt,
                size=size,
                n=1,
                response_format="b64_json",
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise VisualGenerationError(f"OpenAI image generation failed: {exc}") from exc

        image_b64 = response.data[0].b64_json
        output_path = output_path.with_suffix(".png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(image_b64))
        log.info("OpenAI image written to %s", output_path)
        return output_path
