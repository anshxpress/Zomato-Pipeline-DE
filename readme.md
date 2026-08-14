# Zomato - End-to-End Data Engineering Pipeline

An end-to-end Data Engineering project that builds a cloud-based ELT pipeline for Zomato restaurant and order data using AWS, Snowflake, dbt, and Airflow.

## Architecture

```mermaid
graph TD
    A[CSV Data] --> B[AWS S3]
    B --> C[Snowflake <br/> Bronze]
    C --> D[dbt <br/> Silver → Gold]
    D --> E[Data Marts]
    E --> F[Analytics / AI]
```

Apache Airflow orchestrates the pipeline from ingestion through transformation and validation.

## Tech Stack

- **Languages:** Python, SQL
- **Cloud:** AWS S3
- **Data Warehouse:** Snowflake
- **Transformation:** dbt
- **Orchestration:** Apache Airflow
- **Processing:** Pandas
- **AI:** OpenAI API
- **Application:** Streamlit
- **Infrastructure:** Docker

## Key Features

- Built an end-to-end ELT pipeline from raw CSV data to analytics-ready datasets.
- Implemented Bronze → Silver → Gold data architecture.
- Developed dbt models with incremental processing, dimensional modeling, and SCD Type 2 snapshots.
- Added dbt data quality tests including uniqueness, null, relationship, and accepted-value checks.
- Automated pipeline execution using Apache Airflow.
- Created analytical fact, dimension, and business-mart tables in Snowflake.
- Added an optional AI layer for review enrichment, RAG, and natural-language SQL.

## Pipeline Flow

```text
Source Data
    ↓
S3 Raw Layer
    ↓
Snowflake Raw Tables
    ↓
dbt Transformations
    ↓
Data Quality Tests
    ↓
Gold Data Marts
    ↓
Analytics / AI
```

## Project Structure

```text
├── airflow/       # Airflow DAGs and Docker setup
├── zomato/        # dbt models and transformations
├── snowflake/     # Snowflake setup and SQL scripts
├── ai/            # AI enrichment and analytics
├── docs/          # Architecture documentation
└── README.md
```

## Setup

### Prerequisites

- Python 3.x
- Docker
- AWS account
- Snowflake account
- dbt
- OpenAI API key (AI features only)

### Start Airflow

1. Fill your credentials in `airflow/.env.example` and rename it to `airflow/.env` (if applicable).
2. Start the Airflow cluster using Docker Compose:

```bash
cd airflow
docker compose build
docker compose up -d
```

3. Access the Airflow UI at [http://localhost:8082](http://localhost:8082) (Default login: admin/admin).

### Run dbt & Start Docs Server

Assuming you have `uv` installed, you can use it to easily run `dbt` and its docs server without a local virtual environment:

```bash
cd zomato

# Run models
uvx --from dbt-snowflake dbt debug --profiles-dir .
uvx --from dbt-snowflake dbt build --profiles-dir .

# Generate and serve dbt docs (served on port 8085)
uvx --from dbt-snowflake dbt docs generate --profiles-dir .
uvx --from dbt-snowflake dbt docs serve --profiles-dir . --port 8085
```

Access the dbt docs at [http://localhost:8085](http://localhost:8085).

### Start Streamlit Apps

1. Fill your credentials in `ai/.env` (Snowflake + OpenAI API key).
2. Install dependencies:

```bash
cd ai
pip install -r requirements.txt
```

3. Run either app:

```bash
# RAG Chat – ask questions answered from review embeddings
streamlit run rag_chat.py            # http://localhost:8501

# Text-to-SQL – ask questions in English, get SQL + results
streamlit run text_to_sql.py         # http://localhost:8502
```

## Data Engineering Concepts

This project demonstrates:

**ELT** · **Data Lake** · **Data Warehouse** · **dbt** · **Airflow** · **Dimensional Modeling** · **Incremental Loads** · **SCD Type 2** · **Data Quality** · **Data Marts** · **AWS IAM**

> **Note:** Keep AWS, Snowflake, Airflow, and OpenAI credentials in environment variables or secret management. Never commit secrets to Git.
