"""Abstract interface every platform publisher must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from dropagent.models import PlatformMetadata


class BasePublisher(ABC):
    """Uploads/publishes an exported video to a specific platform."""

    platform: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether credentials required for this publisher are present."""
        raise NotImplementedError

    @abstractmethod
    def publish(self, video_path: Path, thumbnail_path: Path, metadata: PlatformMetadata) -> str:
        """Publish the video and return a URL or platform-specific identifier."""
        raise NotImplementedError
