# Roadmap

## Phase 1 - Metadata Intelligence (Current)

Fast, lightweight pipeline using metadata only.

| Task                              | Status      |
|-----------------------------------|-------------|
| YouTube channel ingestion         | Done        |
| YouTube keyword ingestion         | Done        |
| Bronze compaction (JSON -> JSONL) | Done        |
| Airflow DAG orchestration         | Done        |
| Unit tests for ingestion          | Done        |
| Bronze -> Silver (PySpark)        | Not started |
| LLM metadata classification      | Not started |
| Config-driven scoring engine      | Not started |
| Gold ranked dataset               | Not started |
| Data quality checks               | Not started |

### Acceptance Criteria (Stage 1 Complete)

- Daily ingestion succeeds
- Silver dataset passes schema validation
- LLM classification produces valid 0-10 metrics
- Gold ranking generated from scored dataset
- Data quality checks pass
- Re-scoring works without re-running LLM classification

## Phase 2 - Transcript Extraction

A separate, independent Airflow DAG.

- Extract video transcripts via YouTube transcript API
- Bronze -> Silver transcript transformation
- LLM classification on full transcript text
- Merge metadata + transcript silver datasets
- Combined scoring using both metadata and transcript signals

## Phase 3 - Advanced Enrichment

- Embeddings generation for semantic search
- Vector database integration
- Similarity-based video clustering

## Phase 4 - Frontend & Feedback Loop

- Django web UI for browsing ranked videos
- User rating system for video quality
- Active learning pipeline (user feedback improves scoring)
- Channel quality scoring based on aggregate metrics

## AWS Migration Path

The platform is designed for straightforward migration to AWS:

| Local Component | AWS Equivalent        |
|-----------------|-----------------------|
| Local filesystem| Amazon S3             |
| PySpark (local) | AWS Glue              |
| Airflow (Docker)| Amazon MWAA           |
| Ollama (local)  | Amazon Bedrock / SageMaker |

The `utils/path_builder.py` module abstracts storage paths, and `utils/s3_utils.py` is stubbed for future S3 operations.
