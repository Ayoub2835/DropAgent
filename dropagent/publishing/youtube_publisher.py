"""YouTube Data API v3 publisher.

Uses the official ``google-api-python-client`` with an OAuth 2.0 "installed
app" flow. Requires you to:

1. Create a project in Google Cloud Console and enable the YouTube Data API v3.
2. Create OAuth client credentials (Desktop app) and download the JSON file.
3. Set ``YOUTUBE_CLIENT_SECRETS_FILE`` to that file's path.

On first run this opens a local browser consent screen; the resulting
token is cached at ``YOUTUBE_TOKEN_FILE`` for subsequent runs.
"""

from __future__ import annotations

from pathlib import Path

from dropagent.config import Settings
from dropagent.exceptions import PublishingError
from dropagent.logging_config import get_logger
from dropagent.models import PlatformMetadata
from dropagent.publishing.base import BasePublisher

log = get_logger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubePublisher(BasePublisher):
    platform = "youtube"

    def __init__(self, settings: Settings):
        self._settings = settings

    def is_configured(self) -> bool:
        return bool(self._settings.youtube_client_secrets_file)

    def publish(self, video_path: Path, thumbnail_path: Path, metadata: PlatformMetadata) -> str:
        if not self.is_configured():
            raise PublishingError(
                "YOUTUBE_CLIENT_SECRETS_FILE is not set; cannot publish to YouTube."
            )

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise PublishingError(
                "google-api-python-client and google-auth-oauthlib are required for "
                "YouTube publishing. Install them with "
                "`pip install google-api-python-client google-auth-oauthlib`."
            ) from exc

        credentials = self._load_credentials(Request, Credentials, InstalledAppFlow)
        youtube = build("youtube", "v3", credentials=credentials)

        body = {
            "snippet": {
                "title": metadata.title[:100],
                "description": f"{metadata.description}\n\n{metadata.hashtags_line()}",
                "tags": metadata.keywords,
                "categoryId": "24",  # Entertainment
            },
            "status": {"privacyStatus": self._settings.youtube_privacy_status},
        }

        try:
            media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = request.execute()
            video_id = response["id"]

            if thumbnail_path.exists():
                youtube.thumbnails().set(
                    videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))
                ).execute()
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise PublishingError(f"YouTube upload failed: {exc}") from exc

        url = f"https://youtube.com/watch?v={video_id}"
        log.info("Published to YouTube: %s", url)
        return url

    def _load_credentials(self, Request, Credentials, InstalledAppFlow):
        token_path = Path(self._settings.youtube_token_file)
        credentials = None

        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._settings.youtube_client_secrets_file, _SCOPES
                )
                credentials = flow.run_local_server(port=0)

            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(credentials.to_json(), encoding="utf-8")

        return credentials
