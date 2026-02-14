"""
Path builder utility for the YouTube AI Intelligence platform.

Abstracts all file path construction so storage backends (local, S3)
can be swapped without touching business logic.
"""
from __future__ import annotations

import glob as _glob
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

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


def build_compacted_jsonl_path(
    source: str,
    identifier: str,
    dt: date | None = None,
) -> str:
    """Return the path for the compacted JSONL file within a bronze partition."""
    directory = get_bronze_metadata_path(source, identifier, dt)
    return os.path.join(directory, "_compacted.jsonl")


def build_compaction_manifest_path(
    source: str,
    identifier: str,
    dt: date | None = None,
) -> str:
    """Return the path for the compaction manifest within a bronze partition."""
    directory = get_bronze_metadata_path(source, identifier, dt)
    return os.path.join(directory, "_compaction_manifest.json")


def iter_compacted_bronze_records(
    source: str,
    identifier: str,
    dt: date | None = None,
) -> list[dict[str, Any]]:
    """Read all records from a compacted JSONL bronze partition.

    Falls back to reading individual ``video_*.json`` files if no
    compacted file exists yet (backward compatibility).
    """
    jsonl_path = build_compacted_jsonl_path(source, identifier, dt)

    if os.path.exists(jsonl_path):
        records = []
        with open(jsonl_path, "r") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    # Fallback: read individual files
    partition_dir = get_bronze_metadata_path(source, identifier, dt)
    if not os.path.isdir(partition_dir):
        return []

    records = []
    for json_file in sorted(_glob.glob(os.path.join(partition_dir, "video_*.json"))):
        with open(json_file, "r") as fh:
            records.append(json.load(fh))
    return records
