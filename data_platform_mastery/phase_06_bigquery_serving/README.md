# Phase 06 — BigQuery Serving: FDP→CDP, the Dim/Fact Builder (`v0.6.0`)

> **Mission:** build the consumption layer. A template-driven **Dim/Fact Builder**
> (the "accelerator" from the reference architecture) turns FDP into CDP star
> schemas, pre-aggregated rollups, and data products — partitioned, clustered,
> cost-measured, and idempotent. This is the phase where the data finally earns
> its keep.

## 1. Concepts

Read notes **§6 (data model design)**, **§11 (partitioning)**, **§15 (cost)**;
GCP **M03/M04 (BigQuery fundamentals & at scale)**.

**Grain first, always (§6).** Before any DDL, say it out loud and write it in the
model's YAML: *"one row in `fct_order_lines` = one order line item."* Undeclared
grain = double-counted revenue when someone joins to `dim_products`.

**The CDP is a set of data products, not "the gold dataset".** Each product has an
owner, an SLA, a declared grain, documented columns, and a freshness stamp — the
"data as a product" pillar of Data Mesh (§25), implemented small. Enterprise
architectures call this layer CDP (Consumption Data Products); Databricks calls it
gold; Kimball calls it the presentation layer. Same thing — say all three names.

**Model set for NovaMart** (star schema, §6's default):

```
fct_order_lines   grain: one order line       PK: order_line_sk
                  FKs: customer_sk (SCD2 as-of!), product_sk, date_key
                  measures: quantity, unit_price_usd, line_amount_usd, line_amount_local
fct_sessions      grain: one browsing session (from Phase 5 sessionize)
dim_customers     SCD2 (from Phase 5) — query pattern: WHERE is_current, or as-of join
dim_products      SCD1 (overwrite — corrections only, no history requirement)
dim_date          generated calendar
agg_daily_revenue grain: one day × product_category — the dashboard rollup
```

**The as-of join (§17 late-arriving-fact pattern)** — facts must pick the dimension
version that was true *at event time*, not now:

```sql
JOIN `fdp.dim_customers` c
  ON o.customer_id = c.customer_id
 AND o.order_ts >= c.effective_from AND o.order_ts < c.effective_to
```

**Cost engineering is part of the design (§15, M04):**
- `PARTITION BY DATE(order_ts)` + `CLUSTER BY product_sk, customer_sk` (≤4 cols).
- `require_partition_filter = true` on big facts — a guardrail, not a suggestion.
- Rollups exist so dashboards never scan raw facts: one daily aggregate serving 50
  dashboard queries is the single biggest saving in most real platforms (§15's ~$4.6K example).
- Measure everything with `--dry_run` bytes-scanned before/after; keep the numbers.

## 2. Build

### 2.1 Terraform: the CDP datasets

`bigquery` module additions: datasets `fdp`, `fdp_staging`, `cdp`; default table
expiration on `fdp_staging` (3 days — staging is disposable); `cdp` labeled
`layer=cdp, owner=analytics`. Authorized views come in Phase 9.

### 2.2 The Dim/Fact Builder — `src/pipeforge/serving/`

Transform-as-config, same philosophy as ingestion. Each model is a YAML + SQL pair:

`serving/models/fct_order_lines.yaml`:

```yaml
name: fct_order_lines
layer: cdp
grain: one row per order line item
owner: analytics@novamart.dev
sla_freshness_minutes: 360
partition_field: order_date
clustering: [product_sk, customer_sk]
write_mode: partition_overwrite         # or: merge | full_refresh
depends_on: [fdp.orders, fdp.dim_customers, fdp.dim_products, fdp.fx_rates]
tests:                                   # consumed by Phase 8 DQ engine
  - {type: unique, columns: [order_line_sk], severity: block}
  - {type: not_null, columns: [customer_sk, product_sk], severity: block}
  - {type: reconciles_to, source: fdp.orders, measure: "SUM(line_amount_usd)", tolerance_pct: 0.1}
```

`serving/models/fct_order_lines.sql.j2`:

```sql
SELECT
  {{ sk(['o.order_line_id']) }}               AS order_line_sk,
  c.sk                                         AS customer_sk,   -- as-of SCD2 join below
  p.sk                                         AS product_sk,
  DATE(o.order_ts)                             AS order_date,
  o.quantity,
  o.unit_price_usd,
  o.quantity * o.unit_price_usd                AS line_amount_usd,
  o.quantity * o.unit_price_usd * fx.rate      AS line_amount_local
FROM `{{ project }}.fdp.orders` o
JOIN `{{ project }}.fdp.dim_customers` c
  ON o.customer_id = c.customer_id
 AND o.order_ts >= c.effective_from AND o.order_ts < c.effective_to
JOIN `{{ project }}.fdp.dim_products` p
  ON o.product_id = p.product_id AND p.is_current
LEFT JOIN `{{ project }}.fdp.fx_rates` fx
  ON DATE(o.order_ts) = fx.rate_date AND fx.currency = 'EUR'
WHERE DATE(o.order_ts) BETWEEN DATE('{{ ds }}') - {{ lookback }} AND DATE('{{ ds }}')
```

`builder.py` renders the template, then executes idempotently by `write_mode`:

```python
def run_model(model: Model, execution_date: str) -> None:
    sql = render(model, ds=execution_date, lookback=model.lookback_days)
    if model.write_mode == "partition_overwrite":
        # MERGE-free idempotency for facts (§7 pattern 1):
        job = bq.query(f"""
          DECLARE d_start DATE DEFAULT DATE('{execution_date}') - {model.lookback_days};
          DELETE `{model.fqn}` WHERE {model.partition_field} BETWEEN d_start AND '{execution_date}';
          INSERT `{model.fqn}` {sql};
        """, job_config=QueryJobConfig(
            maximum_bytes_billed=model.max_bytes_billed))   # the cost seatbelt, always on
    ...
    emit_audit(...)  # rows, bytes_billed, slot_ms -> pipeline_run
```

(Yes, `MERGE`/`INSERT OVERWRITE`-style alternatives exist; implementing
delete+insert in one script and merge for dims means you've personally used all
three §7 idempotency patterns. Say so.)

CLI: `pipeforge build --model fct_order_lines --execution-date 2026-07-15`, plus
`--select cdp.*` to run a whole layer in dependency order (topo-sort `depends_on` —
a 20-line DAG resolver you'll reuse in Phase 7).

### 2.3 dim_date + rollups

- `dim_date`: one-off generated `GENERATE_DATE_ARRAY` script (2020→2030).
- `agg_daily_revenue`: partition-overwrite model over `fct_order_lines`.
- One **materialized view** for a "live-ish" metric (revenue today) — know its
  constraints (limited SQL surface, auto-refresh economics) vs the rollup table (M04).

### 2.4 Prove the cost model (do not skip)

```bash
bq query --dry_run --use_legacy_sql=false \
  'SELECT SUM(line_amount_usd) FROM cdp.fct_order_lines'                        # full scan
bq query --dry_run --use_legacy_sql=false \
  'SELECT SUM(line_amount_usd) FROM cdp.fct_order_lines WHERE order_date = "2026-07-15"'  # pruned
```

Record both byte counts in `docs/adr/0003-cdp-design.md`, compute the ratio, and
multiply to a 2 TB/day production table at $6.25/TB — *that* number is your §15
interview ammunition. Then flip `require_partition_filter=true` and watch the
first query get **rejected** — the guardrail in action.

### 2.5 Ship it

Tests: template rendering, topo-sort ordering, delete+insert window math
(lookback), as-of join on a crafted SCD2 fixture (customer changes tier mid-month;
orders before/after pick different versions). Tag `v0.6.0`.

## 3. Prove it

- [ ] `SELECT COUNT(*) FROM cdp.fct_order_lines GROUP BY order_line_sk HAVING COUNT(*)>1` → empty, even after running the same date 3 times
- [ ] Tier-change customer: July-1 order shows old tier, July-15 order shows new tier (SCD2 as-of works)
- [ ] Revenue in `agg_daily_revenue` == revenue in `fct_order_lines` == manifest-based source estimate within tolerance (recon preview)
- [ ] Unfiltered query on the fact table is **rejected** by `require_partition_filter`
- [ ] Bytes-billed for the dashboard query dropped ≥ 10x via the rollup (documented)

## 4. Break it

Change the as-of join to the naive `AND c.is_current` (what most juniors write),
rebuild a historical date, and diff revenue-by-tier against the correct version.
Quantify the misstatement. This is your concrete story for "why does SCD2 matter?"
— restore, then write `docs/incidents/006-current-flag-join.md`.

## 5. Interview corner

- Run the full **Q3 (e-commerce warehouse — the most-asked question)** with a 45-min
  timer. You have now *built* the canonical answer: declare grain → star schema →
  SCD2 dims → idempotent daily loads → rollups → cost numbers.
- *"Star schema or OBT?"* — you chose star; know when OBT wins (single predictable
  dashboard, §6) and mention wide-fact pragmatism.
- dbt fluency without dbt (§32): your YAML+Jinja+`depends_on`+tests **is** dbt's
  mental model — `ref()` ≈ `depends_on`, materializations ≈ `write_mode`, dbt tests
  ≈ your `tests:` block. Being able to map them shows you understand the concepts,
  not the tool branding. (Stretch: port two models to real dbt and compare.)

## 6. Stretch goals

- Port `fct_order_lines` + `agg_daily_revenue` to **dbt** with contracts + tests; run both side by side.
- Add a BI Engine reservation + Looker Studio dashboard on the rollup (M11).
- Feature-store flavor: build `cdp.customer_features` (RFM metrics) and discuss offline/online split (Q8).
