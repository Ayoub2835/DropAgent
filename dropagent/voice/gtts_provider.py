"""Google Translate TTS provider via the free `gTTS` library.

Requires no API key -- good default for local development and demos -- but
does need outbound internet access. For a fully offline story, use
``TTS_PROVIDER=pyttsx3`` instead.
"""

from __future__ import annotations

from pathlib import Path

from dropagent.config import Settings
from dropagent.exceptions import ProviderNotAvailableError, TTSGenerationError
from dropagent.logging_config import get_logger
from dropagent.voice.base import BaseTTSProvider

log = get_logger(__name__)


class GTTSProvider(BaseTTSProvider):
    name = "gtts"

    def __init__(self, settings: Settings):
        try:
            from gtts import gTTS  # noqa: F401
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderNotAvailableError(
                "The 'gTTS' package is required for GTTSProvider. Install it with `pip install gTTS`."
            ) from exc
        self._language = settings.tts_language

    def synthesize(self, text: str, output_path: Path) -> Path:
        from gtts import gTTS
        from gtts.tts import gTTSError

        output_path = output_path.with_suffix(".mp3")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            gTTS(text=text, lang=self._language).save(str(output_path))
        except gTTSError as exc:
            raise TTSGenerationError(f"gTTS synthesis failed: {exc}") from exc

        log.info("gTTS narration written to %s", output_path)
        return output_path
