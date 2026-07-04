"""Offline placeholder image provider.

Renders a stylized gradient card with the scene's visual prompt as caption
text using Pillow only -- no API key, no network. This is the default
provider so the pipeline is runnable out of the box, and it is also used
as the last-resort fallback if a paid image provider fails or is
unconfigured.
"""

from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from dropagent.logging_config import get_logger
from dropagent.visuals.base import BaseImageProvider

log = get_logger(__name__)

_PALETTES = [
    ((17, 24, 39), (88, 28, 135)),
    ((12, 74, 110), (15, 23, 42)),
    ((76, 5, 25), (23, 23, 23)),
    ((6, 78, 59), (17, 24, 39)),
    ((67, 20, 7), (24, 24, 27)),
]


class PlaceholderImageProvider(BaseImageProvider):
    name = "placeholder"

    def generate(self, prompt: str, output_path: Path, width: int, height: int) -> Path:
        top, bottom = self._pick_palette(prompt)
        image = self._render_gradient(width, height, top, bottom)
        self._draw_caption(image, prompt)

        output_path = output_path.with_suffix(".png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        log.info("Placeholder image written to %s", output_path)
        return output_path

    @staticmethod
    def _pick_palette(prompt: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(_PALETTES)
        return _PALETTES[index]

    @staticmethod
    def _render_gradient(
        width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]
    ) -> Image.Image:
        image = Image.new("RGB", (width, height), top)
        draw = ImageDraw.Draw(image)
        for y in range(height):
            ratio = y / max(height - 1, 1)
            r = int(top[0] + (bottom[0] - top[0]) * ratio)
            g = int(top[1] + (bottom[1] - top[1]) * ratio)
            b = int(top[2] + (bottom[2] - top[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        return image

    @staticmethod
    def _draw_caption(image: Image.Image, prompt: str) -> None:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        font_size = max(24, width // 22)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
            )
        except OSError:
            font = ImageFont.load_default()

        wrapped = textwrap.fill(prompt, width=26)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (width - text_w) / 2
        y = (height - text_h) / 2

        # Soft shadow for legibility over any gradient.
        draw.multiline_text(
            (x + 3, y + 3), wrapped, font=font, fill=(0, 0, 0, 180), align="center", spacing=10
        )
        draw.multiline_text(
            (x, y), wrapped, font=font, fill=(240, 240, 240), align="center", spacing=10
        )
