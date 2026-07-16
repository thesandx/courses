# Module 4: BigQuery at Scale — Performance & Cost

## Learning Objectives
- Design **partitioning** and **clustering** to slash bytes scanned.
- Choose between **on-demand** and **capacity (slot/editions)** pricing.
- Use **materialized views**, **BI Engine**, and **search indexes** to speed dashboards.
- Diagnose queries with the **query plan** and avoid the classic anti-patterns.
- Control cost with **partition expiration, `maximum_bytes_billed`, and dry runs**.

---

## 1. Partitioning: Prune Whole Blocks

A partitioned table is physically split so a `WHERE` on the partition column reads only
matching partitions.

| Partition type | Column | Use |
|----------------|--------|-----|
| **Time-unit** | `DATE`/`TIMESTAMP`/`DATETIME` (hour/day/month/year) | Time-series, logs, events |
| **Ingestion-time** | pseudo-column `_PARTITIONTIME` | You don't control a time column |
| **Integer range** | INT64 bucketed | Numeric key like customer_id ranges |

```sql
CREATE TABLE analytics.events (
  event_ts TIMESTAMP, user_id STRING, action STRING
)
PARTITION BY DATE(event_ts)
OPTIONS (partition_expiration_days = 90, require_partition_filter = TRUE);
```

> **Pitfall:** `require_partition_filter = TRUE` forces every query to include a partition
> predicate — the single best guardrail against accidental full-table scans. Also: max
> **4,000 partitions** per table.

## 2. Clustering: Sort Within Partitions

Clustering sorts data by up to **4 columns**, so filters/aggregations on those columns
read less. It's complementary to partitioning.

| | Partitioning | Clustering |
|--|-------------|-----------|
| Granularity | Coarse (whole partitions) | Fine (sorted blocks) |
| Cardinality fit | Low-medium (dates) | **High** (user_id, sku) |
| Cost guarantee | Predictable prune | Best-effort (auto-reclustered) |
| Limit | 4,000 partitions | 4 columns, **order matters** (most-filtered first) |

> **Exam pattern:** *partition by date, cluster by the high-cardinality columns you
> filter/group on* (e.g. `PARTITION BY DATE(ts) CLUSTER BY customer_id, sku`).

## 3. Pricing Models

| Model | You pay for | Best when |
|-------|-------------|-----------|
| **On-demand** | Bytes **scanned** ($/TiB) | Spiky/unpredictable, low volume |
| **Editions (capacity)** | **Slot-hours** (autoscale + baseline), Standard/Enterprise/Enterprise Plus | Steady, high volume; predictable cost |
| **Flat-rate commitments** | Reserved slots (1yr/3yr) | Large, stable workloads (discount) |

> **Trap:** on-demand has a **per-query bytes-scanned** cost — a single `SELECT *` on a
> huge table can be expensive. Cap it with `maximum_bytes_billed`.

## 4. Speeding Up Reads

| Tool | What it does | Use |
|------|-------------|-----|
| **Materialized view** | Precomputes & **incrementally** maintains an aggregate | Repeated GROUP BY dashboards |
| **BI Engine** | In-memory acceleration for BI/Looker | Sub-second dashboards |
| **Search index** | Indexes text/columns for `SEARCH()` and point lookups | Needle-in-haystack lookups |
| **Table snapshot / clone** | Cheap point-in-time copies | Backups, dev copies |

Materialized views auto-rewrite: queries against the **base table** can be transparently
served from the MV ("smart tuning").

## 5. Reading the Query Plan

`EXPLAIN`-style stages appear in the console / `INFORMATION_SCHEMA.JOBS`. Watch for:
- **High "bytes shuffled"** → a big JOIN; consider denormalizing / broadcast.
- **Skew** (one slot does most work) → skewed join key; salt it.
- **Repartition stages** → often from `ORDER BY` on huge sets; limit or pre-aggregate.

```sql
-- Find your most expensive queries in the last day:
SELECT job_id, total_bytes_billed, total_slot_ms, query
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
ORDER BY total_bytes_billed DESC
LIMIT 10;
```

---

## 🎯 Exam Focus

| Scenario | Answer |
|----------|--------|
| "Queries always filter by date and customer" | `PARTITION BY DATE(ts) CLUSTER BY customer_id` |
| "Prevent accidental full scans" | `require_partition_filter = TRUE` + `maximum_bytes_billed` |
| "Same dashboard aggregate runs all day" | **Materialized view** (+ BI Engine) |
| "Steady multi-TB daily workload, predictable bill" | **Editions / slot commitments** |
| "Spiky, occasional queries" | **On-demand** |
| "Table has 6 years of daily data — partition limit?" | Max 4,000 partitions → partition by **month**, or expire old partitions |

### Practice Questions
1. **A 5 TB events table is always filtered by `event_date` and grouped by `country`.
   Design it.** → `PARTITION BY event_date CLUSTER BY country`. Partition prunes dates;
   clustering speeds the group-by.
2. **Analysts keep running unbounded `SELECT *` and blowing the budget.** →
   `require_partition_filter = TRUE`, set `maximum_bytes_billed`, and educate on column
   selection; consider Editions with a slot cap.
3. **A Looker dashboard recomputes the same daily revenue rollup thousands of times.** →
   **Materialized view** for the rollup + **BI Engine** for in-memory serving.
4. **10 years of daily data — you hit a partition limit. Fix?** → 3,650 daily partitions
   is under 4,000 but close; partition by **month** or apply `partition_expiration_days`.
5. **Workload is steady at 8 TB scanned/day; how to make cost predictable?** → Move from
   on-demand to **Editions / committed slots**.

---

## Key Takeaways
- **Partition** (coarse, low-cardinality time) + **cluster** (fine, high-cardinality
  filters) = dramatic bytes-scanned reduction.
- Guardrails: `require_partition_filter`, `maximum_bytes_billed`, partition expiration,
  dry runs.
- **On-demand** for spiky; **Editions/commitments** for steady, high-volume.
- Accelerate reads with **materialized views, BI Engine, search indexes**.

Next: [Module 5 — Choosing the Right Database](../module_05_choosing_a_database/README.md).

---

## Files in This Module
- `concepts.tf` — a partitioned + clustered table and a materialized view
- `optimize.sql` — tuning queries, dry runs, INFORMATION_SCHEMA cost analysis
- `exercise.md` — redesign a slow table for scale
- `solution.tf` / `solution.sql` — reference solution
