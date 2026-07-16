# Module 9 Exercise: A Backfillable Daily Pipeline

## Goal
Author an Airflow DAG that ingests a day's web-log file and produces a daily error-rate
summary — and can be **safely backfilled** for any past date without duplicating data.
This is the orchestration skill the exam probes hardest.

## Tasks
Create `logs_dag.py`. Reference `solution.py` after attempting.

### TODO 1 — DAG skeleton
`dag_id="daily_error_rate"`, `schedule="@daily"`, a `start_date`, **`catchup=False`**,
`retries=2`, `retry_delay=5m`.

### TODO 2 — Sensor
`GCSObjectExistenceSensor` waiting for `logs/{{ ds }}/access.log` in your raw bucket.

### TODO 3 — Load
`GCSToBigQueryOperator` loading that file into `staging.access_stg` with
`WRITE_TRUNCATE`.

### TODO 4 — Idempotent transform
`BigQueryInsertJobOperator` that **deletes then inserts** the `{{ ds }}` partition of
`analytics.error_rate` (columns: `log_date DATE, total INT64, errors INT64`). Re-running
a date must overwrite, not append.

### TODO 5 — Wire dependencies
`sensor >> load >> transform`.

## Self-Verification
```bash
# Copy the DAG to the Composer bucket:
gcloud storage cp logs_dag.py "$(terraform -chdir=../ output -raw dag_gcs_prefix)"

# In the Airflow UI (airflow_uri output), the DAG parses with no import errors.

# Trigger a specific past date twice and confirm NO duplication:
gcloud composer environments run de-orchestration --location=us-central1 \
  dags trigger -- daily_error_rate -e 2026-07-02
# (run it again for the same date)
bq query --use_legacy_sql=false \
  "SELECT log_date, COUNT(*) FROM analytics.error_rate WHERE log_date='2026-07-02' GROUP BY log_date"
#   → exactly ONE row (idempotent), not two
```

## Stretch Goals
1. Add an `on_failure_callback` that posts to a Pub/Sub topic (alerting).
2. Add a task-level `sla` and observe an SLA miss in the UI.
3. Replace the transform with a **DataprocCreateBatchOperator** (Serverless Spark) and
   compare when you'd use SQL vs Spark here.

## Cleanup
```bash
terraform destroy -var project_id="$PROJECT_ID"   # deletes the (costly) environment
```
