"""End-to-end smoke test using only offline/mock providers.

Skipped automatically if ffmpeg/ffprobe are not on PATH (e.g. minimal CI
runners) -- see the Docker image for a guaranteed ffmpeg environment.
"""

from __future__ import annotations

import shutil

import pytest

from dropagent.pipeline import StoryPipeline

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not available on PATH",
)


@requires_ffmpeg
def test_full_pipeline_runs_end_to_end_with_offline_providers(isolated_settings):
    pipeline = StoryPipeline(isolated_settings)
    result = pipeline.run(
        topic="a lighthouse keeper who finds a message in a bottle",
        genre="mystery",
        platforms=["tiktok"],
    )

    assert result.master_video_path.exists()
    assert result.thumbnail_path.exists()
    assert result.subtitle_path.exists()
    assert result.subtitle_path.read_text(encoding="utf-8").strip()

    assert len(result.exports) == 1
    export = result.exports[0]
    assert export.platform == "tiktok"
    assert export.path.exists()
    assert export.path.stat().st_size > 0

    assert "tiktok" in result.metadata
    assert result.metadata["tiktok"].title

    for scene in result.scenes:
        assert scene.image_path and scene.image_path.exists()
        assert scene.narration_audio_path and scene.narration_audio_path.exists()
        assert scene.narration_duration > 0
