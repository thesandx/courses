# Module 3 Exercise: Model & Query an Events Dataset

## Goal
Create an `ecommerce` dataset, model a `sessions` table with nested page-view events,
load a few rows, and write a query that flattens the nested data — proving you can model
and query BigQuery's semi-structured style.

## Tasks
Create `main.tf` for infra and `answers.sql` for queries. Reference the `solution.*`
files after attempting.

### TODO 1 — Dataset
`google_bigquery_dataset` `ecommerce` in `var.region`, `delete_contents_on_destroy = true`.

### TODO 2 — Nested table
Create a `sessions` table with:
- `session_id STRING REQUIRED`, `user_id STRING`, `started_at TIMESTAMP`
- `pageviews` — a **REPEATED STRUCT** of `{ url STRING, ts TIMESTAMP, dwell_ms INT64 }`

### TODO 3 — Load rows
Insert (via SQL `INSERT`) at least 2 sessions, each with 2+ pageviews.

### TODO 4 — Flatten query
Write a query returning **one row per pageview**: `session_id, url, dwell_ms`, ordered by
`dwell_ms DESC`.

### TODO 5 — Aggregate query
Return, per `user_id`, the total number of pageviews and total dwell time.

## Self-Verification
```bash
terraform init && terraform apply -var project_id="$PROJECT_ID"

bq query --use_legacy_sql=false \
  'SELECT COUNT(*) AS n FROM ecommerce.sessions'
#   → n = 2 (or however many you inserted)

# Flatten check — rows should exceed session count:
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM ecommerce.sessions, UNNEST(pageviews)'
#   → >= 4

# Dry-run to see bytes scanned (cost awareness):
bq query --dry_run --use_legacy_sql=false \
  'SELECT session_id FROM ecommerce.sessions'
#   → prints "... will process N bytes"
```

## Stretch Goals
1. Create a **view** `top_pages` returning the 10 URLs by total dwell time.
2. Add an **external table** over a CSV you upload to GCS and query it without loading.
3. Use `bq load` to bulk-load a newline-delimited JSON file and compare cost (free) vs an
   `INSERT` (query cost).

## Cleanup
```bash
terraform destroy -var project_id="$PROJECT_ID"
```
