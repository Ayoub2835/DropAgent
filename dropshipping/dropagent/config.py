"""Carga y validación de la configuración de DropAgent desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "si", "sí")


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_list(name: str, default: List[str]) -> List[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Config:
    # AliExpress
    aliexpress_app_key: str = field(default_factory=lambda: os.getenv("ALIEXPRESS_APP_KEY", ""))
    aliexpress_app_secret: str = field(default_factory=lambda: os.getenv("ALIEXPRESS_APP_SECRET", ""))
    aliexpress_tracking_id: str = field(default_factory=lambda: os.getenv("ALIEXPRESS_TRACKING_ID", "dropagent"))
    aliexpress_keywords: List[str] = field(
        default_factory=lambda: _env_list("ALIEXPRESS_KEYWORDS", ["gadgets", "hogar", "fitness"])
    )

    # Shopify
    shopify_shop_url: str = field(default_factory=lambda: os.getenv("SHOPIFY_SHOP_URL", ""))
    shopify_access_token: str = field(default_factory=lambda: os.getenv("SHOPIFY_ACCESS_TOKEN", ""))
    shopify_api_version: str = field(default_factory=lambda: os.getenv("SHOPIFY_API_VERSION", "2024-10"))
    shopify_price_markup_percent: float = field(
        default_factory=lambda: _env_float("SHOPIFY_PRICE_MARKUP_PERCENT", 45.0)
    )
    shopify_publish_immediately: bool = field(
        default_factory=lambda: _env_bool("SHOPIFY_PUBLISH_IMMEDIATELY", False)
    )

    # Claude
    claude_api_key: str = field(default_factory=lambda: os.getenv("CLAUDE_API_KEY", ""))
    claude_model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-5"))

    # Facebook Ads
    facebook_access_token: str = field(default_factory=lambda: os.getenv("FACEBOOK_ACCESS_TOKEN", ""))
    facebook_ad_account_id: str = field(default_factory=lambda: os.getenv("FACEBOOK_AD_ACCOUNT_ID", ""))
    facebook_api_version: str = field(default_factory=lambda: os.getenv("FACEBOOK_API_VERSION", "v21.0"))
    facebook_monitor_interval_hours: float = field(
        default_factory=lambda: _env_float("FACEBOOK_MONITOR_INTERVAL_HOURS", 24.0)
    )
    facebook_min_roas: float = field(default_factory=lambda: _env_float("FACEBOOK_MIN_ROAS", 1.5))
    facebook_max_spend_no_sales: float = field(
        default_factory=lambda: _env_float("FACEBOOK_MAX_SPEND_NO_SALES", 20.0)
    )

    # TikTok Ads
    tiktok_access_token: str = field(default_factory=lambda: os.getenv("TIKTOK_ACCESS_TOKEN", ""))
    tiktok_advertiser_id: str = field(default_factory=lambda: os.getenv("TIKTOK_ADVERTISER_ID", ""))
    tiktok_identity_id: str = field(default_factory=lambda: os.getenv("TIKTOK_IDENTITY_ID", ""))
    tiktok_identity_type: str = field(
        default_factory=lambda: os.getenv("TIKTOK_IDENTITY_TYPE", "CUSTOMIZED_USER")
    )
    tiktok_pixel_id: str = field(default_factory=lambda: os.getenv("TIKTOK_PIXEL_ID", ""))
    tiktok_api_version: str = field(default_factory=lambda: os.getenv("TIKTOK_API_VERSION", "v1.3"))
    tiktok_daily_budget: float = field(default_factory=lambda: _env_float("TIKTOK_DAILY_BUDGET", 20.0))
    tiktok_objective_type: str = field(
        default_factory=lambda: os.getenv("TIKTOK_OBJECTIVE_TYPE", "TRAFFIC")
    )
    tiktok_optimization_goal: str = field(
        default_factory=lambda: os.getenv("TIKTOK_OPTIMIZATION_GOAL", "CLICK")
    )
    tiktok_bid_type: str = field(default_factory=lambda: os.getenv("TIKTOK_BID_TYPE", "BID_TYPE_NO_BID"))
    tiktok_billing_event: str = field(default_factory=lambda: os.getenv("TIKTOK_BILLING_EVENT", "CPC"))
    tiktok_location_ids: List[str] = field(
        default_factory=lambda: _env_list("TIKTOK_LOCATION_IDS", ["6252001"])
    )
    tiktok_monitor_interval_hours: float = field(
        default_factory=lambda: _env_float("TIKTOK_MONITOR_INTERVAL_HOURS", 24.0)
    )
    tiktok_min_roas: float = field(default_factory=lambda: _env_float("TIKTOK_MIN_ROAS", 1.5))
    tiktok_max_spend_no_sales: float = field(
        default_factory=lambda: _env_float("TIKTOK_MAX_SPEND_NO_SALES", 20.0)
    )
    # Nombres de las métricas de compras/ingresos en el reporte de TikTok.
    # Configurables porque TikTok puede variar estos campos según el tipo de
    # cuenta publicitaria (Shop Ads vs. Web Conversions vía pixel).
    tiktok_purchase_metric: str = field(
        default_factory=lambda: os.getenv("TIKTOK_PURCHASE_METRIC", "conversion")
    )
    tiktok_revenue_metric: str = field(
        default_factory=lambda: os.getenv("TIKTOK_REVENUE_METRIC", "total_purchase_value")
    )

    # General
    max_products_per_run: int = field(default_factory=lambda: _env_int("MAX_PRODUCTS_PER_RUN", 5))
    log_file: str = field(default_factory=lambda: os.getenv("LOG_FILE", "log.json"))

    @property
    def aliexpress_configured(self) -> bool:
        return bool(self.aliexpress_app_key and self.aliexpress_app_secret)

    @property
    def shopify_configured(self) -> bool:
        return bool(self.shopify_shop_url and self.shopify_access_token)

    @property
    def claude_configured(self) -> bool:
        return bool(self.claude_api_key)

    @property
    def facebook_configured(self) -> bool:
        return bool(self.facebook_access_token and self.facebook_ad_account_id)

    @property
    def tiktok_configured(self) -> bool:
        return bool(self.tiktok_access_token and self.tiktok_advertiser_id)


config = Config()
