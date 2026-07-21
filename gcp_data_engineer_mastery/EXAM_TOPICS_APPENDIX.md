# 📎 Exam Topics Appendix — Concepts the Real PDE Exam Tests

This appendix closes the gap between the 12 course modules and the full spread of
concepts the **actual Professional Data Engineer exam question bank** is known to
test. Each section maps to a module and adds the exam-relevant details that
didn't fit the module narrative. Every one of these topics also has matching
questions in the [Mock Exam](mock_exam/README.md).

---

## BigQuery (Modules 03–04)

### Sharded tables vs partitioned tables
Legacy pipelines often create one table per day (`events_20240101`,
`events_20240102`, …) — **table sharding**. The exam expects you to know:
- Sharding forces BigQuery to keep schema/metadata per table and check
  permissions per table queried → overhead; partitioned tables perform better.
- Queries hit the **1,000-tables-per-query limit**; a partitioned table supports
  up to **10,000 partitions** (long the exam's "4,000" — know both eras).
- You can query shards together with a **wildcard table**: `` `ds.events_*` ``
  filtered by the pseudo-column `_TABLE_SUFFIX` (e.g., `WHERE _TABLE_SUFFIX
  BETWEEN '20240101' AND '20240131'`).
- Migration path: `CREATE TABLE ... PARTITION BY` + one `INSERT ... SELECT` over
  the wildcard, or `bq` partition conversion — **convert shards into one
  date-partitioned table**.

### Nested & repeated fields (ARRAY / STRUCT) — denormalize on purpose
BigQuery is columnar and charges/performs by bytes scanned, so **denormalization
is normal**: model one-to-many relationships as `ARRAY<STRUCT<...>>` inside the
parent row instead of a separate table + join. Use `UNNEST()` to flatten at
query time. Exam signal: "orders and line items", "avoid joins", "self-describing
format" → nested/repeated schema (and prefer Avro/Parquet, which preserve it,
over CSV, which can't).

### BI Engine
**BI Engine** is an in-memory acceleration layer for BigQuery. Reserve capacity
and dashboard queries (Looker Studio, and SQL-interface BI tools) get
sub-second, cached scans with no data movement. Exam pattern: "dashboard is
slow / too costly, data already in BigQuery" → *BI Engine reservation* (or a
materialized view — BI Engine when you want to accelerate many/interactive
queries without rewriting anything; materialized view when one heavy
aggregation dominates).

### Search indexes & point lookups
`CREATE SEARCH INDEX` + `SEARCH()` makes needle-in-haystack lookups (find one
user's rows for GDPR, find an ID in logs) cheap without scanning every column of
every row.

### Short query optimized mode & continuous queries (newer exam refresh)
- Continuous queries let SQL run perpetually over streaming inserts, writing
  results onward (e.g., to another table or Pub/Sub) — SQL-only streaming
  transformation.
- Know they exist and their niche; Dataflow remains the answer for complex
  streaming logic.

---

## Databases (Module 05)

### AlloyDB for PostgreSQL — the HTAP answer
**AlloyDB** = PostgreSQL-compatible, Google-optimized: separates compute from a
distributed storage layer and keeps a **columnar engine** in memory, so it serves
**transactional AND analytical** queries on the same database. Exam signal:
"PostgreSQL app, want transactions *and* analytics in one system, better
performance than Cloud SQL" → AlloyDB. (Full multi-region horizontal write
scaling still → Spanner; simple lift-and-shift → Cloud SQL.)

### Spanner interleaved tables
Spanner lets you **interleave** a child table's rows physically inside the
parent's rows (`INTERLEAVE IN PARENT`): parent + children co-located → cheap
joins along that hierarchy (e.g., `Customers` → `Orders`). Use when the child is
always accessed with its parent; the child's PK must be prefixed by the
parent's PK.

### Bigtable operations
- **Key Visualizer**: heatmap diagnostic tool that shows access patterns per key
  range over time — THE tool to confirm hotspots from bad row-key design.
- **SSD vs HDD clusters**: SSD is the default for latency-sensitive serving
  (single-digit ms); HDD only for large, latency-tolerant, scan-heavy archives
  (rarely the exam answer).
- **HBase compatibility**: Bigtable speaks the **HBase API** — migrating an
  on-prem HBase (or Cassandra-style wide-column) workload → Bigtable with
  minimal application change.

### Firestore/Datastore export & analytics
Firestore (Datastore mode) has a **managed export** to a Cloud Storage bucket
(`gcloud firestore export`); the export can be **loaded straight into
BigQuery** for analytics. Terms to recognize: entities (~rows), kinds (~tables),
ancestor paths (hierarchy).

---

## Migration & Hybrid Connectivity (Modules 01–02)

### Choosing a transfer mechanism (a recurring exam item)
| Scenario | Answer |
|---|---|
| < a few TB, ad-hoc, decent bandwidth | `gcloud storage cp` / `gsutil` |
| Large recurring/scheduled transfers, S3/HTTP/on-prem NAS sources | **Storage Transfer Service** |
| Tens of TB–PB, poor/slow link, or a deadline the math can't meet | **Transfer Appliance** (physical device shipped to you) |
| SaaS sources (Google Ads, GA4, YouTube…) into BigQuery | **BigQuery Data Transfer Service** |
| Continuous database replication | **Datastream** (CDC) |

Rule of thumb: compute transfer time = data ÷ effective bandwidth; if it blows
the deadline (e.g., 400 TB over 100 Mbps ≈ 1 year), the answer is Transfer
Appliance.

