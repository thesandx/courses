# Phase 05 — Spark on Dataproc: RAW→ODP→FDP, SCD2 & Surrogate Keys ⑤⑥ (`v0.5.0`)

> **Mission:** distributed processing enters the platform. PySpark jobs on
> **Dataproc Serverless** promote RAW to a typed, deduplicated, event-date-
> partitioned ODP (Parquet on GCS, exposed to BigQuery via BigLake), and build the
> FDP layer with **SCD Type-2 history** and **surrogate keys** using the
> Spark-computes / BigQuery-MERGEs hybrid pattern. Late data handled by design.

## 1. Concepts

Read notes **§29 (Spark internals)**, **§17 (late data)**, **§18 (dedup)**,
**§22 (medallion)**, **§6 (SCD strategy)**; GCP **M08 (Dataproc)**.

**Layer semantics you are implementing (charter §3):**

| Transition | What happens | Write pattern | Partitioning |
|---|---|---|---|
| RAW→ODP | parse, type-cast per contract, normalize names, **dedup**, add `_pf_*` audit cols | **dynamic partition overwrite** | by **event_date** (business time starts here — §17) |
| ODP→FDP | conform, **SCD2** for dims, surrogate keys, tokenized PII (P09) | staging + **MERGE** | business date / current-flag |

**Why the ingestion-date→event-date flip at ODP?** RAW partitions by when data
*arrived* (predictable, append-safe). Analytics needs *when it happened*. The
promotion job reads arrival-partitioned input and writes event-partitioned output —
and because late events land in old event_date partitions, the job processes a
**lookback window**: running for execution_date D rewrites event_date partitions
[D−2, D]. That one sentence is the §17 "append & compact + grace period" strategy
in production form.

**The dedup you promised in Phase 4** — the ROW_NUMBER pattern (§18), verbatim:

```python
w = Window.partitionBy("event_id").orderBy(F.col("event_ts").desc(),
                                           F.col("_pf_ingested_at").desc())
deduped = df.withColumn("rn", F.row_number().over(w)).filter("rn = 1").drop("rn")
```

**SCD2 (⑤):** dims keep full history with `effective_from`, `effective_to`,
`is_current`. Use it where reporting accuracy depends on historical attribute
values (customer tier at *order time* — §6). You'll join facts to dims *as-of
event time* in Phase 6, the late-arriving-fact pattern (§17).

**Surrogate keys (⑥):** deterministic hash of (tenant, natural key):
`sha256("novamart|customer|C123")[:16]`. Why hash over sequence? Idempotent
(re-runs produce identical keys — no coordination state), parallel-safe, stable
across backfills. Tradeoff to be able to recite: theoretical collisions
(negligible at 64+ bits for your cardinality — do the birthday math), and keys are
opaque/wide vs compact ints. A `key_map` table in FDP records natural→surrogate
for debugging and GDPR lookups.

**Spark-computes / BigQuery-MERGEs:** the Spark BigQuery connector can't run
`MERGE`. So Spark writes the *change set* to a BQ staging table, then the
framework executes one atomic `MERGE` in BigQuery. Heavy lifting distributed,
mutation atomic — a genuinely common production pattern, and a tidy answer to
"how do you get idempotent upserts out of Spark?"

## 2. Build

### 2.1 Terraform for Dataproc Serverless

Serverless batches need a subnet with Private Google Access; add a `network`
module (VPC + subnet + PGA + firewall) and a `dataproc` module granting the
pipeline SA `roles/dataproc.worker`, plus a BQ dataset `odp` and the BigLake
connection for external tables. Also grant the SA `roles/bigquery.jobUser` and
dataset-level write on `fdp_staging`/`fdp`.

### 2.2 Job scaffolding — `src/pipeforge/processing/spark/`

`session.py`:

```python
def spark_session(app: str) -> SparkSession:
    return (SparkSession.builder.appName(app)
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")  # idempotent partition writes
        .config("spark.sql.adaptive.enabled", "true")                   # AQE: runtime coalesce/skew (§29)
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate())
```

`standardize.py` (RAW→ODP, one job for ALL datasets — parameter-driven):

