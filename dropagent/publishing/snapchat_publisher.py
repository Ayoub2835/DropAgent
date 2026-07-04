"""Snapchat publisher.

IMPORTANT LIMITATION: unlike YouTube and TikTok, Snapchat does not currently
offer a public server-side API for organic creators to publish directly to
Spotlight. Snapchat's official APIs are either:

- The Marketing API (`https://marketingapi.snapchat.com`), which publishes
  paid ads, not organic Spotlight posts.
- Creative Kit, a client-side SDK that opens Snapchat's own app with your
  media pre-attached so a *human* taps "send" -- it cannot post
  unattended from a server.

This publisher therefore does not perform an unattended upload. It
validates that credentials/config are present for future use, and exposes
``prepare_manual_package`` so the pipeline can hand off a ready-to-post
folder (video + thumbnail + caption) for a human to publish through the
Snapchat app, while keeping the same interface as the other publishers so
this can be swapped for a real API call the moment Snapchat exposes one.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dropagent.config import Settings
from dropagent.exceptions import PublishingError
from dropagent.logging_config import get_logger
from dropagent.models import PlatformMetadata
from dropagent.publishing.base import BasePublisher

log = get_logger(__name__)


class SnapchatPublisher(BasePublisher):
    platform = "snapchat"

    def __init__(self, settings: Settings):
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.snapchat_access_token)

    def publish(self, video_path: Path, thumbnail_path: Path, metadata: PlatformMetadata) -> str:
        raise PublishingError(
            "Snapchat has no public API for unattended organic Spotlight posting. "
            "Use prepare_manual_package() to stage the video/caption for manual upload "
            "through the Snapchat app, or integrate the Marketing API if this is a paid "
            "ad campaign instead."
        )

    def prepare_manual_package(
        self, video_path: Path, thumbnail_path: Path, metadata: PlatformMetadata, output_dir: Path
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video_path, output_dir / video_path.name)
        if thumbnail_path.exists():
            shutil.copy2(thumbnail_path, output_dir / thumbnail_path.name)

        caption_path = output_dir / "caption.txt"
        caption_path.write_text(
            f"{metadata.title}\n\n{metadata.description}\n\n{metadata.hashtags_line()}",
            encoding="utf-8",
        )
        log.info("Prepared manual Snapchat Spotlight package at %s", output_dir)
        return output_dir
