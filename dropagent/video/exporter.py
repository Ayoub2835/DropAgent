"""Exports the master (9:16) video into platform-specific deliverables.

- TikTok / Snapchat Spotlight: native 9:16, so the master is simply
  transcoded/validated for the target container.
- YouTube: reframed to 16:9 using a blurred, scaled copy of the same
  footage as background padding, so no content is cropped away.
"""

from __future__ import annotations

from pathlib import Path

from dropagent.config import Settings, get_settings
from dropagent.logging_config import get_logger
from dropagent.models import ExportedVideo
from dropagent.video.ffmpeg_utils import run_ffmpeg

log = get_logger(__name__)

PLATFORM_SPECS: dict[str, tuple[int, int, str]] = {
    "youtube": (1920, 1080, "16:9"),
    "tiktok": (1080, 1920, "9:16"),
    "snapchat": (1080, 1920, "9:16"),
}


class VideoExporter:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def export_all(
        self, master_video_path: Path, output_dir: Path, platforms: list[str]
    ) -> list[ExportedVideo]:
        output_dir.mkdir(parents=True, exist_ok=True)
        exports = []
        for platform in platforms:
            spec = PLATFORM_SPECS.get(platform.lower())
            if spec is None:
                log.warning("Unknown export platform '%s' -- skipping.", platform)
                continue
            width, height, aspect = spec
            output_path = output_dir / f"{platform.lower()}.mp4"
            if aspect == "9:16":
                self._export_vertical(master_video_path, width, height, output_path)
            else:
                self._export_horizontal_with_blur(master_video_path, width, height, output_path)
            exports.append(ExportedVideo(platform=platform.lower(), aspect_ratio=aspect, path=output_path))
            log.info("Exported %s (%s) to %s", platform, aspect, output_path)
        return exports

    @staticmethod
    def _export_vertical(source: Path, width: int, height: int, output_path: Path) -> None:
        run_ffmpeg(
            [
                "-i", str(source),
                "-vf",
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
                "-c:v", "libx264",
                "-crf", "19",
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(output_path),
            ],
            description="vertical (9:16) export",
        )

    @staticmethod
    def _export_horizontal_with_blur(source: Path, width: int, height: int, output_path: Path) -> None:
        filter_complex = (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},gblur=sigma=30[bg];"
            f"[0:v]scale=-2:{height}[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto[vout]"
        )
        run_ffmpeg(
            [
                "-i", str(source),
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "0:a",
                "-c:v", "libx264",
                "-crf", "19",
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(output_path),
            ],
            description="horizontal (16:9) blurred-background export",
        )
