"""Small, dependency-free wrappers around the `ffmpeg` / `ffprobe` CLIs.

We shell out to the CLI tools directly (rather than a heavier Python
binding) to keep full control over filter graphs and to keep the
dependency footprint minimal -- ffmpeg/ffprobe just need to be on PATH
(they are installed in the provided Docker image).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from dropagent.config import get_settings
from dropagent.exceptions import VideoAssemblyError
from dropagent.logging_config import get_logger

log = get_logger(__name__)


def run_ffmpeg(args: list[str], *, description: str = "ffmpeg command") -> None:
    """Run an ffmpeg command, raising :class:`VideoAssemblyError` on failure."""
    settings = get_settings()
    command = [settings.ffmpeg_binary, "-y", "-hide_banner", "-loglevel", "error", *args]
    log.debug("Running %s: %s", description, " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise VideoAssemblyError(
            f"{description} failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )


def get_media_duration(path: Path) -> float:
    """Return the duration in seconds of an audio or video file via ffprobe."""
    settings = get_settings()
    command = [
        settings.ffprobe_binary,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise VideoAssemblyError(f"ffprobe failed to read duration of {path}:\n{result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise VideoAssemblyError(f"Could not parse ffprobe duration output for {path}") from exc


def check_ffmpeg_available() -> bool:
    """Return True if both ffmpeg and ffprobe are reachable on PATH."""
    settings = get_settings()
    for binary in (settings.ffmpeg_binary, settings.ffprobe_binary):
        try:
            subprocess.run([binary, "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    return True
