"""
Path builder utility for the YouTube AI Intelligence platform.

Abstracts all file path construction so storage backends (local, S3)
can be swapped without touching business logic.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# Root of the local data lake — override via DATA_ROOT env var.
_DEFAULT_DATA_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
)
DATA_ROOT: str = os.environ.get("DATA_ROOT", _DEFAULT_DATA_ROOT)


def get_bronze_metadata_path(
    source: str,
    identifier: str,
    dt: date | None = None,
) -> str:
    """Return the directory for a bronze metadata partition.

    Args:
        source: Ingestion source — ``"channel"`` or ``"search"``.
        identifier: For *channel* source this is the channel ID;
                    for *search* source this is the keyword string.
        dt: Partition date. Defaults to today.

    Returns:
        Absolute path to the partition directory.
    """
    if dt is None:
        dt = date.today()

    dt_str = dt.strftime("%Y-%m-%d")

    if source == "channel":
        return os.path.join(
            DATA_ROOT,
            "bronze",
            "metadata",
            f"source={source}",
            f"dt={dt_str}",
            identifier,
        )
    elif source == "search":
        safe_keyword = _sanitise_keyword(identifier)
        return os.path.join(
            DATA_ROOT,
            "bronze",
            "metadata",
            f"source={source}",
            f"dt={dt_str}",
            f"keyword={safe_keyword}",
        )
    else:
        raise ValueError(f"Unknown source type: {source!r}. Expected 'channel' or 'search'.")


def build_video_file_path(
    source: str,
    identifier: str,
    video_id: str,
    dt: date | None = None,
) -> str:
    """Return the full file path for a single video JSON file.

    Args:
        source: ``"channel"`` or ``"search"``.
        identifier: Channel ID or keyword string.
        video_id: YouTube video ID.
        dt: Partition date.

    Returns:
        Absolute path ending in ``video_<video_id>.json``.
    """
    directory = get_bronze_metadata_path(source, identifier, dt)
    return os.path.join(directory, f"video_{video_id}.json")


def _sanitise_keyword(keyword: str) -> str:
    """Make a keyword string safe for use in directory names."""
    return keyword.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")


def ensure_directory(path: str) -> None:
    """Create directory (and parents) if it does not exist."""
    Path(path).mkdir(parents=True, exist_ok=True)
