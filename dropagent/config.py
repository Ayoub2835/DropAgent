"""Centralized configuration for DropAgent.

All runtime configuration is read from environment variables (populated from
a `.env` file via python-dotenv in local/dev use, or injected directly by
Docker/CI in production). Nothing in the codebase should call `os.getenv`
directly outside of this module -- import `get_settings()` instead so there
is a single, testable source of truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env once at import time. Real environment variables (e.g. set by
# Docker) always take precedence over values in the file.
load_dotenv(override=False)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the application configuration."""

    # --- General ---
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    output_dir: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "output")).resolve())
    assets_dir: Path = field(default_factory=lambda: Path(os.getenv("ASSETS_DIR", "assets")).resolve())
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_dir: Path = field(default_factory=lambda: Path(os.getenv("LOG_DIR", "logs")).resolve())

    # --- LLM (story / script / metadata generation) ---
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai").lower())
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_text_model: str = field(default_factory=lambda: os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    anthropic_text_model: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_TEXT_MODEL", "claude-sonnet-5")
    )

    # --- Text-to-speech ---
    tts_provider: str = field(default_factory=lambda: os.getenv("TTS_PROVIDER", "gtts").lower())
    elevenlabs_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY"))
    elevenlabs_voice_id: str = field(
        default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    )
    openai_tts_voice: str = field(default_factory=lambda: os.getenv("OPENAI_TTS_VOICE", "alloy"))
    tts_language: str = field(default_factory=lambda: os.getenv("TTS_LANGUAGE", "en"))

    # --- Image / video generation for scenes ---
    image_provider: str = field(default_factory=lambda: os.getenv("IMAGE_PROVIDER", "placeholder").lower())
    stability_api_key: Optional[str] = field(default_factory=lambda: os.getenv("STABILITY_API_KEY"))
    openai_image_model: str = field(default_factory=lambda: os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3"))
    image_width: int = field(default_factory=lambda: _env_int("IMAGE_WIDTH", 1024))
    image_height: int = field(default_factory=lambda: _env_int("IMAGE_HEIGHT", 1792))

    # --- Subtitles ---
    subtitle_mode: str = field(default_factory=lambda: os.getenv("SUBTITLE_MODE", "even").lower())
    whisper_model_size: str = field(default_factory=lambda: os.getenv("WHISPER_MODEL_SIZE", "base"))

    # --- Video assembly ---
    ffmpeg_binary: str = field(default_factory=lambda: os.getenv("FFMPEG_BINARY", "ffmpeg"))
    ffprobe_binary: str = field(default_factory=lambda: os.getenv("FFPROBE_BINARY", "ffprobe"))
    video_fps: int = field(default_factory=lambda: _env_int("VIDEO_FPS", 30))
    transition_duration: float = field(
        default_factory=lambda: float(os.getenv("TRANSITION_DURATION", "0.6"))
    )
    music_volume_db: float = field(default_factory=lambda: float(os.getenv("MUSIC_VOLUME_DB", "-22")))
    scene_min_duration: float = field(
        default_factory=lambda: float(os.getenv("SCENE_MIN_DURATION", "3.0"))
    )

    # --- Export targets ---
    export_platforms: list[str] = field(
        default_factory=lambda: _env_list("EXPORT_PLATFORMS", ["youtube", "tiktok", "snapchat"])
    )

    # --- Publishing (official APIs) ---
    auto_publish: bool = field(default_factory=lambda: _env_bool("AUTO_PUBLISH", False))
    youtube_client_secrets_file: Optional[str] = field(
        default_factory=lambda: os.getenv("YOUTUBE_CLIENT_SECRETS_FILE")
    )
    youtube_token_file: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_TOKEN_FILE", ".secrets/youtube_token.json")
    )
    youtube_privacy_status: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_PRIVACY_STATUS", "private")
    )
    tiktok_access_token: Optional[str] = field(default_factory=lambda: os.getenv("TIKTOK_ACCESS_TOKEN"))
    tiktok_open_id: Optional[str] = field(default_factory=lambda: os.getenv("TIKTOK_OPEN_ID"))
    snapchat_access_token: Optional[str] = field(
        default_factory=lambda: os.getenv("SNAPCHAT_ACCESS_TOKEN")
    )

    def ensure_directories(self) -> None:
        """Create runtime directories if they do not exist yet."""
        for path in (self.output_dir, self.assets_dir, self.log_dir):
            path.mkdir(parents=True, exist_ok=True)


_settings: Optional[Settings] = None


def get_settings(refresh: bool = False) -> Settings:
    """Return the process-wide Settings singleton.

    Args:
        refresh: force re-reading environment variables (mainly useful in tests).
    """
    global _settings
    if _settings is None or refresh:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings
