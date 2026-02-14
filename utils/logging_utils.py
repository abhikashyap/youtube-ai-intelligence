"""
Centralised logging configuration for the YouTube AI Intelligence platform.
"""
from __future__ import annotations

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a consistently-configured logger.

    Args:
        name: Logger name — typically ``__name__`` of the calling module.
        level: Logging level (default ``INFO``).

    Returns:
        A ``logging.Logger`` with a stream handler attached (if not already).
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
