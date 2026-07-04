"""Abstract interface every text-to-speech provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseTTSProvider(ABC):
    """Synthesizes narration audio for a piece of text."""

    name: str = "base"

    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> Path:
        """Render ``text`` to speech and write it as an audio file at ``output_path``.

        Returns the path that was actually written (providers may need to
        change the extension, e.g. mp3 vs wav).
        """
        raise NotImplementedError
