# Module 5 Exercise: Pick & Provision the Right Store

## Goal
Three product teams describe their needs. For **each**, name the correct GCP database,
justify it in one sentence, and provision it with Terraform. This is exactly the reasoning
the exam tests.

## Scenarios
1. **Fleet telemetry** — 2 million vehicle sensor writes/second, queried by
   `vehicle_id` + time window, single-digit-ms reads, petabyte retention.
2. **Global wallet** — user balances and transfers that must be **strongly consistent
   worldwide** and scale horizontally without sharding.
3. **Loyalty mobile app** — user profiles and point history, needs **offline sync** and
   realtime updates on phones.

## Tasks
Create `main.tf`. Reference `solution.tf` after attempting.

### TODO 1 — Decide (write it in a comment)
For each scenario, put a comment: `# Scenario N -> <service> because <reason>`.

### TODO 2 — Provision scenario 1
Provision the chosen store for telemetry with an **autoscaling** cluster and a column
family. In a comment, state the **row-key design** you'd use and why it avoids hotspotting.

### TODO 3 — Provision scenario 2
Provision the chosen global relational store with a small node count and one database +
one table (DDL).

### TODO 4 — Provision scenario 3
Provision the chosen document store.

## Self-Verification
```bash
terraform init && terraform apply -var project_id="$PROJECT_ID"

# Scenario 1 store exists and autoscales:
gcloud bigtable instances list
gcloud bigtable clusters list --instances=<your-instance>
#   → shows min/max autoscaling nodes

# Scenario 2 (Spanner) instance + db exist:
gcloud spanner instances list
gcloud spanner databases list --instance=<your-instance>

# Scenario 3 (Firestore) database exists:
gcloud firestore databases list
```

Correct answers: **1 → Bigtable**, **2 → Spanner**, **3 → Firestore**.

## Stretch Goals
1. Add a **Memorystore (Redis)** cache for scenario 2's hot balances (sub-ms reads).
2. For scenario 1, justify SSD vs HDD storage and pick based on latency needs.
3. Explain why **BigQuery** is wrong for all three (it's analytical, seconds-latency, not
   OLTP).

## Cleanup
```bash
# These stores bill hourly — destroy right away.
terraform destroy -var project_id="$PROJECT_ID"
```
