FROM apache/airflow:3.0.0

# Install uv for fast python package management
RUN pip install uv

# Create a virtual environment for dbt and install dbt-snowflake
RUN uv venv /opt/airflow/dbt_venv && \
    uv pip install --python /opt/airflow/dbt_venv dbt-snowflake

# Install necessary providers in the main airflow environment
RUN pip install --no-cache-dir apache-airflow-providers-snowflake apache-airflow-providers-fab
