# Module 8 Exercise: Serverless Spark ETL

## Goal
Run a PySpark aggregation as a **Serverless Spark batch** (no cluster to manage) that
reads CSV sales data from GCS and writes per-category revenue to the curated zone as
Parquet. Then provision an **ephemeral autoscaling cluster** with Spot workers as the
alternative, and compare.

## Tasks
Create `agg.py` (Spark) and `main.tf` (infra). Reference the `solution.*` files after.

### TODO 1 — Upload input
Put a small `sales.csv` (`category,amount` rows) in
`gs://$PROJECT_ID-lake-raw/sales/` and the job file in `gs://$PROJECT_ID-lake-raw/jobs/`.

### TODO 2 — Spark job
`agg.py` reads the CSV (`header=True`), groups by `category`, sums `amount`, and writes
Parquet to `gs://$PROJECT_ID-lake-curated/category_revenue/`. Use **gs://** paths only.

### TODO 3 — Serverless batch (Terraform)
Provision a `google_dataproc_batch` (PySpark) that runs `agg.py` with the input/output
args. Runtime version `2.2`.

### TODO 4 — Ephemeral cluster (Terraform)
Also define a `google_dataproc_cluster` with 2 on-demand primaries, 2 **SPOT**
secondaries, and `idle_delete_ttl = 1800s`. (Comment which one you'd use for a scheduled
nightly job and why → Serverless.)

## Self-Verification
```bash
terraform init && terraform apply -var project_id="$PROJECT_ID"

# The batch ran and produced output:
gcloud dataproc batches list --region=us-central1
gcloud storage ls gs://$PROJECT_ID-lake-curated/category_revenue/
#   → _SUCCESS + part-*.parquet files

# Query the result with BigQuery over the Parquet (external):
bq query --use_legacy_sql=false \
  "SELECT * FROM EXTERNAL_QUERY OR load it; or: bq load --source_format=PARQUET ..."
```

## Stretch Goals
1. Write the aggregation **directly to BigQuery** using the Spark-BigQuery connector.
2. Add an **autoscaling policy** to the cluster and describe the scale trigger.
3. Convert the whole job to a BigQuery SQL statement and argue when that's the better
   choice (transform is set-based → BigQuery wins).

## Cleanup
```bash
terraform destroy -var project_id="$PROJECT_ID"
gcloud dataproc batches delete wordcount-batch --region=us-central1 -q 2>/dev/null || true
```
