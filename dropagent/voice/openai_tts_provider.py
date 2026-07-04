"""OpenAI text-to-speech provider."""

from __future__ import annotations

from pathlib import Path

from dropagent.config import Settings
from dropagent.exceptions import ProviderNotAvailableError, TTSGenerationError
from dropagent.logging_config import get_logger
from dropagent.voice.base import BaseTTSProvider

log = get_logger(__name__)


class OpenAITTSProvider(BaseTTSProvider):
    name = "openai"

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ProviderNotAvailableError(
                "OPENAI_API_KEY is not set but TTS_PROVIDER=openai was requested."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderNotAvailableError(
                "The 'openai' package is required for OpenAITTSProvider."
            ) from exc

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._voice = settings.openai_tts_voice

    def synthesize(self, text: str, output_path: Path) -> Path:
        output_path = output_path.with_suffix(".mp3")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice=self._voice,
                input=text,
            ) as response:
                response.stream_to_file(str(output_path))
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise TTSGenerationError(f"OpenAI TTS request failed: {exc}") from exc

        log.info("OpenAI TTS narration written to %s", output_path)
        return output_path
