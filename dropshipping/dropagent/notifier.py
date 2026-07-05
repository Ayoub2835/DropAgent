"""Sistema de notificaciones de DropAgent: consola + archivo log.json.

Reemplaza temporalmente al bot de Telegram. Cada evento se imprime en
consola con un formato legible y se persiste en un archivo JSON para
poder consultar el historial más adelante.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import config

_LOCK = threading.Lock()

_LEVEL_ICONS = {
    "info": "ℹ️ ",
    "success": "✅",
    "warning": "⚠️ ",
    "error": "❌",
    "product": "🛒",
    "ad": "📊",
}


class Notifier:
    """Gestiona la salida por consola y la persistencia en log.json."""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file or config.log_file

    def notify(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None,
               level: str = "info") -> Dict[str, Any]:
        """Registra un evento: lo imprime en consola y lo guarda en log.json."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "level": level,
            "message": message,
            "data": data or {},
        }
        self._print(entry)
        self._append_to_file(entry)
        return entry

    def info(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
        return self.notify(event_type, message, data, level="info")

    def success(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
        return self.notify(event_type, message, data, level="success")

    def warning(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
        return self.notify(event_type, message, data, level="warning")

    def error(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
        return self.notify(event_type, message, data, level="error")

    def _print(self, entry: Dict[str, Any]) -> None:
        # Se imprime en stderr para que stdout quede libre para la salida
        # `--json` de los comandos del CLI.
        icon = _LEVEL_ICONS.get(entry["level"], "•")
        ts = entry["timestamp"].replace("T", " ").split(".")[0]
        print(f"[{ts}] {icon} [{entry['event_type']}] {entry['message']}", file=sys.stderr)

    def _append_to_file(self, entry: Dict[str, Any]) -> None:
        with _LOCK:
            history = self._read_all_unlocked()
            history.append(entry)
            tmp_path = f"{self.log_file}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.log_file)

    def _read_all_unlocked(self) -> list:
        if not os.path.exists(self.log_file):
            return []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return []

    def read_history(self) -> list:
        with _LOCK:
            return self._read_all_unlocked()


notifier = Notifier()
