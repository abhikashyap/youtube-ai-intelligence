# Architecture

## Repository Structure

```
youtube-ai-intelligence/
├── configs/                    # YAML configuration files
│   ├── channels.yaml           # YouTube channels to ingest
│   ├── discovery_keywords.yaml # Search keywords for discovery
│   ├── interest_profile.yaml   # User interest profiles (planned)
│   ├── metrics.yaml            # Metric definitions (planned)
│   ├── scoring_versions.yaml   # Scoring version mappings (planned)
│   └── current_active_scoring.yaml  # Active scoring config (planned)
│
├── dags/                       # Airflow DAG definitions
│   ├── youtube_metadata_pipeline.py       # Main metadata pipeline
│   ├── youtube_transcript_pipeline.py     # Transcript pipeline (stub)
│   └── youtube_re_enrichment_pipeline.py  # Re-scoring pipeline (stub)
│
├── jobs/                       # Business logic
│   ├── ingestion/              # Data ingestion from YouTube API
│   │   ├── fetch_channel_metadata.py      # Fetch videos from channels
│   │   ├── fetch_keyword_metadata.py      # Fetch videos by keyword search
│   │   ├── compact_bronze_metadata.py     # Merge JSON files -> JSONL
│   │   └── fetch_transcripts.py           # Transcript extraction (stub)
│   │
│   ├── transformations/        # Data transformation (PySpark)
│   │   ├── bronze_to_silver_metadata.py   # JSON -> Parquet (stub)
│   │   ├── bronze_to_silver_transcripts.py
│   │   └── merge_metadata_transcripts.py
│   │
│   ├── enrichment/             # LLM-based classification
│   │   ├── llm_client.py                  # Ollama API client (stub)
│   │   ├── metadata_classifier.py         # Metadata LLM scoring (stub)
│   │   └── transcript_classifier.py       # Transcript scoring (stub)
│   │
│   ├── scoring/                # Config-driven scoring & ranking
│   │   ├── scoring_engine.py              # Main scoring logic (stub)
│   │   ├── ranking.py
│   │   └── scoring_utils.py
│   │
│   └── quality/                # Data quality validation
│       ├── metadata_dq_checks.py
│       ├── transcript_dq_checks.py
│       └── scoring_dq_checks.py
│
├── schemas/                    # Data schema definitions
│   └── silver_metadata.py      # Silver layer StructType (stub)
│
├── utils/                      # Shared utilities
│   ├── config_loader.py        # YAML config & env var loading
│   ├── path_builder.py         # All file path construction
│   ├── logging_utils.py        # Centralized logging setup
│   ├── spark_session.py        # Spark session factory (stub)
│   └── s3_utils.py             # S3 operations (stub)
│
├── docker/                     # Container configuration
│   ├── docker-compose.yml      # Multi-service orchestration
│   ├── Dockerfile.airflow      # Airflow image
│   └── Dockerfile.spark        # AWS Glue/Spark + Jupyter image
│
├── tests/                      # Test suite (pytest)
├── prds/                       # Product requirement documents
├── notebooks/                  # Jupyter notebooks (dev/exploration)
├── data/                       # Local data lake (gitignored)
├── pyproject.toml              # Python project & dependencies
└── .env                        # Environment variables (API keys)
```

## Medallion Data Architecture

### Bronze Layer (Raw, Immutable)

Stores complete YouTube API responses exactly as received.

- **Format**: Individual JSON files per video, compacted into JSONL
- **Characteristics**: Append-only, no transformation, full payload
- **Partitioning**: `source={channel|search}/dt={YYYY-MM-DD}/{identifier}/`

```
data/bronze/metadata/
├── source=channel/
│   └── dt=2026-02-14/
│       ├── UC_x5XG1OV2P6uZZ5FSM9Ttw/
│       │   ├── _compacted.jsonl
│       │   └── _compaction_manifest.json
│       └── UCVHFbqXqoYvEWM1Ddxl0QDg/
│           └── _compacted.jsonl
└── source=search/
    └── dt=2026-02-14/
        └── keyword=spark_structured_streaming/
            └── _compacted.jsonl
```

### Silver Layer (Structured, Deduplicated)

Normalized Parquet dataset generated via PySpark.

| Field            | Type    | Notes              |
|------------------|---------|--------------------|
| video_id         | string  | Primary key        |
| channel_id       | string  |                    |
| channel_name     | string  |                    |
| title            | string  |                    |
| description      | string  |                    |
| tags             | array   |                    |
| duration_seconds | integer |                    |
| view_count       | long    |                    |
| like_count       | long    |                    |
| comment_count    | long    |                    |
| ingestion_source | string  | "channel" or "search" |
| ingestion_dt     | date    |                    |
| snapshot_dt      | date    | Partition key      |

- **Format**: Parquet with Snappy compression
- **Deduplicated** on `video_id`
- **Partitioned** by `snapshot_dt`

### Silver Enriched (LLM Classification)

Silver dataset augmented with LLM-generated scores.

| Metric                      | Scale | Description                |
|-----------------------------|-------|----------------------------|
| concept_depth_score         | 0-10  | Technical depth            |
| practical_score             | 0-10  | Hands-on applicability     |
| architecture_score          | 0-10  | Architectural insights     |
| implementation_score        | 0-10  | Implementation detail      |
| production_readiness_score  | 0-10  | Production-ready content   |
| tradeoff_discussion_score   | 0-10  | Tradeoff analysis          |
| hype_score                  | 0-10  | Marketing hype (penalized) |

Additional fields: `seniority_level`, `topic_clusters`, `llm_summary`, `confidence`

Versioned by `enrichment_version`, `model_version`, `prompt_version`.

### Gold Layer (Ranked Intelligence)

Final business-ready dataset with computed scores and rankings.

| Field                 | Description                        |
|-----------------------|------------------------------------|
| video_id              | Primary key                        |
| final_score           | Computed weighted score            |
| ranking               | Position after sorting by score    |
| primary_topic         | Highest-weight topic cluster       |
| metric_breakdown      | Map of individual weight contributions |
| recommendation_reason | Human-readable explanation         |
| is_recommended        | Boolean (score > threshold)        |
| scoring_version       | Reference to scoring config used   |
| computed_dt           | Date of computation                |

## Scoring Formula

```
final_score = sum(metric_score * metric_weight)
            + sum(topic_adjustments)
            + seniority_adjustment
```

Weights are defined in YAML config files, enabling A/B testing without code changes.

Example:
```yaml
metric_weights:
  concept_depth_score: 1.2
  practical_score: 1.5
  architecture_score: 1.3
  implementation_score: 1.4
  hype_score: -2.0        # negative = penalize hype

topic_weights:
  streaming: 1.5
  llm_systems: 1.4
  data_engineering: 1.2
  frontend: 0.2
  startup: -1.5
```
