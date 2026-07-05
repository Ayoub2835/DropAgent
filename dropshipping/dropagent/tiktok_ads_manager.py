"""Lanzador y monitor de campañas de TikTok Ads (TikTok Marketing API).

Igual que el monitor de Facebook Ads, revisa el ROAS de las campañas cada
24h (configurable). Además, a diferencia de Facebook, este módulo también
puede lanzar campañas nuevas automáticamente para cada producto creado en
Shopify (campaña -> grupo de anuncios -> anuncio).

Si TikTok no está configurado, o si cualquier llamada a la API falla, el
sistema recurre a un modo "dry-run" / se degrada de forma segura para que
el pipeline nunca se detenga.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests
import schedule

from .aliexpress_scraper import Product
from .claude_generator import GeneratedCopy
from .config import config
from .notifier import notifier
from .scheduler import run_forever

BASE_URL = "https://business-api.tiktok.com/open_api/{version}/"


@dataclass
class CampaignResult:
    success: bool
    dry_run: bool
    campaign_id: Optional[str] = None
    adgroup_id: Optional[str] = None
    ad_id: Optional[str] = None
    daily_budget: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "dry_run": self.dry_run,
            "campaign_id": self.campaign_id,
            "adgroup_id": self.adgroup_id,
            "ad_id": self.ad_id,
            "daily_budget": self.daily_budget,
            "error": self.error,
        }


@dataclass
class TikTokAdInsight:
    campaign_id: str
    campaign_name: str
    spend: float
    impressions: int
    clicks: int
    purchases: int
    revenue: float

    @property
    def roas(self) -> float:
        return round(self.revenue / self.spend, 2) if self.spend else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "spend": self.spend,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "purchases": self.purchases,
            "revenue": self.revenue,
            "roas": self.roas,
        }


class TikTokAdsManager:
    """Lanza campañas y monitorea el ROAS en TikTok Ads."""

    def __init__(self):
        self.access_token = config.tiktok_access_token
        self.advertiser_id = config.tiktok_advertiser_id
        self.api_version = config.tiktok_api_version

    @property
    def is_live(self) -> bool:
        return config.tiktok_configured

    def _url(self, path: str) -> str:
        return BASE_URL.format(version=self.api_version) + path

    def _headers(self) -> Dict[str, str]:
        return {
            "Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(
            self._url(path), headers=self._headers(), json=payload, timeout=15
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") not in (0, None):
            raise RuntimeError(f"TikTok API error {data.get('code')}: {data.get('message')}")
        return data.get("data", {})

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.get(self._url(path), headers=self._headers(), params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("code") not in (0, None):
            raise RuntimeError(f"TikTok API error {data.get('code')}: {data.get('message')}")
        return data.get("data", {})

    # ------------------------------------------------------------------
    # Lanzamiento de campañas
    # ------------------------------------------------------------------

    def launch_campaign(
        self,
        product: Product,
        copy: GeneratedCopy,
        landing_page_url: Optional[str] = None,
    ) -> CampaignResult:
        """Crea campaña -> grupo de anuncios -> anuncio para un producto."""
        landing_url = landing_page_url or product.product_url

        if not self.is_live:
            notifier.warning(
                "tiktok_launch",
                f"TikTok Ads no está configurado; simulando lanzamiento de campaña "
                f"para '{copy.title}'",
            )
            return CampaignResult(
                success=True,
                dry_run=True,
                campaign_id=f"dry-run-campaign-{uuid4().hex[:8]}",
                adgroup_id=f"dry-run-adgroup-{uuid4().hex[:8]}",
                ad_id=f"dry-run-ad-{uuid4().hex[:8]}",
                daily_budget=config.tiktok_daily_budget,
            )

        try:
            campaign_id = self._create_campaign(copy)
            adgroup_id = self._create_adgroup(campaign_id, landing_url)
            image_id = self._upload_image(product.image_url) if product.image_url else None
            ad_id = self._create_ad(adgroup_id, copy, landing_url, image_id)

            notifier.success(
                "tiktok_launch",
                f"Campaña de TikTok lanzada para '{copy.title}' "
                f"(campaign_id={campaign_id}, adgroup_id={adgroup_id}, ad_id={ad_id})",
            )
            return CampaignResult(
                success=True,
                dry_run=False,
                campaign_id=campaign_id,
                adgroup_id=adgroup_id,
                ad_id=ad_id,
                daily_budget=config.tiktok_daily_budget,
            )
        except Exception as exc:  # noqa: BLE001 - degradar sin romper el pipeline
            notifier.error(
                "tiktok_launch",
                f"Error al lanzar campaña de TikTok para '{copy.title}': {exc}",
            )
            return CampaignResult(
                success=False,
                dry_run=False,
                daily_budget=config.tiktok_daily_budget,
                error=str(exc),
            )

    def _create_campaign(self, copy: GeneratedCopy) -> str:
        payload = {
            "advertiser_id": self.advertiser_id,
            "campaign_name": f"DropAgent - {copy.title}"[:512],
            "objective_type": config.tiktok_objective_type,
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": config.tiktok_daily_budget,
        }
        data = self._post("campaign/create/", payload)
        return str(data["campaign_id"])

    def _create_adgroup(self, campaign_id: str, landing_url: str) -> str:
        payload = {
            "advertiser_id": self.advertiser_id,
            "campaign_id": campaign_id,
            "adgroup_name": f"DropAgent AdGroup {campaign_id}",
            "placement_type": "PLACEMENT_TYPE_AUTOMATIC",
            "budget_mode": "BUDGET_MODE_DAY",
            "budget": config.tiktok_daily_budget,
            "schedule_type": "SCHEDULE_FROM_NOW",
            "optimization_goal": config.tiktok_optimization_goal,
            "billing_event": config.tiktok_billing_event,
            "bid_type": config.tiktok_bid_type,
            "pacing": "PACING_MODE_SMOOTH",
            "location_ids": config.tiktok_location_ids,
            "promotion_type": "WEBSITE",
            "landing_page_url": landing_url,
        }
        if config.tiktok_pixel_id:
            payload["pixel_id"] = config.tiktok_pixel_id
        data = self._post("adgroup/create/", payload)
        return str(data["adgroup_id"])

    def _upload_image(self, image_url: str) -> Optional[str]:
        try:
            payload = {
                "advertiser_id": self.advertiser_id,
                "upload_type": "UPLOAD_BY_URL",
                "image_url": image_url,
            }
            data = self._post("file/image/ad/upload/", payload)
            return str(data.get("image_id")) if data.get("image_id") else None
        except Exception as exc:  # noqa: BLE001 - la imagen es opcional
            notifier.warning("tiktok_launch", f"No se pudo subir la imagen a TikTok: {exc}")
            return None

    def _create_ad(
        self,
        adgroup_id: str,
        copy: GeneratedCopy,
        landing_url: str,
        image_id: Optional[str],
    ) -> str:
        creative: Dict[str, Any] = {
            "ad_name": copy.title[:512],
            "ad_text": copy.title[:100],
            "identity_id": config.tiktok_identity_id,
            "identity_type": config.tiktok_identity_type,
            "landing_page_url": landing_url,
            "call_to_action": "SHOP_NOW",
        }
        if image_id:
            creative["image_ids"] = [image_id]

        payload = {
            "advertiser_id": self.advertiser_id,
            "adgroup_id": adgroup_id,
            "creatives": [creative],
        }
        data = self._post("ad/create/", payload)
        ad_ids = data.get("ad_ids") or []
        return str(ad_ids[0]) if ad_ids else ""

    # ------------------------------------------------------------------
    # Monitoreo de ROAS
    # ------------------------------------------------------------------

    def fetch_insights(self) -> List[TikTokAdInsight]:
        if not self.is_live:
            notifier.warning(
                "tiktok_monitor",
                "TikTok Ads no está configurado (faltan credenciales); "
                "omitiendo revisión de campañas",
            )
            return []

        params = {
            "advertiser_id": self.advertiser_id,
            "report_type": "BASIC",
            "data_level": "AUCTION_CAMPAIGN",
            "dimensions": '["campaign_id"]',
            "metrics": (
                f'["campaign_name","spend","impressions","clicks",'
                f'"{config.tiktok_purchase_metric}","{config.tiktok_revenue_metric}"]'
            ),
            "page_size": 100,
        }
        try:
            data = self._get("report/integrated/get/", params)
        except Exception as exc:  # noqa: BLE001 - degradar sin romper el pipeline
            notifier.error("tiktok_monitor", f"Error al consultar TikTok Ads: {exc}")
            return []

        insights: List[TikTokAdInsight] = []
        for row in data.get("list", []):
            dims = row.get("dimensions", {})
            metrics = row.get("metrics", {})
            insights.append(
                TikTokAdInsight(
                    campaign_id=str(dims.get("campaign_id", "")),
                    campaign_name=str(metrics.get("campaign_name", "N/A")),
                    spend=float(metrics.get("spend", 0) or 0),
                    impressions=int(float(metrics.get("impressions", 0) or 0)),
                    clicks=int(float(metrics.get("clicks", 0) or 0)),
                    purchases=int(float(metrics.get(config.tiktok_purchase_metric, 0) or 0)),
                    revenue=float(metrics.get(config.tiktok_revenue_metric, 0) or 0),
                )
            )
        return insights

    def run_check(self) -> Dict[str, Any]:
        """Ejecuta una revisión puntual del ROAS de las campañas de TikTok."""
        insights = self.fetch_insights()

        if not insights:
            notifier.info("tiktok_monitor", "No hay datos de campañas de TikTok para revisar")
            return {"insights": [], "underperforming": []}

        underperforming = []
        for insight in insights:
            is_underperforming = (
                insight.roas < config.tiktok_min_roas
                and insight.spend >= config.tiktok_max_spend_no_sales
            )
            if is_underperforming:
                underperforming.append(insight)
                notifier.warning(
                    "tiktok_monitor",
                    f"Campaña de TikTok de bajo rendimiento: '{insight.campaign_name}' "
                    f"(gasto={insight.spend} USD, ROAS={insight.roas})",
                )

        notifier.success(
            "tiktok_monitor",
            f"Revisión completada: {len(insights)} campañas analizadas, "
            f"{len(underperforming)} con bajo rendimiento",
        )

        return {
            "insights": [i.to_dict() for i in insights],
            "underperforming": [i.to_dict() for i in underperforming],
        }

    def start_scheduler(self, interval_hours: Optional[float] = None, run_immediately: bool = True,
                         blocking: bool = True) -> None:
        """Programa `run_check` para ejecutarse cada `interval_hours` horas."""
        interval = interval_hours or config.tiktok_monitor_interval_hours
        schedule.clear("tiktok_monitor")
        schedule.every(interval).hours.do(self.run_check).tag("tiktok_monitor")

        notifier.info(
            "tiktok_monitor",
            f"Monitor de TikTok Ads programado cada {interval} horas",
        )

        if run_immediately:
            self.run_check()

        if blocking:
            run_forever()


def get_manager() -> TikTokAdsManager:
    return TikTokAdsManager()
