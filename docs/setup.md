# Local Development Setup

## Prerequisites

- Docker & Docker Compose
- YouTube Data API key (from [Google Cloud Console](https://console.cloud.google.com/apis/credentials))
- Python 3.12+ (optional, for running tests outside Docker)

## 1. Environment Variables

Create a `.env` file in the project root:

```bash
YOUTUBE_API_KEY=your_youtube_api_key_here
```

## 2. Start All Services

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

This starts the following services:

| Service              | URL                          | Credentials            |
|----------------------|------------------------------|------------------------|
| Airflow UI           | http://localhost:8080         | admin / admin          |
| Jupyter Notebook     | http://localhost:8888         | No auth (local dev)    |
| Spark UI             | http://localhost:4040         | (when Spark is active) |
| pgAdmin              | http://localhost:5050         | admin@example.com / admin |
| PostgreSQL           | localhost:5432                | airflow / airflow      |

## 3. Trigger the Pipeline

From the Airflow UI:
1. Go to http://localhost:8080
2. Find `youtube_metadata_pipeline` in the DAG list
3. Click the play button to trigger a manual run

Or via CLI:
```bash
docker compose -f docker/docker-compose.yml exec airflow-api-server \
  airflow dags trigger youtube_metadata_pipeline
```

## 4. View Results

After a successful run, ingested data appears in:
```
data/bronze/metadata/
├── source=channel/dt=YYYY-MM-DD/{channel_id}/_compacted.jsonl
└── source=search/dt=YYYY-MM-DD/keyword={keyword}/_compacted.jsonl
```

Use the Jupyter notebook at http://localhost:8888 to explore data with PySpark.

## 5. Running Tests

```bash
# Install dependencies
pip install -e ".[dev]"
# or with uv:
uv sync

# Run tests
pytest tests/
```

## Service Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PostgreSQL  │<────│  Airflow Init    │     │  pgAdmin        │
│  (metadata)  │     │  (DB migration)  │     │  (DB browser)   │
│  :5432       │     └──────────────────┘     │  :5050          │
└──────┬───────┘              │               └─────────────────┘
       │              ┌───────┴────────┐
       │              │                │
       ▼              ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│ API Server   │ │ Scheduler    │ │ DAG Processor    │
│ (UI + REST)  │ │ (task exec)  │ │ (DAG parsing)    │
│ :8080        │ │              │ │                  │
└──────────────┘ └──────────────┘ └──────────────────┘

┌──────────────────────────────────────────────┐
│  Glue / Spark Container                      │
│  Jupyter Notebook :8888  |  Spark UI :4040   │
└──────────────────────────────────────────────┘
```

All services run on a shared Docker bridge network (`youtube-ai-net`).

## Stopping Services

```bash
docker compose -f docker/docker-compose.yml down
```

To also remove persistent volumes (database, logs):
```bash
docker compose -f docker/docker-compose.yml down -v
```

## Rebuilding After Code Changes

Airflow containers use bind mounts for `dags/`, `jobs/`, `utils/`, `configs/`, and `schemas/`, so code changes are reflected immediately without rebuilding.

For dependency changes (new pip packages), rebuild the images:
```bash
docker compose -f docker/docker-compose.yml up -d --build
```
