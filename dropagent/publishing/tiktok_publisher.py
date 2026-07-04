"""TikTok Content Posting API publisher.

Uses TikTok's official "Direct Post" Content Posting API
(https://developers.tiktok.com/doc/content-posting-api-get-started/). This
requires:

1. A TikTok developer app with the ``video.publish`` scope approved.
2. An OAuth2 user access token (``TIKTOK_ACCESS_TOKEN``) and the
   authorizing user's ``open_id`` (``TIKTOK_OPEN_ID``).

Note: TikTok gates unaudited apps to posting privately to the creator's own
account ("SELF_ONLY") until your app passes their review -- this
implementation targets that same public endpoint, so behavior will match
whatever audit status your app has.
"""

from __future__ import annotations

from pathlib import Path

import requests

from dropagent.config import Settings
from dropagent.exceptions import PublishingError
from dropagent.logging_config import get_logger
from dropagent.models import PlatformMetadata
from dropagent.publishing.base import BasePublisher

log = get_logger(__name__)

_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"


class TikTokPublisher(BasePublisher):
    platform = "tiktok"

    def __init__(self, settings: Settings):
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.tiktok_access_token and self._settings.tiktok_open_id)

    def publish(self, video_path: Path, thumbnail_path: Path, metadata: PlatformMetadata) -> str:
        if not self.is_configured():
            raise PublishingError(
                "TIKTOK_ACCESS_TOKEN / TIKTOK_OPEN_ID are not set; cannot publish to TikTok."
            )

        video_size = video_path.stat().st_size
        headers = {
            "Authorization": f"Bearer {self._settings.tiktok_access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "post_info": {
                "title": metadata.title,
                "description": f"{metadata.description} {metadata.hashtags_line()}".strip(),
                "privacy_level": "SELF_ONLY",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        }

        try:
            init_response = requests.post(_INIT_URL, json=payload, headers=headers, timeout=30)
            init_response.raise_for_status()
            init_data = init_response.json()
            upload_url = init_data["data"]["upload_url"]
            publish_id = init_data["data"]["publish_id"]

            with open(video_path, "rb") as video_file:
                upload_headers = {
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
                }
                upload_response = requests.put(
                    upload_url, data=video_file, headers=upload_headers, timeout=300
                )
                upload_response.raise_for_status()
        except requests.RequestException as exc:
            raise PublishingError(f"TikTok publish failed: {exc}") from exc
        except (KeyError, ValueError) as exc:
            raise PublishingError(f"Unexpected TikTok API response: {exc}") from exc

        log.info("TikTok publish initiated, publish_id=%s", publish_id)
        return publish_id
