"""Tests for the offline placeholder image provider and thumbnail generator."""

from __future__ import annotations

from PIL import Image

from dropagent.video.thumbnail import THUMBNAIL_SIZE, ThumbnailGenerator
from dropagent.visuals.placeholder_provider import PlaceholderImageProvider


def test_placeholder_provider_generates_image_at_requested_size(tmp_path):
    provider = PlaceholderImageProvider()
    output = provider.generate(
        "A lone woman at a frost-covered radio console", tmp_path / "scene_000", width=768, height=1344
    )
    assert output.exists()
    with Image.open(output) as img:
        assert img.size == (768, 1344)


def test_thumbnail_generator_produces_youtube_sized_image(tmp_path):
    provider = PlaceholderImageProvider()
    scene_image = provider.generate("An eerie arctic station at night", tmp_path / "scene", 1024, 1792)

    thumbnail_path = ThumbnailGenerator().generate(scene_image, "The Last Signal", tmp_path / "thumb.jpg")
    assert thumbnail_path.exists()
    with Image.open(thumbnail_path) as img:
        assert img.size == THUMBNAIL_SIZE
