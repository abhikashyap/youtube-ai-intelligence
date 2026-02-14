# YouTube AI Content Intelligence Platform
# YouTube AI Content Intelligence Platform (Pipeline 1 – Metadata)

## Overview

This project is a production-style AI data platform designed to extract high-signal technical content from YouTube using a medallion architecture, PySpark transformations, Airflow orchestration, and LLM-based enrichment.

Pipeline 1 focuses only on metadata-based intelligence. It ingests video metadata from curated channels and discovery keywords, processes it through a lakehouse architecture, classifies it using a local LLM, and produces ranked outputs.

This system is built locally using PySpark and Airflow, with a design ready for migration to S3 and AWS Glue.

---

## Architecture (Pipeline 1 – Metadata Only)

YouTube API  
→ Bronze (Raw Metadata JSON)  
→ Silver (Structured Parquet)  
→ LLM Metadata Classification  
→ Gold (Ranked & Scored Dataset)

---

## Tech Stack

- Python
- PySpark (local mode)
- Apache Airflow
- Local filesystem (S3-ready structure)
- Parquet (Snappy)
- Ollama (Local LLM)
- YAML-based config-driven scoring

---

## Data Architecture (Medallion Design)

### Bronze Layer (Immutable Raw)

Stores complete YouTube API responses.

# YouTube AI Content Intelligence Platform (Pipeline 1 – Metadata)

## Overview

This project is a production-style AI data platform designed to extract high-signal technical content from YouTube using a medallion architecture, PySpark transformations, Airflow orchestration, and LLM-based enrichment.

Pipeline 1 focuses only on metadata-based intelligence. It ingests video metadata from curated channels and discovery keywords, processes it through a lakehouse architecture, classifies it using a local LLM, and produces ranked outputs.

This system is built locally using PySpark and Airflow, with a design ready for migration to S3 and AWS Glue.

---

## Architecture (Pipeline 1 – Metadata Only)

YouTube API  
→ Bronze (Raw Metadata JSON)  
→ Silver (Structured Parquet)  
→ LLM Metadata Classification  
→ Gold (Ranked & Scored Dataset)

---

## Tech Stack

- Python
- PySpark (local mode)
- Apache Airflow
- Local filesystem (S3-ready structure)
- Parquet (Snappy)
- Ollama (Local LLM)
- YAML-based config-driven scoring

---

## Data Architecture (Medallion Design)

### Bronze Layer (Immutable Raw)

Stores complete YouTube API responses.


Characteristics:
- Append-only
- No transformation
- Full JSON payload stored
- Idempotent ingestion

---

### Silver Layer (Structured Metadata)

Normalized Parquet dataset generated via PySpark.

Schema (simplified):

- video_id
- channel_id
- channel_name
- title
- description
- tags
- duration_seconds
- view_count
- like_count
- comment_count
- ingestion_source
- ingestion_dt
- snapshot_dt

Partitioned by snapshot_dt.

Deduplicated on video_id.

---

### Silver Enriched (Metadata-Based LLM Classification)

LLM analyzes only metadata (title, description, tags, engagement).

Metrics (0–10 scale):

- concept_depth_score
- practical_score
- architecture_score
- implementation_score
- production_readiness_score
- tradeoff_discussion_score
- hype_score
- seniority_level
- topic_clusters
- llm_summary
- confidence

Versioned by model_version.

---

### Gold Layer (Ranked Intelligence)

Final business-ready dataset.

- video_id
- final_score
- ranking
- primary_topic
- metric_breakdown
- recommendation_reason
- is_recommended
- scoring_version
- computed_dt

Gold datasets are versioned.

---

## Airflow DAG (Metadata Pipeline)

DAG: `youtube_metadata_pipeline`

Tasks:

1. ingest_channel_metadata
2. ingest_keyword_metadata
3. bronze_to_silver_metadata
4. metadata_llm_classification
5. scoring_engine
6. data_quality_checks

Schedule: Daily

Design Principles:
- Idempotent
- Modular
- Domain-separated
- Version-aware

---

## Scoring Engine

Scoring is configuration-driven.

Example config:

```yaml
metric_weights:
  concept_depth_score: 1.2
  practical_score: 1.5
  architecture_score: 1.3
  implementation_score: 1.4
  hype_score: -2.0

topic_weights:
  streaming: 1.5
  llm_systems: 1.4
  frontend: 0.2
  startup: -1.5
