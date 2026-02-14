# YouTube AI Content Intelligence Platform

## What This Project Does

This platform ingests YouTube video metadata from curated channels and keyword searches, processes it through a medallion data architecture (Bronze -> Silver -> Gold), enriches it using a local LLM (Ollama), and produces a ranked dataset of high-signal technical videos.

Stage 1 (current) focuses exclusively on metadata-based intelligence. Transcript extraction and deeper analysis are planned for Stage 2.

## Tech Stack

| Component       | Technology                         |
|-----------------|------------------------------------|
| Language        | Python 3.12+                       |
| Orchestration   | Apache Airflow 3.1.7               |
| Processing      | PySpark 4.1.1 (local mode)         |
| Storage         | Local filesystem (S3-ready)        |
| Data Formats    | JSON (bronze), Parquet/Snappy (silver/gold) |
| LLM             | Ollama (local)                     |
| Configuration   | YAML-based, config-driven scoring  |
| Containers      | Docker & Docker Compose            |
| Testing         | pytest                             |

## High-Level Data Flow

```
YouTube Data API v3
        |
        v
  +-----------+     +-----------+
  | Channel   |     | Keyword   |
  | Ingestion |     | Ingestion |
  +-----------+     +-----------+
        \               /
         v             v
    +---------------------+
    | Bronze Layer        |
    | (Raw JSON -> JSONL) |
    +---------------------+
              |
              v
    +---------------------+
    | Silver Layer        |  <-- PySpark transformation
    | (Structured Parquet)|
    +---------------------+
              |
              v
    +---------------------+
    | LLM Enrichment      |  <-- Ollama classification
    | (Silver Enriched)   |
    +---------------------+
              |
              v
    +---------------------+
    | Scoring Engine      |  <-- Config-driven weights
    | (Gold Layer)        |
    +---------------------+
              |
              v
    +---------------------+
    | Data Quality Checks |
    +---------------------+
```

## Current Implementation Status

| Component                  | Status       |
|----------------------------|--------------|
| Channel metadata ingestion | Implemented  |
| Keyword metadata ingestion | Implemented  |
| Bronze compaction          | Implemented  |
| Bronze -> Silver transform | Stub         |
| LLM classification        | Stub         |
| Scoring engine             | Stub         |
| Data quality checks        | Stub         |
| Transcript pipeline        | Stub (Phase 2) |

## Design Principles

- **Idempotent**: Every job is safe to re-run without creating duplicates
- **Modular**: Each pipeline stage is an independent, composable unit
- **Config-driven**: Scoring weights and thresholds live in YAML, not code
- **Version-aware**: Enrichment and scoring outputs track model/config versions
- **S3-ready**: All path construction is abstracted via `path_builder.py` for easy migration to S3/Glue
