"""
Tests for keyword-based metadata ingestion.

All YouTube API calls are mocked — no real network traffic.
"""
from __future__ import annotations

import json
import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from jobs.ingestion.fetch_keyword_metadata import (
    QuotaExceededError,
    fetch_video_metadata,
    ingest_keyword,
    save_video_json,
    search_videos_by_keyword,
)
from utils.path_builder import build_video_file_path


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

FAKE_API_KEY = "FAKE_KEY"
TEST_KEYWORD = "spark structured streaming"
TEST_DATE = date(2025, 6, 15)


def _make_search_response(video_ids: list[str]) -> dict:
    return {
        "items": [{"id": {"videoId": vid}} for vid in video_ids],
    }


def _make_videos_response(video_ids: list[str]) -> dict:
    items = []
    for vid in video_ids:
        items.append({
            "id": vid,
            "snippet": {
                "title": f"Video {vid}",
                "description": "A keyword result.",
                "channelId": "UC_SOME",
                "publishedAt": "2025-06-15T00:00:00Z",
                "tags": ["streaming"],
            },
            "contentDetails": {"duration": "PT15M"},
            "statistics": {
                "viewCount": "5000",
                "likeCount": "200",
                "commentCount": "30",
            },
        })
    return {"items": items}


# ──────────────────────────────────────────────
# Tests — search_videos_by_keyword
# ──────────────────────────────────────────────

@patch("jobs.ingestion.fetch_keyword_metadata._api_get")
def test_search_returns_video_ids(mock_api_get: MagicMock) -> None:
    mock_api_get.return_value = _make_search_response(["k1", "k2"])

    ids = search_videos_by_keyword(FAKE_API_KEY, TEST_KEYWORD, max_results=5)

    assert ids == ["k1", "k2"]
    mock_api_get.assert_called_once()


@patch("jobs.ingestion.fetch_keyword_metadata._api_get")
def test_search_respects_max_results(mock_api_get: MagicMock) -> None:
    mock_api_get.return_value = _make_search_response(
        [f"k{i}" for i in range(10)]
    )

    ids = search_videos_by_keyword(FAKE_API_KEY, TEST_KEYWORD, max_results=3)

    assert len(ids) == 3


# ──────────────────────────────────────────────
# Tests — fetch_video_metadata
# ──────────────────────────────────────────────

@patch("jobs.ingestion.fetch_keyword_metadata._api_get")
def test_fetch_video_metadata(mock_api_get: MagicMock) -> None:
    mock_api_get.return_value = _make_videos_response(["k1", "k2"])

    items = fetch_video_metadata(FAKE_API_KEY, ["k1", "k2"])

    assert len(items) == 2
    assert items[1]["id"] == "k2"


# ──────────────────────────────────────────────
# Tests — save_video_json (idempotency)
# ──────────────────────────────────────────────

def test_save_creates_file(tmp_path: pytest.TempPathFactory) -> None:
    video = {"id": "kv1", "snippet": {"title": "Keyword Video"}}

    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        wrote = save_video_json(video, keyword=TEST_KEYWORD, dt=TEST_DATE)
        filepath = build_video_file_path("search", TEST_KEYWORD, "kv1", TEST_DATE)

    assert wrote is True
    assert os.path.exists(filepath)

    with open(filepath) as f:
        assert json.load(f)["id"] == "kv1"


def test_save_skips_existing(tmp_path: pytest.TempPathFactory) -> None:
    video = {"id": "kv1", "snippet": {"title": "Keyword Video"}}

    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        save_video_json(video, keyword=TEST_KEYWORD, dt=TEST_DATE)
        wrote = save_video_json(video, keyword=TEST_KEYWORD, dt=TEST_DATE)

    assert wrote is False


# ──────────────────────────────────────────────
# Tests — path structure for keyword source
# ──────────────────────────────────────────────

def test_keyword_path_structure(tmp_path: pytest.TempPathFactory) -> None:
    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        path = build_video_file_path("search", "rag production system", "vid1", TEST_DATE)

    assert "source=search" in path
    assert "dt=2025-06-15" in path
    assert "keyword=rag_production_system" in path
    assert path.endswith("video_vid1.json")


# ──────────────────────────────────────────────
# Tests — ingest_keyword end-to-end (mocked API)
# ──────────────────────────────────────────────

@patch("jobs.ingestion.fetch_keyword_metadata._api_get")
def test_ingest_keyword_end_to_end(mock_api_get: MagicMock, tmp_path: pytest.TempPathFactory) -> None:
    mock_api_get.side_effect = [
        _make_search_response(["k1", "k2", "k3"]),
        _make_videos_response(["k1", "k2", "k3"]),
    ]

    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        result = ingest_keyword(
            api_key=FAKE_API_KEY,
            keyword=TEST_KEYWORD,
            max_results=5,
            dt=TEST_DATE,
        )

    assert result["fetched"] == 3
    assert result["written"] == 3
    assert result["skipped"] == 0


@patch("jobs.ingestion.fetch_keyword_metadata._api_get")
def test_ingest_keyword_idempotent(mock_api_get: MagicMock, tmp_path: pytest.TempPathFactory) -> None:
    search_resp = _make_search_response(["k1"])
    videos_resp = _make_videos_response(["k1"])

    with patch("utils.path_builder.DATA_ROOT", str(tmp_path)):
        mock_api_get.side_effect = [search_resp, videos_resp]
        first = ingest_keyword(FAKE_API_KEY, TEST_KEYWORD, 5, TEST_DATE)

        mock_api_get.side_effect = [search_resp, videos_resp]
        second = ingest_keyword(FAKE_API_KEY, TEST_KEYWORD, 5, TEST_DATE)

    assert first["written"] == 1
    assert second["written"] == 0
    assert second["skipped"] == 1


# ──────────────────────────────────────────────
# Tests — error handling
# ──────────────────────────────────────────────

@patch("jobs.ingestion.fetch_keyword_metadata._api_get")
def test_quota_error_raises(mock_api_get: MagicMock) -> None:
    mock_api_get.side_effect = QuotaExceededError("quota")

    with pytest.raises(QuotaExceededError):
        search_videos_by_keyword(FAKE_API_KEY, TEST_KEYWORD)
