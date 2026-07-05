"""Bucle compartido para ejecutar tareas programadas con la librería `schedule`.

Tanto el monitor de Facebook Ads como el de TikTok Ads registran sus
propios trabajos (`schedule.every(...).do(...)`); este módulo simplemente
mantiene vivo el proceso y dispara los trabajos pendientes, permitiendo
que ambos monitores corran de forma concurrente en un solo loop.
"""

from __future__ import annotations

import time

import schedule

from .notifier import notifier


def run_forever(sleep_seconds: int = 60) -> None:
    """Ejecuta `schedule.run_pending()` en bucle hasta recibir Ctrl+C."""
    try:
        while True:
            schedule.run_pending()
            time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        notifier.info("scheduler", "Programador detenido por el usuario")
