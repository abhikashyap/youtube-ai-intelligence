"""
Airflow DAG for the YouTube metadata pipeline.

Schedule: daily
Task chain:
    [ingest_channel_metadata, ingest_keyword_metadata]
        >> compact_bronze
        >> bronze_to_silver_metadata
        >> metadata_llm_classification
        >> scoring_engine
        >> data_quality_checks
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from jobs.ingestion.compact_bronze_metadata import run_bronze_compaction
from jobs.ingestion.fetch_channel_metadata import run_channel_ingestion
from jobs.ingestion.fetch_keyword_metadata import run_keyword_ingestion

with DAG(
    dag_id="youtube_metadata_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 2, 14),
    catchup=False,
    tags=["youtube", "metadata"],
) as dag:

    t_ingest_channels = PythonOperator(
        task_id="ingest_channel_metadata",
        python_callable=run_channel_ingestion,
    )

    t_ingest_keywords = PythonOperator(
        task_id="ingest_keyword_metadata",
        python_callable=run_keyword_ingestion,
    )

    t_compact_bronze = PythonOperator(
        task_id="compact_bronze",
        python_callable=run_bronze_compaction,
    )

    # Wire dependencies: ingest first, then compact.
    # Future tasks (bronze_to_silver, enrichment, scoring) chain after compact.
    [t_ingest_channels, t_ingest_keywords] >> t_compact_bronze
