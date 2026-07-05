"""Generador de descripciones de producto usando la API de Claude (Anthropic).

Si no hay una CLAUDE_API_KEY configurada, o si la llamada a la API falla
por cualquier motivo (sin conexión, límite de cuota, etc.), se usa un
generador de plantillas local para que el pipeline nunca se detenga.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .aliexpress_scraper import Product
from .config import config
from .notifier import notifier

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - el paquete se instala via requirements.txt
    Anthropic = None  # type: ignore


PROMPT_TEMPLATE = """Eres un copywriter experto en e-commerce y dropshipping.
Genera una ficha de producto persuasiva en español para vender el siguiente
artículo en una tienda Shopify.

Producto: {title}
Precio de referencia: {price} {currency}
Categoría/keyword: {keyword}

Responde ÚNICAMENTE con un JSON válido (sin texto adicional, sin markdown)
con esta forma exacta:
{{
  "title": "título corto y atractivo para la tienda (máx 70 caracteres)",
  "description_html": "descripción en HTML con <p> y una lista <ul><li> de \
beneficios, lista para pegar en Shopify",
  "tags": ["tag1", "tag2", "tag3"]
}}
"""


@dataclass
class GeneratedCopy:
    title: str
    description_html: str
    tags: list
    source: str = "claude"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description_html": self.description_html,
            "tags": self.tags,
            "source": self.source,
        }


class ClaudeDescriptionGenerator:
    """Genera títulos y descripciones de venta usando la API de Claude."""

    def __init__(self):
        self._client: Optional["Anthropic"] = None
        if config.claude_configured and Anthropic is not None:
            self._client = Anthropic(api_key=config.claude_api_key)

    @property
    def is_live(self) -> bool:
        return self._client is not None

    def generate(self, product: Product) -> GeneratedCopy:
        if self.is_live:
            try:
                return self._generate_with_claude(product)
            except Exception as exc:  # noqa: BLE001 - degradar sin romper el pipeline
                notifier.warning(
                    "claude_generate",
                    f"Fallo al llamar a la API de Claude ({exc}); usando plantilla local",
                )
        else:
            notifier.warning(
                "claude_generate",
                "CLAUDE_API_KEY no configurada; usando generador de plantillas local",
            )
        return self._generate_with_template(product)

    def _generate_with_claude(self, product: Product) -> GeneratedCopy:
        import json

        prompt = PROMPT_TEMPLATE.format(
            title=product.title,
            price=product.price,
            currency=product.currency,
            keyword=product.keyword or "general",
        )
        response = self._client.messages.create(
            model=config.claude_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()

        # Los modelos a veces envuelven el JSON en bloques ```json; lo limpiamos.
        cleaned = raw_text.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

        data = json.loads(cleaned)
        copy = GeneratedCopy(
            title=data.get("title", product.title)[:70],
            description_html=data.get("description_html", ""),
            tags=data.get("tags", []),
            source="claude",
        )
        notifier.success(
            "claude_generate", f"Descripción generada con Claude para '{product.title}'"
        )
        return copy

    def _generate_with_template(self, product: Product) -> GeneratedCopy:
        title = product.title if len(product.title) <= 70 else product.title[:67] + "..."
        benefits = [
            "Envío rápido y seguimiento incluido",
            "Calidad verificada por miles de compradores",
            "Stock limitado: ¡pide el tuyo antes de que se agote!",
        ]
        benefits_html = "".join(f"<li>{b}</li>" for b in benefits)
        description_html = (
            f"<p>Descubre <strong>{product.title}</strong>, uno de los productos más "
            f"populares de la categoría {product.keyword or 'tendencias'} con "
            f"{product.orders or 'miles de'} pedidos realizados.</p>"
            f"<ul>{benefits_html}</ul>"
        )
        tags = [t for t in [product.keyword, "trending", "dropshipping"] if t]
        notifier.info(
            "claude_generate",
            f"Descripción generada con plantilla local para '{product.title}'",
        )
        return GeneratedCopy(
            title=title,
            description_html=description_html,
            tags=tags,
            source="template",
        )


def get_generator() -> ClaudeDescriptionGenerator:
    return ClaudeDescriptionGenerator()
