# Module 4 Exercise: Redesign a Table for Scale

## Goal
You inherit a flat `weblogs` table that analysts scan fully every query. Redesign it with
partitioning, clustering, and guardrails, then prove (via dry run) that a typical query
now scans far fewer bytes.

## Tasks
Create `main.tf` and `answers.sql`. Reference the `solution.*` files after attempting.

### TODO 1 — Dataset
`google_bigquery_dataset` `logs` in `var.region`, contents deletable on destroy.

### TODO 2 — Partitioned + clustered table
Create `weblogs`:
- Columns: `request_ts TIMESTAMP`, `status INT64`, `host STRING`, `path STRING`,
  `bytes INT64`.
- **Partition by DAY** on `request_ts`, expire after **30 days**, and
  **require a partition filter**.
- **Cluster by** `host, status` (the columns analysts filter on).

### TODO 3 — Materialized view
A MV `errors_per_host_daily` = daily count of rows where `status >= 500`, per host.

### TODO 4 — Prove the win
Write two queries in `answers.sql`: one properly filtered by a single day + host, and one
that would be rejected (no partition filter) — comment the second and explain why.

## Self-Verification
```bash
terraform init && terraform apply -var project_id="$PROJECT_ID"

# Table is partitioned + clustered:
bq show --format=prettyjson $PROJECT_ID:logs.weblogs | \
  python3 -c "import json,sys;d=json.load(sys.stdin);print('part:',d.get('timePartitioning'));print('cluster:',d.get('clustering'))"
#   → part: {...'field':'request_ts','requirePartitionFilter':True...}  cluster: {'fields':['host','status']}

# Unfiltered query is REJECTED (guardrail works):
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM logs.weblogs' 2>&1 | grep -i partition
#   → error mentioning partition filter (expected)

# Dry-run the filtered query to see the small scan:
bq query --dry_run --use_legacy_sql=false \
  'SELECT path FROM logs.weblogs WHERE request_ts >= TIMESTAMP("2026-07-01") AND request_ts < TIMESTAMP("2026-07-02") AND host="api"'
#   → prints a small "will process N bytes"
```

## Stretch Goals
1. Add `maximum_bytes_billed` via a `bq` flag and show a too-large query gets blocked.
2. Convert on-demand thinking to capacity: describe when you'd buy an **Editions**
   reservation for this workload.
3. Add a **search index** on `path` and use `SEARCH()` for a needle lookup.

## Cleanup
```bash
terraform destroy -var project_id="$PROJECT_ID"
```
