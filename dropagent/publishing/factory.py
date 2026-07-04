"""Resolves a platform name to its publisher implementation."""

from __future__ import annotations

from dropagent.config import Settings, get_settings
from dropagent.publishing.base import BasePublisher


def get_publisher(platform: str, settings: Settings | None = None) -> BasePublisher:
    settings = settings or get_settings()
    platform = platform.lower()

    if platform == "youtube":
        from dropagent.publishing.youtube_publisher import YouTubePublisher

        return YouTubePublisher(settings)
    if platform == "tiktok":
        from dropagent.publishing.tiktok_publisher import TikTokPublisher

        return TikTokPublisher(settings)
    if platform == "snapchat":
        from dropagent.publishing.snapchat_publisher import SnapchatPublisher

        return SnapchatPublisher(settings)

    raise ValueError(f"No publisher available for platform '{platform}'.")
