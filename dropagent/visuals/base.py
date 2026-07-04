"""Abstract interface every scene-visual (image) provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseImageProvider(ABC):
    """Generates a single still image for a scene's visual prompt."""

    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, output_path: Path, width: int, height: int) -> Path:
        """Render an image for ``prompt`` and write it as a file at ``output_path``."""
        raise NotImplementedError
