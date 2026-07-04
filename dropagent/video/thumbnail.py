"""Generates a YouTube-ready thumbnail (1280x720) from a scene image + title."""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from dropagent.logging_config import get_logger

log = get_logger(__name__)

THUMBNAIL_SIZE = (1280, 720)


class ThumbnailGenerator:
    def generate(self, source_image_path: Path, title: str, output_path: Path) -> Path:
        base = Image.open(source_image_path).convert("RGB")
        thumbnail = self._fit_and_crop(base, THUMBNAIL_SIZE)
        thumbnail = self._darken_for_contrast(thumbnail)
        self._draw_title(thumbnail, title)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail.save(output_path, quality=92)
        log.info("Thumbnail written to %s", output_path)
        return output_path

    @staticmethod
    def _fit_and_crop(image: Image.Image, size: tuple[int, int]) -> Image.Image:
        target_w, target_h = size
        src_w, src_h = image.size
        target_ratio = target_w / target_h
        src_ratio = src_w / src_h

        if src_ratio > target_ratio:
            new_h = target_h
            new_w = int(src_ratio * new_h)
        else:
            new_w = target_w
            new_h = int(new_w / src_ratio)

        resized = image.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        return resized.crop((left, top, left + target_w, top + target_h))

    @staticmethod
    def _darken_for_contrast(image: Image.Image) -> Image.Image:
        overlay = Image.new("RGB", image.size, (0, 0, 0))
        blurred = image.filter(ImageFilter.GaussianBlur(0))
        darkened = Image.blend(blurred, overlay, alpha=0.35)
        return ImageEnhance.Contrast(darkened).enhance(1.1)

    @staticmethod
    def _draw_title(image: Image.Image, title: str) -> None:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        font_size = 92
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
            )
        except OSError:
            font = ImageFont.load_default()

        wrapped = textwrap.fill(title.upper(), width=16)

        while True:
            bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=8)
            text_w = bbox[2] - bbox[0]
            if text_w <= width * 0.9 or font_size <= 40:
                break
            font_size -= 6
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
                )
            except OSError:
                break

        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=8)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (width - text_w) / 2
        y = height - text_h - 60

        outline_range = 4
        for dx in range(-outline_range, outline_range + 1, 2):
            for dy in range(-outline_range, outline_range + 1, 2):
                draw.multiline_text(
                    (x + dx, y + dy), wrapped, font=font, fill=(0, 0, 0), align="center", spacing=8
                )
        draw.multiline_text((x, y), wrapped, font=font, fill=(255, 214, 0), align="center", spacing=8)
