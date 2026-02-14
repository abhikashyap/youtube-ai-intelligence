"""
Bronze metadata compaction for the YouTube AI Intelligence platform.

Merges individual per-video JSON files within each bronze partition
into a single JSONL file (``_compacted.jsonl``), reducing filesystem
overhead and improving downstream read performance.

Entry point: ``run_bronze_compaction()``
"""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import date
from typing import Any

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils.config_loader import load_channels_config, load_keywords_config
from utils.logging_utils import get_logger
from utils.path_builder import (
    build_compacted_jsonl_path,
    build_compaction_manifest_path,
    get_bronze_metadata_path,
)

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────

def compact_partition(
    source: str,
    identifier: str,
    dt: date,
) -> dict[str, int]:
    """Compact all ``video_*.json`` files in a partition into ``_compacted.jsonl``.

    Algorithm:
    1. List all ``video_*.json`` files in the partition directory.
    2. If ``_compacted.jsonl`` already exists, load its video IDs for
       incremental (append-only) compaction.
    3. Append new records as single JSON lines to the JSONL file.
    4. Write a ``_compaction_manifest.json`` with operational metadata.
    5. Delete the original ``video_*.json`` files (only when zero errors).

    Returns:
        Summary dict with keys ``files_found``, ``files_compacted``,
        ``files_skipped``, ``errors``.
    """
    partition_dir = get_bronze_metadata_path(source, identifier, dt)
    jsonl_path = build_compacted_jsonl_path(source, identifier, dt)
    manifest_path = build_compaction_manifest_path(source, identifier, dt)

    if not os.path.isdir(partition_dir):
        logger.info("Partition directory does not exist, skipping: %s", partition_dir)
        return {"files_found": 0, "files_compacted": 0, "files_skipped": 0, "errors": 0}

    json_files = sorted(glob.glob(os.path.join(partition_dir, "video_*.json")))

    if not json_files:
        logger.info("No video JSON files found in %s", partition_dir)
        return {"files_found": 0, "files_compacted": 0, "files_skipped": 0, "errors": 0}

    # Load already-compacted video IDs for incremental support.
    existing_ids: set[str] = set()
    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        existing_ids.add(record["id"])
                    except (json.JSONDecodeError, KeyError):
                        pass

    compacted = 0
    skipped = 0
    errors = 0
    compacted_files: list[str] = []

    with open(jsonl_path, "a") as out_fh:
        for json_file in json_files:
            try:
                with open(json_file, "r") as in_fh:
                    video = json.load(in_fh)

                video_id = video["id"]
                if video_id in existing_ids:
                    skipped += 1
                    continue

                out_fh.write(json.dumps(video, separators=(",", ":")) + "\n")
                existing_ids.add(video_id)
                compacted += 1
                compacted_files.append(os.path.basename(json_file))

            except Exception:
                logger.exception("Error compacting file: %s", json_file)
                errors += 1

    # Write manifest.
    manifest = {
        "source": source,
        "identifier": identifier,
        "dt": dt.isoformat(),
        "compacted_at": date.today().isoformat(),
        "total_records": len(existing_ids),
        "files_compacted_this_run": compacted_files,
        "files_skipped_this_run": skipped,
        "errors_this_run": errors,
    }
    with open(manifest_path, "w") as mf:
        json.dump(manifest, mf, indent=2)

    # Delete originals only when zero errors.
    if errors == 0:
        for json_file in json_files:
            os.remove(json_file)
        logger.info(
            "Removed %d original JSON files from %s", len(json_files), partition_dir,
        )

    logger.info(
        "Compacted partition %s — found=%d, compacted=%d, skipped=%d, errors=%d",
        partition_dir, len(json_files), compacted, skipped, errors,
    )
    return {
        "files_found": len(json_files),
        "files_compacted": compacted,
        "files_skipped": skipped,
        "errors": errors,
    }


# ──────────────────────────────────────────────
# Orchestration
# ──────────────────────────────────────────────

def run_bronze_compaction(dt: date | None = None, **kwargs: Any) -> None:
    """Airflow-callable entry point.

    Iterates over all configured channels and keywords, compacting
    each partition's individual JSON files into a single JSONL.
    """
    if dt is None:
        dt = date.today()

    logger.info("=== Bronze compaction started (dt=%s) ===", dt)

    channels = load_channels_config()
    keywords = load_keywords_config()

    total = {"files_found": 0, "files_compacted": 0, "files_skipped": 0, "errors": 0}

    for ch in channels:
        try:
            result = compact_partition(
                source="channel",
                identifier=ch["id"],
                dt=dt,
            )
            for key in total:
                total[key] += result[key]
        except Exception:
            logger.exception("Failed to compact channel partition %s", ch["id"])
            total["errors"] += 1

    for kw in keywords:
        try:
            result = compact_partition(
                source="search",
                identifier=kw["keyword"],
                dt=dt,
            )
            for key in total:
                total[key] += result[key]
        except Exception:
            logger.exception("Failed to compact keyword partition %s", kw["keyword"])
            total["errors"] += 1

    logger.info(
        "=== Bronze compaction complete — found=%d, compacted=%d, skipped=%d, errors=%d ===",
        total["files_found"], total["files_compacted"],
        total["files_skipped"], total["errors"],
    )


if __name__ == "__main__":
    run_bronze_compaction(dt=date.fromisoformat("2026-02-14"))
