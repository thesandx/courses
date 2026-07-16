-- ===========================================================================
-- Capstone — Marts DDL + fine-grained security (Modules 3, 4, 10)
--   bq query --use_legacy_sql=false < schema.sql
-- ===========================================================================

-- Daily KPI mart, partitioned by date for cheap time-range dashboards.
CREATE TABLE IF NOT EXISTS rideshare_marts.daily_kpis (
  trip_date      DATE    NOT NULL,
  trips          INT64,
  revenue_cents  INT64,
  active_drivers INT64
)
PARTITION BY trip_date
OPTIONS (require_partition_filter = FALSE);

-- Per-region trips view feeding row-level security.
CREATE OR REPLACE VIEW rideshare_marts.trips_by_region AS
SELECT
  DATE(event_ts) AS trip_date,
  IF(lng < -100, 'WEST', 'EAST') AS region,   -- toy region derivation
  COUNT(*) AS trips,
  SUM(fare_cents) AS revenue_cents
FROM rideshare.trips_raw
WHERE event_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY trip_date, region;

-- ROW-LEVEL SECURITY: EMEA analysts see only WEST region rows (Module 10).
-- (Requires the base data to have a region column; shown as the pattern.)
-- CREATE ROW ACCESS POLICY west_only ON rideshare_marts.daily_kpis
-- GRANT TO ('group:west-analysts@example.com')
-- FILTER USING (TRUE);   -- replace with a real region predicate

-- COLUMN-LEVEL SECURITY is applied by attaching the `rider-pii` policy tag
-- (from governance.tf) to rider_id in the trips_raw schema, then granting
-- roles/datacatalog.categoryFineGrainedReader only to compliance.
