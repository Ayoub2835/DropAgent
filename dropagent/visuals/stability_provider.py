"""Stability AI (Stable Diffusion) image generation provider."""

from __future__ import annotations

from pathlib import Path

import requests

from dropagent.config import Settings
from dropagent.exceptions import ProviderNotAvailableError, VisualGenerationError
from dropagent.logging_config import get_logger
from dropagent.visuals.base import BaseImageProvider

log = get_logger(__name__)

_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"


class StabilityImageProvider(BaseImageProvider):
    name = "stability"

    def __init__(self, settings: Settings):
        if not settings.stability_api_key:
            raise ProviderNotAvailableError(
                "STABILITY_API_KEY is not set but IMAGE_PROVIDER=stability was requested."
            )
        self._api_key = settings.stability_api_key

    def generate(self, prompt: str, output_path: Path, width: int, height: int) -> Path:
        aspect_ratio = "9:16" if height > width else ("16:9" if width > height else "1:1")
        headers = {"authorization": f"Bearer {self._api_key}", "accept": "image/*"}
        files = {"none": ""}
        data = {"prompt": prompt, "output_format": "png", "aspect_ratio": aspect_ratio}

        try:
            response = requests.post(_API_URL, headers=headers, files=files, data=data, timeout=90)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise VisualGenerationError(f"Stability AI image generation failed: {exc}") from exc

        output_path = output_path.with_suffix(".png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        log.info("Stability AI image written to %s", output_path)
        return output_path
