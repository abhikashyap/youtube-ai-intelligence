# PRD -- Stage 1

# YouTube AI Content Intelligence Platform (Metadata Pipeline)

------------------------------------------------------------------------

# 1. Executive Summary

Stage 1 delivers a production-grade data pipeline that ingests YouTube
metadata from curated channels and discovery keywords, processes it
using a medallion architecture (Bronze → Silver → Gold), enriches it
using a local LLM, and produces a ranked dataset of high-signal
technical videos.

This stage focuses exclusively on metadata-based intelligence.

It is designed to be:

-   Local-first
-   Spark-based
-   Airflow-orchestrated
-   Versioned
-   S3/Glue-ready

------------------------------------------------------------------------

# 2. Objectives

## Primary Objective

Build a reliable, versioned, and reproducible metadata intelligence
pipeline.

## Secondary Objectives

-   Demonstrate medallion architecture
-   Operationalize local LLM classification
-   Implement config-driven scoring
-   Ensure versioned enrichment and scoring
-   Maintain modular DAG architecture

------------------------------------------------------------------------

# 3. Scope

## In Scope

-   YouTube metadata ingestion (channels + keywords)
-   Bronze raw JSON storage
-   Silver structured Parquet transformation
-   Metadata-based LLM classification
-   Config-driven scoring engine
-   Gold ranked dataset
-   Airflow DAG orchestration
-   Data quality checks
-   Version control of enrichment & scoring

## Out of Scope (Stage 1)

-   Transcript extraction
-   Full-text LLM classification
-   Embeddings
-   UI/Django integration
-   User feedback loop
-   Channel quality scoring

------------------------------------------------------------------------

# 4. System Architecture (Stage 1)

    YouTube API
        ↓
    Bronze (raw metadata JSON)
        ↓
    Silver (structured metadata parquet)
        ↓
    LLM metadata classification
        ↓
    Scoring engine
        ↓
    Gold (ranked dataset)

Airflow orchestrates all stages.

------------------------------------------------------------------------

# 5. Repository Structure (Stage 1 Relevant Folders)

    youtube-ai-intelligence/
    │
    ├── configs/
    ├── dags/
    ├── jobs/
    │   ├── ingestion/
    │   ├── transformations/
    │   ├── enrichment/
    │   ├── scoring/
    │   └── quality/
    ├── schemas/
    ├── utils/
    └── tests/

------------------------------------------------------------------------

# 6. Functional Requirements

## 6.1 Metadata Ingestion

Fetch metadata from curated channels and keyword-based search.

Outputs raw JSON into Bronze layer.

Requirements: - Idempotent ingestion - Deduplicate by video_id - Log API
usage - Store full payload

------------------------------------------------------------------------

## 6.2 Bronze → Silver Transformation

Transform raw JSON into structured Parquet using PySpark.

Key Fields: - video_id - channel_id - channel_name - title -
description - tags - duration_seconds - view_count - like_count -
comment_count - ingestion_source - ingestion_dt - snapshot_dt

Requirements: - Deduplicate on video_id - Partition by snapshot_dt -
Enforce schema validation

------------------------------------------------------------------------

## 6.3 Metadata LLM Classification

Use local LLM (Ollama) to classify metadata.

Metrics (0--10 scale):

-   concept_depth_score
-   practical_score
-   architecture_score
-   implementation_score
-   production_readiness_score
-   tradeoff_discussion_score
-   hype_score

Additional Fields: - seniority_level - topic_clusters - llm_summary -
confidence

Requirements: - Deterministic output - JSON schema validation -
Versioned enrichment path

------------------------------------------------------------------------

## 6.4 Scoring Engine

Compute final ranking using configurable weights.

Formula:

    final_score =
      Σ(metric_score × metric_weight)
      + Σ(topic_adjustments)

Outputs versioned Gold dataset.

------------------------------------------------------------------------

# 7. Airflow Design

DAG: youtube_metadata_pipeline

Tasks:

1.  ingest_channel_metadata\
2.  ingest_keyword_metadata\
3.  bronze_to_silver_metadata\
4.  metadata_llm_classification\
5.  scoring_engine\
6.  metadata_data_quality

Dependency:

    [1,2] → 3 → 4 → 5 → 6

------------------------------------------------------------------------

# 8. Non-Functional Requirements

Performance: - Handle 1,000+ videos/day - Batch LLM classification

Scalability: - S3-ready storage abstraction - Glue-compatible Spark jobs

Reliability: - Idempotent jobs - Versioned outputs - No destructive
overwrites

------------------------------------------------------------------------

# 9. Versioning Strategy

Each enrichment must store: - enrichment_version - model_version -
prompt_version - scoring_version

Each gold dataset must store: - scoring_version - computed_dt

------------------------------------------------------------------------

# 10. Acceptance Criteria

Stage 1 is complete when:

-   Daily ingestion succeeds
-   Silver dataset is valid
-   LLM classification produces valid metrics
-   Gold ranking generated
-   Data quality checks pass
-   Re-scoring works without reclassification
