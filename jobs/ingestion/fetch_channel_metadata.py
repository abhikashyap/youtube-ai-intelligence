"""
Channel-based metadata ingestion for the YouTube AI Intelligence platform.

Fetches the latest videos from configured YouTube channels via the
YouTube Data API v3, retrieves full metadata for each video, and persists
the raw JSON response into the bronze layer.

Entry point: ``run_channel_ingestion()``
"""
from __future__ import annotations

import json
import os
import time
from datetime import date
from typing import Any

import requests

from utils.config_loader import get_youtube_api_key, load_channels_config
from utils.logging_utils import get_logger
from utils.path_builder import build_video_file_path, ensure_directory

logger = get_logger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


# ──────────────────────────────────────────────
# YouTube API helpers
# ──────────────────────────────────────────────

def _api_get(url: str, params: dict[str, Any], retries: int = MAX_RETRIES) -> dict[str, Any]:
    """Execute a GET request with retries and back-off.

    Raises after *retries* transient failures.  Quota errors (403) are
    surfaced immediately without retry.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)

            if resp.status_code == 403:
                error_body = resp.json()
                logger.error("API quota/permission error: %s", error_body)
                raise QuotaExceededError(
                    f"YouTube API returned 403: {error_body}"
                )

            resp.raise_for_status()
            return resp.json()

        except QuotaExceededError:
            raise
        except requests.RequestException as exc:
            logger.warning(
                "Transient API error (attempt %d/%d): %s", attempt, retries, exc
            )
            if attempt == retries:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    # Unreachable, but keeps mypy happy.
    raise RuntimeError("Exhausted retries")


class QuotaExceededError(Exception):
    """Raised when the YouTube API returns a 403 quota error."""


# ──────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────

def fetch_video_ids_for_channel(
    api_key: str,
    channel_id: str,
    max_results: int = 30,
) -> list[str]:
    """Return up to *max_results* recent video IDs for a channel.

    Uses the ``search.list`` endpoint ordered by date.
    """
    params: dict[str, Any] = {
        "key": api_key,
        "channelId": channel_id,
        "part": "id",
        "order": "date",
        "type": "video",
        "maxResults": min(max_results, 50),  # API cap per page
    }

    video_ids: list[str] = []
    page_token: str | None = None

    while len(video_ids) < max_results:
        if page_token:
            params["pageToken"] = page_token

        data = _api_get(YOUTUBE_SEARCH_URL, params)
        for item in data.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if vid:
                video_ids.append(vid)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return video_ids[:max_results]


def fetch_video_metadata(api_key: str, video_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch full metadata for a batch of video IDs via ``videos.list``.

    The API accepts up to 50 IDs per call, so we batch accordingly.
    """
    all_items: list[dict[str, Any]] = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        params = {
            "key": api_key,
            "id": ",".join(batch),
            "part": "snippet,contentDetails,statistics",
        }
        data = _api_get(YOUTUBE_VIDEOS_URL, params)
        all_items.extend(data.get("items", []))

    return all_items


def save_video_json(
    video: dict[str, Any],
    source: str,
    identifier: str,
    dt: date,
) -> bool:
    """Persist a single video's raw JSON to the bronze layer.

    Returns ``True`` if a new file was written, ``False`` if skipped
    (idempotency — file already exists).
    """
    video_id = video["id"]
    filepath = build_video_file_path(source, identifier, video_id, dt)

    if os.path.exists(filepath):
        return False

    ensure_directory(os.path.dirname(filepath))

    with open(filepath, "w") as fh:
        json.dump(video, fh, indent=2)

    return True


# ──────────────────────────────────────────────
# Orchestration
# ──────────────────────────────────────────────

def ingest_channel(
    api_key: str,
    channel_id: str,
    channel_name: str,
    max_results: int,
    dt: date,
) -> dict[str, int]:
    """Run end-to-end ingestion for a single channel.

    Returns a summary dict with counts.
    """
    logger.info(
        "Starting ingestion for channel %s (%s), max_results=%d",
        channel_name, channel_id, max_results,
    )

    video_ids = fetch_video_ids_for_channel(api_key, channel_id, max_results)
    logger.info("Fetched %d video IDs for channel %s", len(video_ids), channel_name)

    if not video_ids:
        return {"fetched": 0, "written": 0, "skipped": 0}

    videos = fetch_video_metadata(api_key, video_ids)
    logger.info("Retrieved metadata for %d videos", len(videos))

    written = 0
    skipped = 0
    for video in videos:
        if save_video_json(video, source="channel", identifier=channel_id, dt=dt):
            written += 1
        else:
            skipped += 1

    logger.info(
        "Channel %s done — fetched=%d, written=%d, skipped=%d",
        channel_name, len(videos), written, skipped,
    )
    return {"fetched": len(videos), "written": written, "skipped": skipped}


def run_channel_ingestion(dt: date | None = None, **kwargs: Any) -> None:
    """Airflow-callable entry point.

    Iterates over all channels defined in ``channels.yaml`` and ingests
    metadata for each.  A single channel failure does not abort the run.
    """
    if dt is None:
        dt = date.today()

    logger.info("=== Channel metadata ingestion started (dt=%s) ===", dt)

    api_key = get_youtube_api_key()
    channels = load_channels_config()

    total = {"fetched": 0, "written": 0, "skipped": 0, "errors": 0}

    for ch in channels:
        try:
            result = ingest_channel(
                api_key=api_key,
                channel_id=ch["id"],
                channel_name=ch["name"],
                max_results=ch.get("max_results", 30),
                dt=dt,
            )
            total["fetched"] += result["fetched"]
            total["written"] += result["written"]
            total["skipped"] += result["skipped"]
        except QuotaExceededError:
            logger.error("Quota exceeded — aborting remaining channels.")
            total["errors"] += 1
            break
        except Exception:
            logger.exception("Failed to ingest channel %s", ch.get("name", ch["id"]))
            total["errors"] += 1

    logger.info(
        "=== Channel ingestion complete — fetched=%d, written=%d, skipped=%d, errors=%d ===",
        total["fetched"], total["written"], total["skipped"], total["errors"],
    )
