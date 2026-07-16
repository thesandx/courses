"""
Module 9 Solution — A Backfillable Daily Pipeline
=================================================
Idempotent daily error-rate rollup. Backfilling any date overwrites that date's
partition, so re-runs never duplicate.

Deploy: gcloud storage cp solution.py $(terraform output -raw dag_gcs_prefix)
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import (
    GCSToBigQueryOperator,
)
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator,
)

PROJECT = "YOUR_PROJECT"
RAW_BUCKET = f"{PROJECT}-lake-raw"

default_args = {"retries": 2, "retry_delay": timedelta(minutes=5)}

with DAG(
    dag_id="daily_error_rate",
    schedule="@daily",
    start_date=datetime(2026, 7, 1),
    catchup=False,                    # TODO 1: no mass backfill on deploy
    default_args=default_args,
    tags=["mastery"],
) as dag:

    # TODO 2 — wait for the day's log file
    wait = GCSObjectExistenceSensor(
        task_id="wait_for_log",
        bucket=RAW_BUCKET,
        object="logs/{{ ds }}/access.log",
        timeout=3600,
        poke_interval=60,
    )

    # TODO 3 — load into staging (truncate each run)
    load = GCSToBigQueryOperator(
        task_id="load_staging",
        bucket=RAW_BUCKET,
        source_objects=["logs/{{ ds }}/access.log"],
        destination_project_dataset_table=f"{PROJECT}.staging.access_stg",
        source_format="CSV",
        field_delimiter=" ",
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
    )

    # TODO 4 — idempotent partition overwrite (DELETE + INSERT for {{ ds }})
    transform = BigQueryInsertJobOperator(
        task_id="rollup_partition",
        configuration={
            "query": {
                "query": (
                    "DELETE FROM `{p}.analytics.error_rate` "
                    "WHERE log_date = DATE('{{{{ ds }}}}'); "
                    "INSERT INTO `{p}.analytics.error_rate` (log_date, total, errors) "
                    "SELECT DATE('{{{{ ds }}}}'), COUNT(*), "
                    "COUNTIF(SAFE_CAST(status AS INT64) >= 500) "
                    "FROM `{p}.staging.access_stg`"
                ).format(p=PROJECT),
                "useLegacySql": False,
            }
        },
    )

    # TODO 5
    wait >> load >> transform
