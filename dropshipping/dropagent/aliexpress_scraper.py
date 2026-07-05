"""Buscador de productos trending en AliExpress.

AliExpress no ofrece una API pública gratuita para "productos trending",
así que este módulo intenta obtener resultados reales haciendo scraping
de las páginas públicas de búsqueda. Si el scraping falla (bloqueo
anti-bot, cambios de HTML, falta de conexión, etc.) DropAgent recurre
automáticamente a un catálogo de demostración para que el resto del
pipeline (generación de descripciones, creación en Shopify) se pueda
seguir probando sin interrupciones.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .config import config
from .notifier import notifier

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

SEARCH_URL = "https://www.aliexpress.com/w/wholesale-{query}.html"


@dataclass
class Product:
    """Representa un producto encontrado en AliExpress."""

    title: str
    price: float
    currency: str
    image_url: str
    product_url: str
    orders: int = 0
    rating: float = 0.0
    source: str = "scraper"
    keyword: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "price": self.price,
            "currency": self.currency,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "orders": self.orders,
            "rating": self.rating,
            "source": self.source,
            "keyword": self.keyword,
        }


# Catálogo de demostración usado como respaldo cuando el scraping en vivo
# no está disponible (bloqueo anti-bot, sin conexión a internet, etc.)
_DEMO_CATALOG: List[Dict[str, Any]] = [
    {
        "title": "Mini luz LED nocturna con sensor de movimiento inalámbrica",
        "price": 4.99,
        "image_url": "https://ae01.alicdn.com/kf/demo-led-light.jpg",
        "orders": 15234,
        "rating": 4.7,
    },
    {
        "title": "Organizador de cables magnético para escritorio (set de 6)",
        "price": 6.49,
        "image_url": "https://ae01.alicdn.com/kf/demo-cable-organizer.jpg",
        "orders": 8420,
        "rating": 4.6,
    },
    {
        "title": "Banda de resistencia para ejercicio con asas ajustables",
        "price": 8.99,
        "image_url": "https://ae01.alicdn.com/kf/demo-resistance-band.jpg",
        "orders": 22110,
        "rating": 4.8,
    },
    {
        "title": "Dispensador automático de comida para mascotas con temporizador",
        "price": 24.99,
        "image_url": "https://ae01.alicdn.com/kf/demo-pet-feeder.jpg",
        "orders": 5310,
        "rating": 4.5,
    },
    {
        "title": "Set de brochas de maquillaje profesional 12 piezas",
        "price": 7.29,
        "image_url": "https://ae01.alicdn.com/kf/demo-makeup-brush.jpg",
        "orders": 31890,
        "rating": 4.7,
    },
    {
        "title": "Soporte ajustable para celular y tablet de aluminio",
        "price": 5.79,
        "image_url": "https://ae01.alicdn.com/kf/demo-phone-stand.jpg",
        "orders": 12750,
        "rating": 4.6,
    },
]


class AliExpressScraper:
    """Busca productos trending en AliExpress con respaldo a datos demo."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()

    def get_trending_products(self, keyword: str, limit: int = 5) -> List[Product]:
        """Devuelve productos trending para una palabra clave.

        Intenta scraping en vivo primero; si falla por cualquier motivo,
        cae en el catálogo demo para que el pipeline nunca se detenga.
        """
        try:
            products = self._scrape_live(keyword, limit)
            if products:
                notifier.success(
                    "aliexpress_search",
                    f"Se encontraron {len(products)} productos reales para '{keyword}'",
                )
                return products
            notifier.warning(
                "aliexpress_search",
                f"El scraping no devolvió resultados para '{keyword}', usando catálogo demo",
            )
        except Exception as exc:  # noqa: BLE001 - queremos degradar sin romper el pipeline
            notifier.warning(
                "aliexpress_search",
                f"No se pudo scrapear AliExpress para '{keyword}' ({exc}); usando catálogo demo",
            )
        return self._demo_products(keyword, limit)

    def get_trending_for_all_keywords(self, limit_per_keyword: int = 3) -> List[Product]:
        """Busca productos trending para todas las keywords configuradas en .env."""
        all_products: List[Product] = []
        for keyword in config.aliexpress_keywords:
            all_products.extend(self.get_trending_products(keyword, limit_per_keyword))
        return all_products

    def _scrape_live(self, keyword: str, limit: int) -> List[Product]:
        url = SEARCH_URL.format(query=requests.utils.quote(keyword))
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        products: List[Product] = []

        # AliExpress renderiza los resultados vía JavaScript, pero en algunos
        # casos incrusta un bloque JSON con los datos iniciales de búsqueda.
        # Intentamos localizar precios/títulos con una búsqueda de texto laxa
        # para tolerar cambios de estructura del HTML.
        price_pattern = re.compile(r"\"salePrice\":\s*\{[^}]*\"formattedPrice\":\s*\"([^\"]+)\"")
        title_pattern = re.compile(r"\"title\":\s*\{[^}]*\"displayTitle\":\s*\"([^\"]+)\"")

        titles = title_pattern.findall(response.text)
        prices = price_pattern.findall(response.text)

        for idx, title in enumerate(titles[:limit]):
            raw_price = prices[idx] if idx < len(prices) else "$0.00"
            price_value = self._parse_price(raw_price)
            products.append(
                Product(
                    title=title,
                    price=price_value,
                    currency="USD",
                    image_url="",
                    product_url=url,
                    source="scraper",
                    keyword=keyword,
                )
            )

        return products

    @staticmethod
    def _parse_price(raw_price: str) -> float:
        cleaned = re.sub(r"[^0-9.,]", "", raw_price).replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _demo_products(self, keyword: str, limit: int) -> List[Product]:
        sample = random.sample(_DEMO_CATALOG, k=min(limit, len(_DEMO_CATALOG)))
        return [
            Product(
                title=item["title"],
                price=item["price"],
                currency="USD",
                image_url=item["image_url"],
                product_url="https://www.aliexpress.com/",
                orders=item["orders"],
                rating=item["rating"],
                source="demo",
                keyword=keyword,
            )
            for item in sample
        ]


def get_scraper() -> AliExpressScraper:
    return AliExpressScraper()
