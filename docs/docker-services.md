# Docker Services

All services are defined in `docker/docker-compose.yml`.

## Services Overview

### PostgreSQL (Airflow metadata DB)

- **Image**: `postgres:17-alpine`
- **Port**: 5432
- **Credentials**: airflow / airflow
- **Purpose**: Stores Airflow's internal metadata (DAG runs, task instances, connections, etc.)
- **Volume**: `postgres-data` (persistent)

### Airflow Init

- **One-shot container** (runs once and exits)
- Runs `airflow db migrate` to create/update the database schema
- Creates the admin user (admin / admin)
- All other Airflow services wait for this to complete

### Airflow API Server (UI + REST API)

- **Port**: 8080
- **Purpose**: Serves the Airflow web UI and REST API
- **Healthcheck**: `GET /api/v2/monitor/health`
- In Airflow 3.x, this replaces the old `webserver` command

### Airflow Scheduler

- **Purpose**: Monitors DAGs and triggers task execution
- With LocalExecutor, tasks run as subprocesses of the scheduler
- **Hostname**: Set to `airflow-scheduler` so the API server can fetch task logs from it via port 8793

### Airflow DAG Processor

- **Purpose**: Parses DAG files independently from the scheduler
- Detects new/modified DAGs and updates the metadata DB

### pgAdmin

- **Image**: `dpage/pgadmin4:latest`
- **Port**: 5050
- **Credentials**: admin@example.com / admin
- **Purpose**: Web-based PostgreSQL browser for inspecting Airflow's metadata DB

### Glue / Spark (Development Container)

- **Image**: Built from `docker/Dockerfile.spark` (base: `amazon/aws-glue-libs:5`)
- **Ports**:
  - 8888: Jupyter Notebook
  - 4040: Spark UI (active during Spark jobs)
  - 18080: Spark History Server
- **Purpose**: Local PySpark development environment with Jupyter
- **Volumes**: Mounts the entire project workspace + AWS credentials (read-only)

## Shared Configuration

All Airflow containers inherit from the `x-airflow-common` YAML anchor which sets:

| Environment Variable                          | Value                                          |
|-----------------------------------------------|-------------------------------------------------|
| `AIRFLOW__CORE__EXECUTOR`                     | LocalExecutor                                   |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`         | postgresql+psycopg2://airflow:airflow@postgres:5432/airflow |
| `AIRFLOW__CORE__LOAD_EXAMPLES`                | false                                           |
| `AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS`| true                                           |
| `AIRFLOW__CORE__EXECUTION_API_SERVER_URL`     | http://airflow-api-server:8080/execution/       |
| `AIRFLOW__API__SECRET_KEY`                    | Shared JWT signing key                          |
| `AIRFLOW__API_AUTH__JWT_SECRET`               | Shared JWT signing key                          |
| `PYTHONPATH`                                  | /opt/airflow                                    |
| `DATA_ROOT`                                   | /opt/airflow/data                               |

Shared volumes (bind mounts) for code hot-reload:
- `dags/`, `jobs/`, `utils/`, `configs/`, `schemas/`, `data/`

Shared named volume for task logs:
- `airflow-logs` -> `/opt/airflow/logs`

## Network

All services run on a custom bridge network `youtube-ai-net`, enabling DNS-based service discovery (containers reach each other by service name).

## Dockerfiles

### Dockerfile.airflow

```dockerfile
FROM apache/airflow:3.1.7-python3.12
# Installs: pyyaml, python-dotenv, requests
# Copies: dags/, jobs/, utils/, configs/, schemas/
```

### Dockerfile.spark

```dockerfile
FROM amazon/aws-glue-libs:5
# Installs: pyyaml, python-dotenv, requests, jupyter, notebook
# Copies: jobs/, utils/, configs/, schemas/
# Runs as: root (drops to hadoop via runuser for Jupyter)
```

## Common Operations

```bash
# Start everything
docker compose -f docker/docker-compose.yml up -d --build

# Restart only Airflow services
docker compose -f docker/docker-compose.yml up -d airflow-api-server airflow-scheduler airflow-dag-processor

# View scheduler logs
docker compose -f docker/docker-compose.yml logs -f airflow-scheduler

# Shell into Spark container
docker compose -f docker/docker-compose.yml exec glue bash

# Stop everything
docker compose -f docker/docker-compose.yml down

# Stop and remove volumes
docker compose -f docker/docker-compose.yml down -v
```
