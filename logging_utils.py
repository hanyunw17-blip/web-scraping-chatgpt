"""Shared logging helpers for Google Play scripts."""
from __future__ import annotations

import logging
import os
from typing import Optional


def _resolve_level(default: int = logging.INFO) -> int:
    env_level = os.getenv("GOOGLEPLAY_LOG_LEVEL")
    if not env_level:
        return default
    if env_level.isdigit():
        return int(env_level)
    return logging._nameToLevel.get(env_level.upper(), default)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger configured for CLI use."""
    logger = logging.getLogger(name if name else "googleplay")
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(_resolve_level())
    logger.propagate = False
    return logger