### Private connectivity for data ingestion
- **Cloud Interconnect** (Dedicated/Partner) or **Cloud VPN** links on-prem to
  your VPC — required when data "must not traverse the public internet".
- **Private Google Access** lets VPC/on-prem hosts reach Google APIs
  (BigQuery, GCS, Pub/Sub) on private IPs (`private.googleapis.com` /
  `restricted.googleapis.com` for VPC-SC).
- **Datastream private connectivity**: peers Datastream into your VPC so CDC
  from an on-prem database flows over Interconnect/VPN privately — the exam's
  "replicate on-prem MySQL to BigQuery with no public internet" answer.

### Kafka → Google Cloud
Existing Kafka estates: use the **Pub/Sub Kafka connector** (Kafka Connect) or
mirror topics into Pub/Sub; Dataflow can also read Kafka directly. Managed
option: **Google Cloud Managed Service for Apache Kafka** when the requirement
is "keep Kafka but stop operating it".

---

## Dataproc (Module 08)

### Performance tuning the exam asks about
- **Disk-I/O-bound jobs**: attach **local SSDs** to workers (shuffle/spill go to
  SSD) or increase persistent-disk size (PD throughput scales with size).
  Signal: "job is slow on Dataproc vs on-prem bare metal; profiling shows heavy
  disk I/O" → local SSDs.
- **Graceful decommissioning**: when downscaling, let YARN nodes finish work
  first (`--graceful-decommission-timeout`) so running jobs don't lose
  shuffle/task progress; **Enhanced Flexibility Mode (EFM)** keeps shuffle data
  off secondary (spot) workers so their preemption doesn't kill jobs.
- Non-splittable inputs (gzip) cap parallelism (see Module 08).

---

## Dataflow / Beam (Module 07)

### Side outputs (tagged outputs) — the dead-letter pattern
A `ParDo` can emit to **multiple tagged outputs** (`TupleTag`s): main output for
good records, a side output for corrupt/unparseable ones, which you write to a
dead-letter table/bucket for later inspection. Exam signal: "filter/divert
malformed records in a streaming pipeline without dropping them" → **ParDo with
side outputs**. (Side *inputs* — small broadcast lookup data — are the other
direction; don't confuse them.)

### Monitoring a streaming pipeline (metric names matter)
- Pub/Sub source: `subscription/num_undelivered_messages` (backlog growing =
  pipeline not consuming) and `subscription/oldest_unacked_message_age`
  (freshness breach).
- Dataflow: **system lag** and **data watermark age** growing = falling behind;
  alert on these in Cloud Monitoring.
- Sink-side: an output-rate drop (e.g., GCS bytes written flat-lining) confirms
  the pipeline stopped producing.

---

## Orchestration & Data Quality (Module 09)

### Event-driven (not scheduled) DAG runs
When files arrive at **unpredictable times**, don't poll on a schedule: a Cloud
Storage **object-finalize trigger** fires a Cloud Function (or Eventarc →
Workflows) that calls the **Airflow REST API to trigger the DAG**. Exam signal:
"no fixed schedule for arriving data" → GCS trigger + function-triggered DAG
(one parameterized DAG per pipeline shape, not one per file).

### Cleansing patterns for dirty CSVs
- **Cloud Data Fusion Wrangler**: interactive, visual data preparation for
  analysts (the successor to Dataprep in exam answers) — profile, fix types,
  standardize formats, then run at scale.
- **ELT staging pattern**: load raw CSV into a staging table (all `STRING`
  columns if types are inconsistent), fix with SQL (`SAFE_CAST`, `REGEXP_REPLACE`),
  then `INSERT`/`MERGE` into the typed production table.

---

## Machine Learning (Module 11)

The bank still contains classic ML-theory items. Know these cold:

| Concept | One-liner |
|---|---|
| **Feature cross** | Synthetic feature = crossing two+ features (e.g., lat × long grid cells) so a *linear* model can learn non-linear interactions |
| **Wide & Deep** | Wide (linear, memorization of crosses) + Deep (embeddings, generalization) in one model — classic recommender architecture |
| **Embeddings** | Dense low-dimensional vectors representing high-cardinality categoricals (user IDs, words); learned; replace huge one-hot vectors |
| **Learning rate too high** | Loss oscillates or diverges → lower it (or use decay); too low → painfully slow convergence |
| **Batch size** | Larger = smoother gradients + more memory; smaller = noisier but sometimes generalizes better |
| **L1 vs L2** | L1 (lasso) drives weights to exactly zero → sparsity/feature selection; L2 (ridge) shrinks weights smoothly → default anti-overfitting |
| **Dropout** | Randomly deactivates units during training; regularizes deep nets (classic answer to "neural net overfits") |
| **Hyperparameter tuning** | Don't grid-search by hand: **Vertex AI hyperparameter tuning** (Vizier, Bayesian optimization) |
| **Precision vs recall** | Precision: of flagged, how many are correct — optimize when false positives are costly; Recall: of actual positives, how many caught — optimize when misses are costly; threshold moves the trade-off |

Also: pretrained APIs (Vision, Speech, NL, Translation, Document AI) before
custom training; BigQuery ML for SQL-first teams; training-serving skew and a
feature store as its fix (Module 11).

---

## IAM Best Practices (Module 10)

- Grant roles to **groups**, not individual users — membership changes shouldn't
  require IAM changes.
- Prefer **predefined roles** over primitive (Owner/Editor/Viewer); custom roles
  only when predefined over-grant.
- Service accounts for workloads, **no exported JSON keys**; use attached
  service accounts / workload identity.
- One service account **per pipeline/workload**, least privilege at the
  narrowest scope (dataset/bucket, not project) — audit with Policy Analyzer.