```python
def run(dataset_name: str, execution_date: str, lookback_days: int = 2) -> None:
    ds, contract = load_registry(dataset_name)          # reads Phase-2 metadata
    spark = spark_session(f"odp-{dataset_name}")

    # 1. Read only complete batches for the window (manifests are the source of truth)
    paths = latest_complete_batches(ds, execution_date, lookback_days)
    raw = read_source_native(spark, ds, paths)          # csv/jsonl/parquet per contract

    # 2. Type-cast from the contract (contract-driven casting = zero per-dataset code)
    typed = cast_per_contract(raw, contract)            # bad casts -> _pf_cast_errors column

    # 3. Audit columns
    typed = (typed
        .withColumn("_pf_ingested_at", F.col("_pf_ingested_at").cast("timestamp"))
        .withColumn("_pf_batch_id", F.input_file_name())
        .withColumn("event_date", F.to_date(F.col(ds.business_date_column))))

    # 4. Dedup (ROW_NUMBER pattern) on primary keys
    deduped, dup_count = dedup(typed, ds.primary_keys, order_col=ds.business_date_column)

    # 5. Write: dynamic partition overwrite of ONLY the touched event_date partitions
    (deduped.write.mode("overwrite")
        .partitionBy("event_date")
        .parquet(f"gs://{settings.odp_bucket}/{dataset_name}/"))

    emit_audit(rows_read=raw.count(), rows_written=deduped.count(),
               rows_deduped=dup_count)                  # -> pipeline_run
```

Target file sizes while writing: aim for the 100 MB–1 GB sweet spot (§11);
`coalesce()` small datasets to 1 file — streaming micro-batches will otherwise
give you the **small-file problem**; schedule a weekly compaction of clickstream
ODP partitions (this is your §11 "compaction is mandatory" checkbox).

`scd2.py` (ODP→FDP for dims) — the algorithm, which you should be able to
whiteboard cold by the end of this phase:

```python
def build_scd2_changeset(spark, dataset, execution_date):
    """Compare today's ODP snapshot of a dim against current FDP rows.
    Emit a changeset with row_action in {INSERT_NEW, CLOSE_AND_INSERT}."""
    incoming = spark.read.parquet(odp_path(dataset)).where(f"event_date <= '{execution_date}'")
    incoming = latest_per_key(incoming, dataset.primary_keys)        # ROW_NUMBER again
    incoming = incoming.withColumn("sk", surrogate_key(dataset, *dataset.primary_keys)) \
                       .withColumn("attr_hash", F.sha2(F.concat_ws("|", *tracked_attrs), 256))

    current = read_bq(spark, f"fdp.dim_{dataset.name}").where("is_current")

    joined = incoming.alias("n").join(current.alias("c"),
                                      on=dataset.primary_keys, how="left")
    new_keys  = joined.where("c.sk IS NULL")                          # never seen
    changed   = joined.where("c.sk IS NOT NULL AND n.attr_hash != c.attr_hash")
    return new_keys, changed
```

Then the framework runs the atomic close-and-insert in BigQuery (one script,
`serving/sql/scd2_merge.sql.j2`, rendered per dataset):

```sql
MERGE `fdp.dim_{{ name }}` t
USING `fdp_staging.dim_{{ name }}_changes_{{ ds_nodash }}` s
ON t.{{ nk }} = s.{{ nk }} AND t.is_current
WHEN MATCHED AND s.row_action = 'CLOSE_AND_INSERT' THEN
  UPDATE SET t.is_current = FALSE, t.effective_to = s.effective_from
WHEN NOT MATCHED BY TARGET THEN
  INSERT ({{ cols }}, effective_from, effective_to, is_current)
  VALUES ({{ cols }}, s.effective_from, TIMESTAMP '9999-12-31', TRUE);
-- Second statement inserts the new versions for CLOSE_AND_INSERT keys;
-- both run in one multi-statement transaction => atomic, re-runnable.
```

Re-run safety: the changeset for a re-run is empty (attr_hash matches) — SCD2 via
MERGE is idempotent *by construction*. That's the interview line.

