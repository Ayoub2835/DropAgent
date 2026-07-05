"""Orquesta el flujo completo: buscar -> describir -> publicar en Shopify."""

from __future__ import annotations

from typing import Any, Dict, List

from .aliexpress_scraper import AliExpressScraper
from .claude_generator import ClaudeDescriptionGenerator
from .config import config
from .notifier import notifier
from .shopify_manager import ShopifyManager
from .tiktok_ads_manager import TikTokAdsManager


class DropAgentPipeline:
    """Pipeline principal de DropAgent: producto trending -> tienda Shopify -> anuncio TikTok."""

    def __init__(self):
        self.scraper = AliExpressScraper()
        self.generator = ClaudeDescriptionGenerator()
        self.shopify = ShopifyManager()
        self.tiktok = TikTokAdsManager()

    def run_once(self, max_products: int = None) -> List[Dict[str, Any]]:
        """Ejecuta una pasada completa del pipeline y devuelve un resumen."""
        max_products = max_products or config.max_products_per_run
        notifier.info(
            "pipeline",
            f"Iniciando búsqueda de productos trending (máx {max_products} productos)",
        )

        products = self.scraper.get_trending_for_all_keywords(limit_per_keyword=2)
        if not products:
            notifier.warning("pipeline", "No se encontraron productos trending en esta ejecución")
            return []

        products = products[:max_products]
        results: List[Dict[str, Any]] = []

        for product in products:
            copy = self.generator.generate(product)
            shopify_result = self.shopify.create_product(product, copy)
            landing_url = self._resolve_landing_url(product, shopify_result)
            tiktok_result = self.tiktok.launch_campaign(product, copy, landing_url)
            results.append(
                {
                    "product": product.to_dict(),
                    "copy": copy.to_dict(),
                    "shopify": shopify_result.to_dict(),
                    "tiktok": tiktok_result.to_dict(),
                }
            )

        successful = sum(1 for r in results if r["shopify"]["success"])
        notifier.success(
            "pipeline",
            f"Pipeline finalizado: {successful}/{len(results)} productos procesados con éxito",
        )
        return results

    @staticmethod
    def _resolve_landing_url(product, shopify_result) -> str:
        """Construye la URL de la ficha de producto en Shopify para usarla como
        landing page del anuncio de TikTok. Si Shopify no está configurado o
        la respuesta no trae el handle, usa la URL de AliExpress como respaldo."""
        handle = None
        if shopify_result.raw_response:
            handle = shopify_result.raw_response.get("product", {}).get("handle")
        if handle and config.shopify_shop_url:
            return f"https://{config.shopify_shop_url.strip().rstrip('/')}/products/{handle}"
        return product.product_url


def get_pipeline() -> DropAgentPipeline:
    return DropAgentPipeline()
