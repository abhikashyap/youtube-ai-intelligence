"""
Configuration loader for the YouTube AI Intelligence platform.

Reads YAML config files from the ``configs/`` directory.
"""
from __future__ import annotations

import os
from typing import Any

import yaml

_CONFIGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "configs",
)


def _load_yaml(filename: str) -> dict[str, Any]:
    """Load and parse a YAML file from the configs directory.

    Args:
        filename: Name of the YAML file (e.g. ``"channels.yaml"``).

    Returns:
        Parsed dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    filepath = os.path.join(_CONFIGS_DIR, filename)
    with open(filepath, "r") as fh:
        return yaml.safe_load(fh) or {}


def load_channels_config() -> list[dict[str, Any]]:
    """Return the list of channel definitions from ``channels.yaml``.

    Each entry has keys: ``id``, ``name``, ``max_results``.
    """
    data = _load_yaml("channels.yaml")
    return data.get("channels", [])


def load_keywords_config() -> list[dict[str, Any]]:
    """Return the list of keyword definitions from ``discovery_keywords.yaml``.

    Each entry has keys: ``keyword``, ``max_results``.
    """
    data = _load_yaml("discovery_keywords.yaml")
    return data.get("keywords", [])


def get_youtube_api_key() -> str:
    """Return the YouTube Data API key from the environment.

    Raises:
        EnvironmentError: If ``YOUTUBE_API_KEY`` is not set.
    """
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise EnvironmentError(
            "YOUTUBE_API_KEY environment variable is not set. "
            "Set it before running ingestion."
        )
    return key
