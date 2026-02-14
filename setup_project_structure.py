import os
from pathlib import Path

BASE_DIR = Path("")

# Set to True if you want to overwrite existing files
OVERWRITE_FILES = False


DIRECTORIES = [
    "configs",
    "dags",
    "jobs/ingestion",
    "jobs/transformations",
    "jobs/enrichment/prompt_templates",
    "jobs/scoring",
    "jobs/quality",
    "schemas",
    "utils",
    "data",
    "tests",
    "docker",
]

FILES = {
    "README.md": "# YouTube AI Content Intelligence Platform\n",
    "SUMMARY.md": "# System Summary\n",
    "requirements.txt": "",
    "configs/channels.yaml": "",
    "configs/discovery_keywords.yaml": "",
    "configs/metrics.yaml": "",
    "configs/interest_profile.yaml": "",
    "configs/scoring_versions.yaml": "",
    "configs/current_active_scoring.yaml": "",
    "dags/youtube_metadata_pipeline.py": "",
    "dags/youtube_transcript_pipeline.py": "",
    "dags/youtube_re_enrichment_pipeline.py": "",
    "jobs/ingestion/fetch_channel_metadata.py": "",
    "jobs/ingestion/fetch_keyword_metadata.py": "",
    "jobs/ingestion/fetch_transcripts.py": "",
    "jobs/transformations/bronze_to_silver_metadata.py": "",
    "jobs/transformations/bronze_to_silver_transcripts.py": "",
    "jobs/transformations/merge_metadata_transcripts.py": "",
    "jobs/enrichment/metadata_classifier.py": "",
    "jobs/enrichment/transcript_classifier.py": "",
    "jobs/enrichment/llm_client.py": "",
    "jobs/enrichment/prompt_templates/metadata_prompt.txt": "",
    "jobs/enrichment/prompt_templates/transcript_prompt.txt": "",
    "jobs/scoring/scoring_engine.py": "",
    "jobs/scoring/ranking.py": "",
    "jobs/scoring/scoring_utils.py": "",
    "jobs/quality/metadata_dq_checks.py": "",
    "jobs/quality/transcript_dq_checks.py": "",
    "jobs/quality/scoring_dq_checks.py": "",
    "schemas/bronze_metadata_schema.json": "{}",
    "schemas/silver_metadata_schema.json": "{}",
    "schemas/silver_transcript_schema.json": "{}",
    "schemas/enrichment_schema.json": "{}",
    "schemas/gold_schema.json": "{}",
    "utils/spark_session.py": "",
    "utils/s3_utils.py": "",
    "utils/path_builder.py": "",
    "utils/logging_utils.py": "",
    "utils/config_loader.py": "",
    "tests/test_scoring_engine.py": "",
    "tests/test_metric_ranges.py": "",
    "tests/test_llm_response_validation.py": "",
    "tests/test_schema_validation.py": "",
    "docker/Dockerfile.spark": "",
    "docker/Dockerfile.airflow": "",
    "docker/docker-compose.yml": "",
}


def create_directories():
    for directory in DIRECTORIES:
        path = BASE_DIR / directory
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {path}")


def create_files():
    for file_path, content in FILES.items():
        path = BASE_DIR / file_path

        if path.exists() and not OVERWRITE_FILES:
            print(f"Skipped existing file: {path}")
            continue

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Created file: {path}")


def create_gitignore():
    gitignore_path = BASE_DIR / ".gitignore"

    content = """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.env

# Data
data/
*.parquet

# Spark
metastore_db/
spark-warehouse/

# Airflow
airflow.db
logs/

# IDE
.vscode/
.idea/
"""

    if not gitignore_path.exists() or OVERWRITE_FILES:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created .gitignore at: {gitignore_path}")
    else:
        print(".gitignore already exists, skipping.")


def main():
    print("Setting up YouTube AI Intelligence project structure...\n")
    BASE_DIR.mkdir(exist_ok=True)
    create_directories()
    create_files()
    create_gitignore()
    print("\nProject structure created successfully.")


if __name__ == "__main__":
    main()
