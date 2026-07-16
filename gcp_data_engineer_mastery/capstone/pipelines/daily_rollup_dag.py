"""
Capstone — Daily Rollup DAG (Cloud Composer / Airflow)
======================================================
Idempotent daily batch (Modules 8, 9):
  Dataproc Serverless enrich raw->curated  ->  build daily marts (partition
  overwrite, so backfills don't duplicate)  ->  retrain the demand forecast.

Deploy: gcloud storage cp daily_rollup_dag.py $(terraform output -raw dag_gcs_prefix)
"""
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocCreateBatchOperator,
)
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator,
)

PROJECT = os.environ.get("GCP_PROJECT", "YOUR_PROJECT")
REGION = "us-central1"
CURATED_BUCKET = os.environ.get("CURATED_BUCKET", f"{PROJECT}-rideshare-curated")

default_args = {"retries": 2, "retry_delay": timedelta(minutes=5)}

with DAG(
    dag_id="rideshare_daily_rollup",
    schedule="@daily",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    default_args=default_args,
    tags=["capstone"],
) as dag:

    # 1. Serverless Spark: enrich the day's raw trips into curated Parquet (Module 8).
    enrich = DataprocCreateBatchOperator(
        task_id="enrich_curated",
        project_id=PROJECT,
        region=REGION,
        batch_id="enrich-{{ ds_nodash }}",
        batch={
            "pyspark_batch": {
                "main_python_file_uri": f"gs://{CURATED_BUCKET}/jobs/enrich.py",
                "args": ["{{ ds }}"],
            },
            "runtime_config": {"version": "2.2"},
        },
    )

    # 2. Idempotent daily mart: overwrite ONLY this date's partition (Modules 4, 9).
    build_mart = BigQueryInsertJobOperator(
        task_id="build_daily_mart",
        configuration={
            "query": {
                "query": (
                    "DELETE FROM `{p}.rideshare_marts.daily_kpis` "
                    "WHERE trip_date = DATE('{{{{ ds }}}}'); "
                    "INSERT INTO `{p}.rideshare_marts.daily_kpis` "
                    "SELECT DATE('{{{{ ds }}}}') AS trip_date, "
                    "COUNT(*) AS trips, SUM(fare_cents) AS revenue_cents, "
                    "COUNT(DISTINCT driver_id) AS active_drivers "
                    "FROM `{p}.rideshare.trips_raw` "
                    "WHERE DATE(event_ts) = DATE('{{{{ ds }}}}')"
                ).format(p=PROJECT),
                "useLegacySql": False,
            }
        },
    )

    # 3. Retrain the demand forecast on the latest marts (Module 11).
    retrain_forecast = BigQueryInsertJobOperator(
        task_id="retrain_forecast",
        configuration={
            "query": {
                "query": (
                    "CREATE OR REPLACE MODEL `{p}.rideshare_ml.demand` "
                    "OPTIONS(model_type='ARIMA_PLUS', "
                    "time_series_timestamp_col='trip_date', "
                    "time_series_data_col='trips', data_frequency='DAILY') AS "
                    "SELECT trip_date, trips FROM `{p}.rideshare_marts.daily_kpis`"
                ).format(p=PROJECT),
                "useLegacySql": False,
            }
        },
    )

    enrich >> build_mart >> retrain_forecast
