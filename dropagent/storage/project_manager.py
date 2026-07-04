"""Creates and organizes the on-disk folder structure for a generated project.

Every run produces a self-contained folder under ``OUTPUT_DIR``:

output/<slug>-<timestamp>/
    scenes/        scene still images
    audio/         per-scene narration + mixed master audio
    subtitles/     the generated .srt file
    video/         the assembled master video
    thumbnails/    the YouTube thumbnail
    exports/       final per-platform videos (youtube.mp4, tiktok.mp4, snapchat.mp4)
    metadata/      story.json, script.json, and <platform>.json metadata
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from dropagent.config import Settings, get_settings
from dropagent.logging_config import get_logger
from dropagent.models import PlatformMetadata, Scene, Script, Story
from dropagent.models import ProjectPaths

log = get_logger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_length: int = 40) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:max_length].strip("-") or "story"


class ProjectManager:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create_project(self, title: str) -> ProjectPaths:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        folder_name = f"{slugify(title)}-{timestamp}"
        root = self._settings.output_dir / folder_name
        paths = ProjectPaths(root=root)
        paths.create_all()
        log.info("Created project folder %s", root)
        return paths

    @staticmethod
    def save_story_and_script(paths: ProjectPaths, story: Story, script: Script, scenes: list[Scene]) -> None:
        (paths.metadata_dir / "story.json").write_text(
            json.dumps(asdict(story), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (paths.metadata_dir / "script.json").write_text(
            json.dumps(asdict(script), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        scenes_data = [
            {
                "index": s.index,
                "text": s.text,
                "visual_prompt": s.visual_prompt,
                "narration_duration": s.narration_duration,
                "image_path": str(s.image_path) if s.image_path else None,
                "narration_audio_path": str(s.narration_audio_path) if s.narration_audio_path else None,
            }
            for s in scenes
        ]
        (paths.metadata_dir / "scenes.json").write_text(
            json.dumps(scenes_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def save_platform_metadata(paths: ProjectPaths, metadata: dict[str, PlatformMetadata]) -> None:
        for platform, meta in metadata.items():
            (paths.metadata_dir / f"{platform}.json").write_text(
                json.dumps(asdict(meta), indent=2, ensure_ascii=False), encoding="utf-8"
            )
