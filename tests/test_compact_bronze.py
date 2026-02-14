"""Tests for bronze metadata compaction and the JSONL fallback reader."""
from __future__ import annotations

import json
import os
from datetime import date
from unittest.mock import patch

import pytest

from jobs.ingestion.compact_bronze_metadata import compact_partition
from utils.path_builder import (
    build_compacted_jsonl_path,
    build_compaction_manifest_path,
    get_bronze_metadata_path,
    iter_compacted_bronze_records,
)

TEST_DT = date(2026, 2, 14)
SOURCE = "channel"
IDENTIFIER = "UC_TEST_CHANNEL"


def _make_video(video_id: str) -> dict:
    """Return a minimal video metadata dict."""
    return {
        "kind": "youtube#video",
        "id": video_id,
        "snippet": {"title": f"Video {video_id}"},
    }


def _write_video_json(partition_dir: str, video_id: str) -> str:
    """Write a single video JSON file into *partition_dir* and return its path."""
    os.makedirs(partition_dir, exist_ok=True)
    filepath = os.path.join(partition_dir, f"video_{video_id}.json")
    with open(filepath, "w") as fh:
        json.dump(_make_video(video_id), fh)
    return filepath


# ──────────────────────────────────────────────
# compact_partition tests
# ──────────────────────────────────────────────


def test_compact_creates_jsonl_from_individual_files(tmp_path):
    """Given 3 video JSONs, compaction produces a 3-line JSONL."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        partition_dir = get_bronze_metadata_path(SOURCE, IDENTIFIER, TEST_DT)
        for vid in ["aaa", "bbb", "ccc"]:
            _write_video_json(partition_dir, vid)

        result = compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        assert result["files_found"] == 3
        assert result["files_compacted"] == 3
        assert result["files_skipped"] == 0
        assert result["errors"] == 0

        jsonl = build_compacted_jsonl_path(SOURCE, IDENTIFIER, TEST_DT)
        with open(jsonl) as fh:
            lines = [l for l in fh if l.strip()]
        assert len(lines) == 3

        ids = {json.loads(line)["id"] for line in lines}
        assert ids == {"aaa", "bbb", "ccc"}


def test_compact_is_idempotent(tmp_path):
    """Running compaction twice does not duplicate records."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        partition_dir = get_bronze_metadata_path(SOURCE, IDENTIFIER, TEST_DT)
        for vid in ["aaa", "bbb"]:
            _write_video_json(partition_dir, vid)

        compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        # Originals were deleted; re-create them to simulate a second run.
        for vid in ["aaa", "bbb"]:
            _write_video_json(partition_dir, vid)

        result = compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        assert result["files_skipped"] == 2
        assert result["files_compacted"] == 0

        jsonl = build_compacted_jsonl_path(SOURCE, IDENTIFIER, TEST_DT)
        with open(jsonl) as fh:
            lines = [l for l in fh if l.strip()]
        assert len(lines) == 2


def test_compact_incremental(tmp_path):
    """New files after first compaction are appended, not duplicated."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        partition_dir = get_bronze_metadata_path(SOURCE, IDENTIFIER, TEST_DT)

        # First batch.
        for vid in ["aaa", "bbb"]:
            _write_video_json(partition_dir, vid)
        compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        # Second batch — new video.
        _write_video_json(partition_dir, "ccc")
        result = compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        assert result["files_compacted"] == 1
        assert result["files_skipped"] == 0

        jsonl = build_compacted_jsonl_path(SOURCE, IDENTIFIER, TEST_DT)
        with open(jsonl) as fh:
            lines = [l for l in fh if l.strip()]
        assert len(lines) == 3


def test_compact_removes_originals(tmp_path):
    """Original video_*.json files are deleted after compaction."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        partition_dir = get_bronze_metadata_path(SOURCE, IDENTIFIER, TEST_DT)
        for vid in ["aaa", "bbb"]:
            _write_video_json(partition_dir, vid)

        compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        remaining = [f for f in os.listdir(partition_dir) if f.startswith("video_")]
        assert remaining == []


def test_compact_preserves_originals_on_error(tmp_path):
    """If a file fails to parse, originals are kept."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        partition_dir = get_bronze_metadata_path(SOURCE, IDENTIFIER, TEST_DT)
        _write_video_json(partition_dir, "aaa")

        # Write a malformed JSON file.
        bad_path = os.path.join(partition_dir, "video_bad.json")
        with open(bad_path, "w") as fh:
            fh.write("{not valid json")

        result = compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        assert result["errors"] == 1
        # Originals should still be on disk.
        remaining = [f for f in os.listdir(partition_dir) if f.startswith("video_")]
        assert len(remaining) == 2


def test_compact_writes_manifest(tmp_path):
    """Manifest contains correct operational metadata."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        partition_dir = get_bronze_metadata_path(SOURCE, IDENTIFIER, TEST_DT)
        _write_video_json(partition_dir, "aaa")

        compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        manifest_path = build_compaction_manifest_path(SOURCE, IDENTIFIER, TEST_DT)
        with open(manifest_path) as fh:
            manifest = json.load(fh)

        assert manifest["source"] == SOURCE
        assert manifest["identifier"] == IDENTIFIER
        assert manifest["dt"] == TEST_DT.isoformat()
        assert manifest["total_records"] == 1
        assert manifest["errors_this_run"] == 0
        assert "video_aaa.json" in manifest["files_compacted_this_run"]


def test_compact_empty_partition(tmp_path):
    """Compacting a nonexistent partition returns zero counts."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        result = compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        assert result == {
            "files_found": 0,
            "files_compacted": 0,
            "files_skipped": 0,
            "errors": 0,
        }


# ──────────────────────────────────────────────
# iter_compacted_bronze_records tests
# ──────────────────────────────────────────────


def test_iter_reads_jsonl(tmp_path):
    """Reader returns records from compacted JSONL."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        partition_dir = get_bronze_metadata_path(SOURCE, IDENTIFIER, TEST_DT)
        for vid in ["aaa", "bbb"]:
            _write_video_json(partition_dir, vid)

        compact_partition(SOURCE, IDENTIFIER, TEST_DT)

        records = iter_compacted_bronze_records(SOURCE, IDENTIFIER, TEST_DT)
        assert len(records) == 2
        assert {r["id"] for r in records} == {"aaa", "bbb"}


def test_iter_falls_back_to_individual_files(tmp_path):
    """When no JSONL exists, reader falls back to individual files."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        partition_dir = get_bronze_metadata_path(SOURCE, IDENTIFIER, TEST_DT)
        for vid in ["aaa", "bbb"]:
            _write_video_json(partition_dir, vid)

        records = iter_compacted_bronze_records(SOURCE, IDENTIFIER, TEST_DT)
        assert len(records) == 2
        assert {r["id"] for r in records} == {"aaa", "bbb"}
