-- ===========================================================================
-- Module 3: BigQuery Fundamentals — Concepts in Action (GoogleSQL)
--   Run in the BigQuery console or:  bq query --use_legacy_sql=false < queries.sql
--   Replace `analytics` with your dataset if different.
-- ===========================================================================

-- 1. DDL: create a native table from a schema (idempotent).
CREATE TABLE IF NOT EXISTS analytics.customers (
  customer_id STRING NOT NULL,
  country     STRING,
  created_at  TIMESTAMP
);

-- 2. Batch load is free — but you can also insert from a query (transform + write).
INSERT INTO analytics.customers (customer_id, country, created_at)
VALUES ('c1', 'US', CURRENT_TIMESTAMP()),
       ('c2', 'DE', CURRENT_TIMESTAMP());

-- 3. Nested/repeated data: explode an ARRAY<STRUCT> with UNNEST to line-items.
--    NOTE the correlated cross join `, UNNEST(items)`.
SELECT
  o.order_id,
  o.customer.country            AS country,   -- STRUCT field access
  item.sku,
  item.qty * item.price         AS line_total
FROM analytics.orders AS o, UNNEST(o.items) AS item;

-- 4. Re-nest / aggregate back into an array with ARRAY_AGG.
SELECT
  customer.country AS country,
  ARRAY_AGG(order_id) AS order_ids,
  COUNT(*) AS n_orders
FROM analytics.orders
GROUP BY country;

-- 5. Cost-aware query: name columns (never SELECT *) and estimate bytes with a dry run:
--    bq query --dry_run --use_legacy_sql=false 'SELECT order_id FROM analytics.orders'
SELECT order_id, order_ts
FROM analytics.orders
WHERE order_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);

-- 6. External/BigLake table: query GCS files in place, no load required.
SELECT COUNT(*) AS events
FROM analytics.raw_events_ext;