`sessionize.py` (clickstream ODP→FDP `fct_sessions`): sessions = gaps > 30 min per
customer — lag/window functions, event-time based. This job is your shuffle/skew
laboratory (a handful of bot customers with 100x events — you'll fix them in P13).

### 2.3 Submitting to Dataproc Serverless

```bash
gcloud dataproc batches submit pyspark src/pipeforge/processing/spark/standardize.py \
  --project $PROJECT_ID --region us-central1 \
  --deps-bucket gs://$PROJECT_ID-pf-dev-artifacts \
  --subnet pf-dev-subnet \
  --service-account pf-dev-pipeline@$PROJECT_ID.iam.gserviceaccount.com \
  --properties spark.executor.instances=2,spark.driver.memory=4g \
  -- --dataset clickstream --execution-date 2026-07-15
```

Wrap it as `pipeforge spark submit --job standardize --dataset clickstream
--execution-date …` (packages your wheel to the artifacts bucket first). Also
support `--local` (spark-submit against local files) — the dev loop must not cost
money or minutes.

**Read the Spark UI once per job** (Dataproc batch → "View Spark UI"): find the
shuffle boundary of the dedup (Exchange in the plan), note task counts, spot the
sessionization skew in the task-duration histogram. Interviews love "in the Spark
UI I saw…" sentences (§29).

### 2.4 BigLake external tables over ODP

Terraform `google_bigquery_table` with `external_data_configuration`
(hive partitioning on `event_date`) for each ODP dataset → analysts can
`SELECT … WHERE event_date = …` and BigQuery prunes partitions. Compare bytes
scanned with/without the filter (`--dry_run`) and write the numbers in the ADR.

### 2.5 Ship it

Tests (run Spark locally in pytest — `pyspark` is just a pip dep): dedup keeps the
right row, contract casting quarantines bad types, SCD2 changeset on a crafted
day-1/day-2 fixture (new key, changed attr, unchanged, re-run ⇒ empty), surrogate
keys stable across runs. Tag `v0.5.0`.

## 3. Prove it

- [ ] ODP clickstream: zero duplicate `event_id` (`SELECT event_id, COUNT(*) … HAVING COUNT(*)>1` → empty) even though RAW had Phase-4 rebalance duplicates — **effectively-once demonstrated**
- [ ] Late rows landed in D−1/D−2 event_date partitions (generator `--late-fraction`)
- [ ] `dim_customers` SCD2: churned customer has 2 rows, old one closed with `effective_to` = new `effective_from`, one `is_current`
- [ ] Re-run FDP job for same date twice → identical table state (row counts + checksums)
- [ ] Same natural key → same surrogate key across two independent backfill runs
- [ ] Dataproc batch completes with 2 executors; you can screenshot the shuffle stage

## 4. Break it

1. **The 2x-revenue classic (§7):** temporarily switch ODP write mode to `append`,
   run the same date twice, watch counts double in a scratch copy. Revert. Now you
   have *personally caused* the incident every interviewer asks about.
   `docs/incidents/005-append-double-count.md`.
2. Feed a `products` file where `unit_price_usd` becomes `unit_price` (the Phase-2
   rename prediction): watch contract casting quarantine 100% of rows and the run
   fail its volume check. The prediction file from Phase 2 gets its "verified" note.

## 5. Interview corner

- Whiteboard SCD2 end-to-end in < 5 min: changeset (hash compare) → atomic
  close-and-insert MERGE → as-of join. Include `effective_from/to`, `is_current`.
- *"How do you handle late data?"* → event-time partitioning + lookback rewrite +
  "data complete through X" honesty (§17) — with your `--late-fraction` demo as proof.
- *"Why not process everything in BigQuery SQL?"* / *"Why not all Spark?"* — the
  hybrid: distributed transform where Python/complexity lives, atomic MERGE where
  the warehouse is strongest. Also know the pure-ELT (dbt) counter-position (§32).
- Recite the four dedup layers (§18) — you now run all four.

## 6. Stretch goals

- **Iceberg on BigLake metastore**: rebuild ODP as Iceberg tables; Spark
  `MERGE INTO` natively; time-travel a bad write away (§35). Compare with the
  staging+MERGE hybrid in an ADR.
- CDC realism: run Debezium in docker against the MySQL source, land the change
  stream to Kafka, and extend `scd2.py` to consume op-coded events (§23, §37) —
  including the delete events your watermark loader misses.
- `EXPLAIN` both MERGE strategies in BQ; measure slot-time.
