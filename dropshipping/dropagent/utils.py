"""Utilidades compartidas entre módulos de DropAgent."""

from __future__ import annotations

import re


def slugify(text: str) -> str:
    """Convierte un texto en un slug apto para nombres de archivo/URL."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60].strip("-") or "producto"
