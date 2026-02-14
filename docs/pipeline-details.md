# Pipeline Details

## Airflow DAGs

### youtube_metadata_pipeline (Main DAG)

**Schedule**: `@daily`

**Task dependency graph**:
```
[ingest_channel_metadata, ingest_keyword_metadata]
        |                           |
        +----------+  +------------+
                   |  |
                   v  v
            compact_bronze
                   |
                   v  (future tasks)
        bronze_to_silver_metadata
                   |
                   v
       metadata_llm_classification
                   |
                   v
            scoring_engine
                   |
                   v
         data_quality_checks
```

Currently only the first three tasks are wired. The remaining tasks will be added as their implementations are completed.

### youtube_transcript_pipeline (Phase 2)

Separate DAG for transcript extraction and processing. Not yet implemented.

### youtube_re_enrichment_pipeline (Phase 2)

Allows re-scoring with different config weights without re-running LLM classification. Not yet implemented.

---

## Implemented Jobs

### 1. Channel Metadata Ingestion

**File**: `jobs/ingestion/fetch_channel_metadata.py`
**Entry point**: `run_channel_ingestion()`

Fetches latest videos from each channel defined in `configs/channels.yaml`.

**How it works**:
1. Reads channel list from `configs/channels.yaml`
2. For each channel, calls YouTube `search.list` API to get recent video IDs
3. Calls `videos.list` API to fetch full metadata (snippet, contentDetails, statistics)
4. Saves each video as an individual JSON file in the bronze layer
5. Skips files that already exist (idempotent)

**API details**:
- Batches video IDs in groups of 50 (API limit)
- Retries transient errors with exponential backoff (max 3 retries)
- Fails immediately on 403 quota errors without retry
- A single channel failure does not abort the entire run

**Output path**: `data/bronze/metadata/source=channel/dt={date}/{channel_id}/video_{video_id}.json`

### 2. Keyword Metadata Ingestion

**File**: `jobs/ingestion/fetch_keyword_metadata.py`
**Entry point**: `run_keyword_ingestion()`

Same structure as channel ingestion, but uses keyword search instead of channel listing.

Keywords are defined in `configs/discovery_keywords.yaml`.

**Output path**: `data/bronze/metadata/source=search/dt={date}/keyword={keyword}/video_{video_id}.json`

### 3. Bronze Compaction

**File**: `jobs/ingestion/compact_bronze_metadata.py`
**Entry point**: `run_bronze_compaction()`

Merges individual `video_*.json` files into a single `_compacted.jsonl` per partition to reduce filesystem overhead.

**How it works**:
1. Lists all `video_*.json` files in a partition directory
2. Loads existing `_compacted.jsonl` to identify already-compacted video IDs
3. Appends only new records (incremental, deduplicates by video_id)
4. Writes a `_compaction_manifest.json` with operational metadata
5. Deletes original JSON files only when zero errors occurred

**Output files**:
- `_compacted.jsonl` - One JSON record per line
- `_compaction_manifest.json` - Metadata about the compaction run

---

## Configuration Files

### configs/channels.yaml

Defines YouTube channels to monitor:

```yaml
channels:
  - id: UC_x5XG1OV2P6uZZ5FSM9Ttw
    name: GoogleDevelopers
    max_results: 10

  - id: UCVHFbqXqoYvEWM1Ddxl0QDg
    name: AlexTheAnalyst
    max_results: 20

  - id: UC8butISFwT-Wl7EV0hUK0BQ
    name: freeCodeCamp
    max_results: 25
```

### configs/discovery_keywords.yaml

Defines search queries for video discovery:

```yaml
keywords:
  - keyword: "spark structured streaming"
    max_results: 20
  - keyword: "rag production system"
    max_results: 20
  - keyword: "data engineering best practices"
    max_results: 15
  - keyword: "airflow dags production"
    max_results: 15
```

---

## Utility Modules

### utils/config_loader.py

Loads YAML configs and environment variables.

| Function                | Returns                       |
|-------------------------|-------------------------------|
| `load_channels_config()`| List of channel dicts         |
| `load_keywords_config()`| List of keyword dicts         |
| `get_youtube_api_key()` | API key string (from `.env`)  |

### utils/path_builder.py

Centralizes all file path construction. Every storage operation goes through this module, making it straightforward to swap from local filesystem to S3.

| Function                         | Purpose                                    |
|----------------------------------|--------------------------------------------|
| `get_bronze_metadata_path()`     | Partition directory for bronze data        |
| `build_video_file_path()`        | Full path for a single video JSON          |
| `build_compacted_jsonl_path()`   | Path to `_compacted.jsonl`                 |
| `build_compaction_manifest_path()` | Path to `_compaction_manifest.json`      |
| `iter_compacted_bronze_records()`| Read all records from a partition          |
| `ensure_directory()`             | Create directory tree                      |

The data root is set via the `DATA_ROOT` environment variable (defaults to `{project}/data`).

### utils/logging_utils.py

Provides `get_logger(name)` for consistent log formatting across all modules.

Format: `%(asctime)s | %(name)s | %(levelname)s | %(message)s`

---

## Error Handling

- **Transient API errors**: Retried with exponential backoff (2s, 4s, 6s)
- **Quota exceeded (403)**: Immediate failure, remaining channels/keywords skipped
- **Individual channel/keyword failure**: Logged and skipped, does not abort the run
- **Compaction errors**: Original JSON files are preserved (not deleted) on any error
