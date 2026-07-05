"""Generador de vídeos publicitarios con la API de Higgsfield.

Cuando un producto es aprobado (creado con éxito en Shopify), este módulo
llama a la API de Higgsfield para generar automáticamente un vídeo corto
tipo anuncio a partir de la imagen y la descripción del producto.

Si HIGGSFIELD_API_KEY no está configurada, o si la llamada a la API falla,
tarda demasiado o agota el tiempo de espera, se degrada a un modo
"dry-run" para que el pipeline nunca se detenga ni gaste presupuesto.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import requests

from .aliexpress_scraper import Product
from .claude_generator import GeneratedCopy
from .config import config
from .notifier import notifier
from .utils import slugify


@dataclass
class VideoResult:
    success: bool
    dry_run: bool
    job_id: Optional[str] = None
    video_url: Optional[str] = None
    local_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "dry_run": self.dry_run,
            "job_id": self.job_id,
            "video_url": self.video_url,
            "local_path": self.local_path,
            "error": self.error,
        }


class HiggsfieldVideoGenerator:
    """Genera vídeos publicitarios cortos con la API de Higgsfield."""

    def __init__(self):
        self.api_key = config.higgsfield_api_key
        self.base_url = config.higgsfield_api_base_url.rstrip("/")
        self.output_dir = Path(config.higgsfield_video_output_dir)

    @property
    def is_live(self) -> bool:
        return config.higgsfield_configured

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _build_prompt(product: Product, copy: GeneratedCopy) -> str:
        return (
            f"Vídeo publicitario corto y dinámico para redes sociales, estilo "
            f"anuncio de producto de e-commerce. Producto: {copy.title}. "
            f"Muestra el producto en uso, con buena iluminación, ritmo rápido "
            f"y texto llamativo, orientado a conversión de ventas."
        )

    def generate_ad_video(self, product: Product, copy: GeneratedCopy) -> VideoResult:
        """Genera (o simula) un vídeo publicitario para un producto aprobado."""
        if not self.is_live:
            notifier.warning(
                "higgsfield_video",
                f"Higgsfield no está configurado; omitiendo generación de vídeo "
                f"para '{copy.title}' (modo dry-run)",
            )
            return VideoResult(success=True, dry_run=True, job_id=f"dry-run-{uuid4().hex[:8]}")

        try:
            job_id = self._submit_job(product, copy)
            video_url = self._poll_until_done(job_id)
            local_path = self._download_video(video_url, product, copy)

            notifier.success(
                "higgsfield_video",
                f"Vídeo generado con Higgsfield para '{copy.title}' -> {local_path}",
            )
            return VideoResult(
                success=True,
                dry_run=False,
                job_id=job_id,
                video_url=video_url,
                local_path=str(local_path),
            )
        except Exception as exc:  # noqa: BLE001 - degradar sin romper el pipeline
            notifier.error(
                "higgsfield_video",
                f"Error al generar vídeo con Higgsfield para '{copy.title}': {exc}",
            )
            return VideoResult(success=False, dry_run=False, error=str(exc))

    def _submit_job(self, product: Product, copy: GeneratedCopy) -> str:
        payload: Dict[str, Any] = {
            "model": config.higgsfield_model,
            "prompt": self._build_prompt(product, copy),
            "aspect_ratio": config.higgsfield_aspect_ratio,
            "duration": config.higgsfield_video_duration_seconds,
        }
        if product.image_url:
            payload["image_url"] = product.image_url

        response = requests.post(
            f"{self.base_url}/{config.higgsfield_generate_endpoint}",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        job_id = data.get("id") or data.get("job_id")
        if not job_id:
            raise RuntimeError(f"Respuesta de Higgsfield sin job id: {data}")
        return str(job_id)

    def _poll_until_done(self, job_id: str) -> str:
        deadline = time.monotonic() + config.higgsfield_poll_timeout_seconds
        while time.monotonic() < deadline:
            response = requests.get(
                f"{self.base_url}/{config.higgsfield_status_endpoint}/{job_id}",
                headers=self._headers(),
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            status = str(data.get("status", "")).lower()

            if status in ("completed", "succeeded", "success"):
                video_url = data.get("video_url") or (data.get("output") or {}).get("video_url")
                if not video_url:
                    raise RuntimeError(f"Job de Higgsfield completado sin video_url: {data}")
                return video_url
            if status in ("failed", "error"):
                raise RuntimeError(f"Job de Higgsfield falló: {data.get('error', data)}")

            time.sleep(config.higgsfield_poll_interval_seconds)

        raise TimeoutError(
            f"Tiempo de espera agotado esperando el vídeo de Higgsfield (job_id={job_id})"
        )

    def _download_video(self, video_url: str, product: Product, copy: GeneratedCopy) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        slug = slugify(copy.title or product.title)
        file_path = self.output_dir / f"{slug}-{uuid4().hex[:6]}.mp4"

        response = requests.get(video_url, timeout=60, stream=True)
        response.raise_for_status()
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 16):
                f.write(chunk)
        return file_path


def get_video_generator() -> HiggsfieldVideoGenerator:
    return HiggsfieldVideoGenerator()
