"""Creador automático de productos en Shopify vía la Admin REST API."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from .aliexpress_scraper import Product
from .claude_generator import GeneratedCopy
from .config import config
from .notifier import notifier


@dataclass
class ShopifyResult:
    success: bool
    product_id: Optional[str]
    price: float
    dry_run: bool
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "product_id": self.product_id,
            "price": self.price,
            "dry_run": self.dry_run,
            "error": self.error,
        }


class ShopifyManager:
    """Crea productos en una tienda Shopify usando la Admin REST API."""

    def __init__(self):
        self.shop_url = config.shopify_shop_url.strip().rstrip("/")
        self.access_token = config.shopify_access_token
        self.api_version = config.shopify_api_version

    @property
    def is_live(self) -> bool:
        return config.shopify_configured

    def _endpoint(self, path: str) -> str:
        return f"https://{self.shop_url}/admin/api/{self.api_version}/{path}"

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    def apply_markup(self, base_price: float) -> float:
        markup = config.shopify_price_markup_percent / 100.0
        final_price = base_price * (1 + markup)
        return round(final_price, 2)

    def create_product(self, product: Product, copy: GeneratedCopy) -> ShopifyResult:
        final_price = self.apply_markup(product.price)
        status = "active" if config.shopify_publish_immediately else "draft"

        payload = {
            "product": {
                "title": copy.title or product.title,
                "body_html": copy.description_html,
                "vendor": "DropAgent",
                "product_type": product.keyword or "General",
                "tags": ", ".join(copy.tags),
                "status": status,
                "variants": [
                    {
                        "price": f"{final_price:.2f}",
                        "inventory_management": None,
                    }
                ],
                "images": [{"src": product.image_url}] if product.image_url else [],
            }
        }

        if not self.is_live:
            fake_id = f"dry-run-{uuid.uuid4().hex[:8]}"
            notifier.warning(
                "shopify_create",
                f"Shopify no está configurado; simulando creación de '{copy.title}' "
                f"(precio final: {final_price} USD)",
            )
            return ShopifyResult(
                success=True,
                product_id=fake_id,
                price=final_price,
                dry_run=True,
            )

        try:
            response = requests.post(
                self._endpoint("products.json"),
                headers=self._headers(),
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            product_id = str(data.get("product", {}).get("id", ""))
            notifier.success(
                "shopify_create",
                f"Producto '{copy.title}' creado en Shopify (id={product_id}, "
                f"precio={final_price} USD, estado={status})",
            )
            return ShopifyResult(
                success=True,
                product_id=product_id,
                price=final_price,
                dry_run=False,
                raw_response=data,
            )
        except requests.RequestException as exc:
            notifier.error(
                "shopify_create",
                f"Error al crear '{copy.title}' en Shopify: {exc}",
            )
            return ShopifyResult(
                success=False,
                product_id=None,
                price=final_price,
                dry_run=False,
                error=str(exc),
            )


def get_manager() -> ShopifyManager:
    return ShopifyManager()
