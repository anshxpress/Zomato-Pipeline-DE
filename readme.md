Zomato --- End-to-End Data Engineering Pipeline

An end-to-end Data Engineering project that builds a cloud-based ELTpipeline for Zomato restaurant and order data using AWS, Snowflake, dbt,and Airflow.

Architecture

CSV Data
   ↓
AWS S3
   ↓
Snowflake (Bronze)
   ↓
dbt (Silver → Gold)
   ↓
Data Marts
   ↓
Analytics / AI

Apache Airflow orchestrates the pipeline from ingestion throughtransformation and validation.

Tech Stack

Languages: Python, SQL

Cloud: AWS S3

Data Warehouse: Snowflake

Transformation: dbt

Orchestration: Apache Airflow

Processing: Pandas

AI: OpenAI API

Application: Streamlit

Infrastructure: Docker

Key Features

Built an end-to-end ELT pipeline from raw CSV data toanalytics-ready datasets.

Implemented Bronze → Silver → Gold data architecture.

Developed dbt models with incremental processing, dimensionalmodeling, and SCD Type 2 snapshots.

Added dbt data quality tests including uniqueness, null,relationship, and accepted-value checks.

Automated pipeline execution using Apache Airflow.

Created analytical fact, dimension, and business-mart tables inSnowflake.

Added an optional AI layer for review enrichment, RAG, andnatural-language SQL.

Pipeline Flow

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

Project Structure

├── airflow/       # Airflow DAGs and Docker setup
├── zomato/        # dbt models and transformations
├── snowflake/     # Snowflake setup and SQL scripts
├── ai/            # AI enrichment and analytics
├── docs/          # Architecture documentation
└── README.md

Setup

Prerequisites

Python 3.x

Docker

AWS account

Snowflake account

dbt

OpenAI API key (AI features only)

Run dbt

cd zomato
dbt debug
dbt build

Start Airflow

cd airflow
docker compose up -d

Then open:

http://localhost:8080

Data Engineering Concepts

This project demonstrates:

ELT · Data Lake · Data Warehouse · dbt · Airflow · DimensionalModeling · Incremental Loads · SCD Type 2 · Data Quality · Data Marts ·AWS IAM

Note: Keep AWS, Snowflake, Airflow, and OpenAI credentials inenvironment variables or secret management. Never commit secrets toGit.
