"""
Module 9: Cloud Composer — Concepts in Action (Airflow DAG)
===========================================================
An IDEMPOTENT daily pipeline:
  wait for the day's file in GCS  ->  load to a BigQuery staging table
  ->  transform into the date PARTITION (overwrite, so re-runs don't duplicate)
  ->  export the result to GCS.

Deploy: copy this file into the Composer environment's DAG bucket:
  gcloud storage cp dag.py $(terraform output -raw dag_gcs_prefix)
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import (
    GCSToBigQueryOperator,
)
from airflow.providers.google.cloud.transfers.bigquery_to_gcs import (
    BigQueryToGCSOperator,
)
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator,
)

PROJECT = "{{ var.value.get('gcp_project', 'YOUR_PROJECT') }}"
RAW_BUCKET = "YOUR_PROJECT-lake-raw"
CURATED_BUCKET = "YOUR_PROJECT-lake-curated"

default_args = {
    "retries": 3,                       # transient-failure recovery
    "retry_delay": timedelta(minutes=5),
    "sla": timedelta(hours=2),          # alert if late
}

with DAG(
    dag_id="daily_sales_rollup",
    schedule="@daily",
    start_date=datetime(2026, 7, 1),
    catchup=False,                      # don't backfill every past interval on deploy
    default_args=default_args,
    tags=["mastery", "idempotent"],
) as dag:

    # 1. Wait for the day's file. {{ ds }} = the run's logical date (YYYY-MM-DD).
    wait_for_file = GCSObjectExistenceSensor(
        task_id="wait_for_file",
        bucket=RAW_BUCKET,
        object="sales/{{ ds }}/sales.csv",
        timeout=60 * 60,
        poke_interval=60,
    )

    # 2. Load that day's file into a staging table (truncate staging each run).
    load = GCSToBigQueryOperator(
        task_id="load_staging",
        bucket=RAW_BUCKET,
        source_objects=["sales/{{ ds }}/sales.csv"],
        destination_project_dataset_table=f"{PROJECT}.staging.sales_stg",
        source_format="CSV",
        skip_leading_rows=1,
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
    )

    # 3. IDEMPOTENT transform: overwrite ONLY this date's partition, so re-running
    #    the same logical date replaces (never duplicates) its rows.
    transform = BigQueryInsertJobOperator(
        task_id="transform_partition",
        configuration={
            "query": {
                "query": (
                    "DELETE FROM `{p}.analytics.daily_sales` "
                    "WHERE sale_date = DATE('{{{{ ds }}}}'); "
                    "INSERT INTO `{p}.analytics.daily_sales` "
                    "SELECT DATE('{{{{ ds }}}}') AS sale_date, category, SUM(amount) AS revenue "
                    "FROM `{p}.staging.sales_stg` GROUP BY category"
                ).format(p=PROJECT),
                "useLegacySql": False,
            }
        },
    )

    # 4. Export the day's result to the curated zone.
    export = BigQueryToGCSOperator(
        task_id="export_result",
        source_project_dataset_table=f"{PROJECT}.analytics.daily_sales",
        destination_cloud_storage_uris=[
            f"gs://{CURATED_BUCKET}/daily_sales/{{{{ ds }}}}/*.parquet"
        ],
        export_format="PARQUET",
    )

    wait_for_file >> load >> transform >> export
