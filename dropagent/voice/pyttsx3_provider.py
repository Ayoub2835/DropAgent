"""Fully offline text-to-speech provider using `pyttsx3` (no network, no API key).

Quality is lower than cloud providers but this guarantees the pipeline can
run end-to-end in air-gapped or CI environments.
"""

from __future__ import annotations

from pathlib import Path

from dropagent.exceptions import ProviderNotAvailableError, TTSGenerationError
from dropagent.logging_config import get_logger
from dropagent.voice.base import BaseTTSProvider

log = get_logger(__name__)


class Pyttsx3Provider(BaseTTSProvider):
    name = "pyttsx3"

    def __init__(self, settings=None):
        try:
            import pyttsx3  # noqa: F401
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ProviderNotAvailableError(
                "The 'pyttsx3' package (and a system speech engine) is required for "
                "Pyttsx3Provider. Install it with `pip install pyttsx3`."
            ) from exc

    def synthesize(self, text: str, output_path: Path) -> Path:
        import pyttsx3

        output_path = output_path.with_suffix(".wav")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            engine = pyttsx3.init()
            engine.save_to_file(text, str(output_path))
            engine.runAndWait()
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise TTSGenerationError(f"pyttsx3 synthesis failed: {exc}") from exc

        log.info("pyttsx3 narration written to %s", output_path)
        return output_path
