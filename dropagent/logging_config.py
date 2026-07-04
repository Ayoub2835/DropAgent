"""Application-wide logging configuration.

Logs go to stdout (for container/orchestrator capture) and to a rotating
file under ``settings.log_dir`` so a full run can be inspected after the
fact. Call ``setup_logging()`` once, early, from the CLI entrypoint.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from dropagent.config import get_settings

_CONFIGURED = False

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str | None = None) -> None:
    """Configure the root logger exactly once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    resolved_level = getattr(logging, (level or settings.log_level).upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    log_file = settings.log_dir / "dropagent.log"
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Silence noisy third-party libraries unless we are in DEBUG.
    if resolved_level > logging.DEBUG:
        for noisy in ("urllib3", "httpx", "httpcore", "openai", "PIL"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Convenience accessor so modules can do ``log = get_logger(__name__)``."""
    setup_logging()
    return logging.getLogger(name)
