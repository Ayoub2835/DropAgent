"""Monitor de rendimiento de Facebook Ads, ejecutado cada 24h por defecto."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
import schedule

from .config import config
from .notifier import notifier
from .scheduler import run_forever

INSIGHT_FIELDS = "spend,impressions,clicks,ctr,cpc,actions,action_values,campaign_name,ad_name"


@dataclass
class AdInsight:
    ad_name: str
    campaign_name: str
    spend: float
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    purchases: int
    revenue: float

    @property
    def roas(self) -> float:
        return round(self.revenue / self.spend, 2) if self.spend else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ad_name": self.ad_name,
            "campaign_name": self.campaign_name,
            "spend": self.spend,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "ctr": self.ctr,
            "cpc": self.cpc,
            "purchases": self.purchases,
            "revenue": self.revenue,
            "roas": self.roas,
        }


class FacebookAdsMonitor:
    """Consulta el rendimiento de las campañas activas vía Graph API Insights."""

    def __init__(self):
        self.access_token = config.facebook_access_token
        self.ad_account_id = config.facebook_ad_account_id
        self.api_version = config.facebook_api_version

    @property
    def is_live(self) -> bool:
        return config.facebook_configured

    def _insights_url(self) -> str:
        account = self.ad_account_id
        if not account.startswith("act_"):
            account = f"act_{account}"
        return f"https://graph.facebook.com/{self.api_version}/{account}/insights"

    def fetch_insights(self) -> List[AdInsight]:
        if not self.is_live:
            notifier.warning(
                "facebook_monitor",
                "Facebook Ads no está configurado (faltan credenciales); "
                "omitiendo revisión de campañas",
            )
            return []

        params = {
            "level": "ad",
            "fields": INSIGHT_FIELDS,
            "date_preset": "yesterday",
            "access_token": self.access_token,
        }
        try:
            response = requests.get(self._insights_url(), params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            notifier.error("facebook_monitor", f"Error al consultar Facebook Ads: {exc}")
            return []

        insights: List[AdInsight] = []
        for row in payload.get("data", []):
            purchases = self._extract_action_count(row.get("actions", []), "purchase")
            revenue = self._extract_action_count(row.get("action_values", []), "purchase")
            insights.append(
                AdInsight(
                    ad_name=row.get("ad_name", "N/A"),
                    campaign_name=row.get("campaign_name", "N/A"),
                    spend=float(row.get("spend", 0) or 0),
                    impressions=int(row.get("impressions", 0) or 0),
                    clicks=int(row.get("clicks", 0) or 0),
                    ctr=float(row.get("ctr", 0) or 0),
                    cpc=float(row.get("cpc", 0) or 0),
                    purchases=int(purchases),
                    revenue=revenue,
                )
            )
        return insights

    @staticmethod
    def _extract_action_count(actions: List[Dict[str, Any]], action_type: str) -> float:
        for action in actions:
            if action.get("action_type") == action_type:
                return float(action.get("value", 0) or 0)
        return 0.0

    def run_check(self) -> Dict[str, Any]:
        """Ejecuta una revisión puntual de las campañas y notifica los resultados."""
        insights = self.fetch_insights()

        if not insights:
            notifier.info("facebook_monitor", "No hay datos de campañas para revisar")
            return {"insights": [], "underperforming": []}

        underperforming = []
        for insight in insights:
            is_underperforming = (
                insight.roas < config.facebook_min_roas
                and insight.spend >= config.facebook_max_spend_no_sales
            )
            if is_underperforming:
                underperforming.append(insight)
                notifier.warning(
                    "facebook_monitor",
                    f"Anuncio de bajo rendimiento: '{insight.ad_name}' "
                    f"(gasto={insight.spend} USD, ROAS={insight.roas})",
                )

        notifier.success(
            "facebook_monitor",
            f"Revisión completada: {len(insights)} anuncios analizados, "
            f"{len(underperforming)} con bajo rendimiento",
        )

        return {
            "insights": [i.to_dict() for i in insights],
            "underperforming": [i.to_dict() for i in underperforming],
        }

    def start_scheduler(self, interval_hours: Optional[float] = None, run_immediately: bool = True,
                         blocking: bool = True) -> None:
        """Programa `run_check` para ejecutarse cada `interval_hours` horas.

        Por defecto queda en un bucle bloqueante; usar blocking=False para
        integrarlo en un hilo o loop externo.
        """
        interval = interval_hours or config.facebook_monitor_interval_hours
        schedule.clear("facebook_monitor")
        schedule.every(interval).hours.do(self.run_check).tag("facebook_monitor")

        notifier.info(
            "facebook_monitor",
            f"Monitor de Facebook Ads programado cada {interval} horas",
        )

        if run_immediately:
            self.run_check()

        if blocking:
            run_forever()


def get_monitor() -> FacebookAdsMonitor:
    return FacebookAdsMonitor()
