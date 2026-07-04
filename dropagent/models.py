"""Core data structures shared across the DropAgent pipeline stages.

Using plain dataclasses (instead of passing dicts around) gives every
stage a typed, IDE-friendly contract for what it receives and returns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Story:
    """The raw, original story concept produced by the LLM."""

    topic: str
    genre: str
    title: str
    synopsis: str
    full_text: str
    language: str = "en"


@dataclass
class Script:
    """A story adapted into a short-form video script with a clear arc."""

    hook: str
    development: str
    climax: str
    resolution: str
    raw_text: str

    def as_single_text(self) -> str:
        parts = [self.hook, self.development, self.climax, self.resolution]
        return "\n\n".join(p.strip() for p in parts if p.strip())


@dataclass
class Scene:
    """One narrated beat of the script, with its own visual and audio."""

    index: int
    text: str
    visual_prompt: str
    narration_audio_path: Optional[Path] = None
    narration_duration: float = 0.0
    image_path: Optional[Path] = None
    video_clip_path: Optional[Path] = None


@dataclass
class SubtitleCue:
    index: int
    start: float
    end: float
    text: str


@dataclass
class PlatformMetadata:
    """SEO-optimized publishing metadata for a single platform."""

    platform: str
    title: str
    description: str
    hashtags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def hashtags_line(self) -> str:
        return " ".join(f"#{tag.lstrip('#')}" for tag in self.hashtags)


@dataclass
class ExportedVideo:
    platform: str
    aspect_ratio: str
    path: Path


@dataclass
class ProjectPaths:
    """Filesystem layout for a single generated project."""

    root: Path

    @property
    def scenes_dir(self) -> Path:
        return self.root / "scenes"

    @property
    def audio_dir(self) -> Path:
        return self.root / "audio"

    @property
    def subtitles_dir(self) -> Path:
        return self.root / "subtitles"

    @property
    def video_dir(self) -> Path:
        return self.root / "video"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    @property
    def thumbnails_dir(self) -> Path:
        return self.root / "thumbnails"

    @property
    def metadata_dir(self) -> Path:
        return self.root / "metadata"

    def create_all(self) -> None:
        for path in (
            self.scenes_dir,
            self.audio_dir,
            self.subtitles_dir,
            self.video_dir,
            self.exports_dir,
            self.thumbnails_dir,
            self.metadata_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class ProjectResult:
    """Final summary of everything produced by a pipeline run."""

    paths: ProjectPaths
    story: Story
    script: Script
    scenes: list[Scene]
    master_video_path: Path
    thumbnail_path: Path
    subtitle_path: Path
    metadata: dict[str, PlatformMetadata]
    exports: list[ExportedVideo]
