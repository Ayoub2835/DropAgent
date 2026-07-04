"""ElevenLabs text-to-speech provider (high-quality, paid API)."""

from __future__ import annotations

from pathlib import Path

import requests

from dropagent.config import Settings
from dropagent.exceptions import ProviderNotAvailableError, TTSGenerationError
from dropagent.logging_config import get_logger
from dropagent.voice.base import BaseTTSProvider

log = get_logger(__name__)

_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class ElevenLabsTTSProvider(BaseTTSProvider):
    name = "elevenlabs"

    def __init__(self, settings: Settings):
        if not settings.elevenlabs_api_key:
            raise ProviderNotAvailableError(
                "ELEVENLABS_API_KEY is not set but TTS_PROVIDER=elevenlabs was requested."
            )
        self._api_key = settings.elevenlabs_api_key
        self._voice_id = settings.elevenlabs_voice_id

    def synthesize(self, text: str, output_path: Path) -> Path:
        output_path = output_path.with_suffix(".mp3")
        url = _API_URL.format(voice_id=self._voice_id)
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TTSGenerationError(f"ElevenLabs TTS request failed: {exc}") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        log.info("ElevenLabs narration written to %s", output_path)
        return output_path
