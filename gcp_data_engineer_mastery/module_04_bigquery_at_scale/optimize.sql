-- ===========================================================================
-- Module 4: BigQuery at Scale — Tuning & Cost Analysis
--   bq query --use_legacy_sql=false < optimize.sql
-- ===========================================================================

-- 1. GOOD: hits one partition + clustered columns -> tiny scan.
SELECT customer_id, SUM(amount) AS spend
FROM analytics_scale.events
WHERE event_ts >= TIMESTAMP('2026-07-01')     -- partition prune
  AND event_ts <  TIMESTAMP('2026-07-02')
  AND customer_id = 'c-123'                     -- cluster prune
GROUP BY customer_id;

-- 2. BAD (would ERROR): no partition filter on a require_partition_filter table.
-- SELECT COUNT(*) FROM analytics_scale.events;   -- rejected: needs a partition predicate

-- 3. Estimate cost BEFORE running (dry run from CLI):
--    bq query --dry_run --use_legacy_sql=false \
--      'SELECT customer_id FROM analytics_scale.events WHERE event_ts >= TIMESTAMP("2026-07-01")'
--    -> prints bytes that WOULD be processed; 0 cost.

-- 4. Cap accidental spend at the query level:
--    bq query --maximum_bytes_billed=1000000000 --use_legacy_sql=false '...'

-- 5. Find the most expensive queries (drive tuning decisions):
SELECT
  job_id,
  ROUND(total_bytes_billed / POW(1024, 4), 3) AS tib_billed,
  total_slot_ms,
  SUBSTR(query, 0, 80) AS query_head
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  AND statement_type = 'SELECT'
ORDER BY total_bytes_billed DESC
LIMIT 10;

-- 6. Verify the materialized view is being used: run a base-table query that matches
--    the MV shape and check the query plan for "materialized view" substitution.
SELECT DATE(event_ts) AS day, SUM(amount) AS revenue
FROM analytics_scale.events
WHERE event_ts >= TIMESTAMP('2026-07-01')
GROUP BY day;
