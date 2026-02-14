"""
Tests for channel-based metadata ingestion.

All YouTube API calls are mocked — no real network traffic.
"""
from __future__ import annotations

import json
import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from jobs.ingestion.fetch_channel_metadata import (
    QuotaExceededError,
    fetch_video_ids_for_channel,
    fetch_video_metadata,
    ingest_channel,
    save_video_json,
)
from utils.path_builder import build_video_file_path


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

FAKE_API_KEY = "FAKE_KEY"
FAKE_CHANNEL_ID = "UC_TEST_CHANNEL"
TEST_DATE = date(2025, 6, 15)


def _make_search_response(video_ids: list[str]) -> dict:
    """Build a mock search.list API response."""
    return {
        "items": [{"id": {"videoId": vid}} for vid in video_ids],
    }


def _make_videos_response(video_ids: list[str]) -> dict:
    """Build a mock videos.list API response with realistic structure."""
    items = []
    for vid in video_ids:
        items.append({
            "id": vid,
            "snippet": {
                "title": f"Video {vid}",
                "description": "A test video.",
                "channelId": FAKE_CHANNEL_ID,
                "publishedAt": "2025-06-15T00:00:00Z",
                "tags": ["test"],
            },
            "contentDetails": {"duration": "PT10M30S"},
            "statistics": {
                "viewCount": "1000",
                "likeCount": "50",
                "commentCount": "10",
            },
        })
    return {"items": items}


# ──────────────────────────────────────────────
# Tests — fetch_video_ids_for_channel
# ──────────────────────────────────────────────

@patch("jobs.ingestion.fetch_channel_metadata._api_get")
def test_fetch_video_ids_returns_ids(mock_api_get: MagicMock) -> None:
    mock_api_get.return_value = _make_search_response(["v1", "v2", "v3"])

    ids = fetch_video_ids_for_channel(FAKE_API_KEY, FAKE_CHANNEL_ID, max_results=5)

    assert ids == ["v1", "v2", "v3"]
    mock_api_get.assert_called_once()


@patch("jobs.ingestion.fetch_channel_metadata._api_get")
def test_fetch_video_ids_respects_max_results(mock_api_get: MagicMock) -> None:
    mock_api_get.return_value = _make_search_response(
        [f"v{i}" for i in range(10)]
    )

    ids = fetch_video_ids_for_channel(FAKE_API_KEY, FAKE_CHANNEL_ID, max_results=3)

    assert len(ids) == 3


# ──────────────────────────────────────────────
# Tests — fetch_video_metadata
# ──────────────────────────────────────────────

@patch("jobs.ingestion.fetch_channel_metadata._api_get")
def test_fetch_video_metadata_returns_items(mock_api_get: MagicMock) -> None:
    mock_api_get.return_value = _make_videos_response(["v1", "v2"])

    items = fetch_video_metadata(FAKE_API_KEY, ["v1", "v2"])

    assert len(items) == 2
    assert items[0]["id"] == "v1"


# ──────────────────────────────────────────────
# Tests — save_video_json (idempotency + paths)
# ──────────────────────────────────────────────

def test_save_video_json_creates_file(tmp_path: pytest.TempPathFactory) -> None:
    """A new video should be written to disk."""
    video = {"id": "abc123", "snippet": {"title": "Test"}}

    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        with patch(
            "jobs.ingestion.fetch_channel_metadata.build_video_file_path",
            wraps=build_video_file_path,
        ):
            filepath = build_video_file_path(
                "channel", FAKE_CHANNEL_ID, "abc123", TEST_DATE
            )
            # Ensure the function writes the file
            wrote = save_video_json(video, "channel", FAKE_CHANNEL_ID, TEST_DATE)

    assert wrote is True
    assert os.path.exists(filepath)

    with open(filepath) as f:
        data = json.load(f)
    assert data["id"] == "abc123"


def test_save_video_json_skips_existing(tmp_path: pytest.TempPathFactory) -> None:
    """If a file already exists, save should return False (idempotent)."""
    video = {"id": "abc123", "snippet": {"title": "Test"}}

    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        # First write
        save_video_json(video, "channel", FAKE_CHANNEL_ID, TEST_DATE)
        # Second write — should skip
        wrote = save_video_json(video, "channel", FAKE_CHANNEL_ID, TEST_DATE)

    assert wrote is False


# ──────────────────────────────────────────────
# Tests — path structure
# ──────────────────────────────────────────────

def test_channel_path_structure(tmp_path: pytest.TempPathFactory) -> None:
    """Verify the bronze path follows the expected pattern."""
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        path = build_video_file_path("channel", "UC_XYZ", "vid1", TEST_DATE)

    assert "source=channel" in path
    assert "dt=2025-06-15" in path
    assert "UC_XYZ" in path
    assert path.endswith("video_vid1.json")


# ──────────────────────────────────────────────
# Tests — ingest_channel (integration-style, mocked API)
# ──────────────────────────────────────────────

@patch("jobs.ingestion.fetch_channel_metadata._api_get")
def test_ingest_channel_end_to_end(mock_api_get: MagicMock, tmp_path: pytest.TempPathFactory) -> None:
    """Full pipeline: search → metadata → save."""
    mock_api_get.side_effect = [
        _make_search_response(["v1", "v2"]),
        _make_videos_response(["v1", "v2"]),
    ]

    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        result = ingest_channel(
            api_key=FAKE_API_KEY,
            channel_id=FAKE_CHANNEL_ID,
            channel_name="TestChannel",
            max_results=5,
            dt=TEST_DATE,
        )

    assert result["fetched"] == 2
    assert result["written"] == 2
    assert result["skipped"] == 0


@patch("jobs.ingestion.fetch_channel_metadata._api_get")
def test_ingest_channel_idempotent_on_rerun(mock_api_get: MagicMock, tmp_path: pytest.TempPathFactory) -> None:
    """Running ingestion twice should skip already-written files."""
    search_resp = _make_search_response(["v1"])
    videos_resp = _make_videos_response(["v1"])

    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        mock_api_get.side_effect = [search_resp, videos_resp]
        first = ingest_channel(FAKE_API_KEY, FAKE_CHANNEL_ID, "Test", 5, TEST_DATE)

        mock_api_get.side_effect = [search_resp, videos_resp]
        second = ingest_channel(FAKE_API_KEY, FAKE_CHANNEL_ID, "Test", 5, TEST_DATE)

    assert first["written"] == 1
    assert second["written"] == 0
    assert second["skipped"] == 1


# ──────────────────────────────────────────────
# Tests — error handling
# ──────────────────────────────────────────────

@patch("jobs.ingestion.fetch_channel_metadata._api_get")
def test_quota_error_raises(mock_api_get: MagicMock) -> None:
    mock_api_get.side_effect = QuotaExceededError("quota hit")

    with pytest.raises(QuotaExceededError):
        fetch_video_ids_for_channel(FAKE_API_KEY, FAKE_CHANNEL_ID)
