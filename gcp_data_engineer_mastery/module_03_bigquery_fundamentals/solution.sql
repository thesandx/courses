-- ===========================================================================
-- Module 3 Solution — Events Dataset (queries)
--   bq query --use_legacy_sql=false < solution.sql
-- ===========================================================================

-- TODO 3 — load two sessions, each with multiple pageviews.
INSERT INTO ecommerce.sessions (session_id, user_id, started_at, pageviews)
VALUES
  ('s1', 'u1', CURRENT_TIMESTAMP(), [
     STRUCT('/home'   AS url, CURRENT_TIMESTAMP() AS ts, 1200 AS dwell_ms),
     STRUCT('/search' AS url, CURRENT_TIMESTAMP() AS ts, 3400 AS dwell_ms)
  ]),
  ('s2', 'u2', CURRENT_TIMESTAMP(), [
     STRUCT('/home'    AS url, CURRENT_TIMESTAMP() AS ts,  800 AS dwell_ms),
     STRUCT('/product' AS url, CURRENT_TIMESTAMP() AS ts, 5100 AS dwell_ms),
     STRUCT('/cart'    AS url, CURRENT_TIMESTAMP() AS ts, 2000 AS dwell_ms)
  ]);

-- TODO 4 — one row per pageview (flatten with UNNEST), ordered by dwell.
SELECT s.session_id, pv.url, pv.dwell_ms
FROM ecommerce.sessions AS s, UNNEST(s.pageviews) AS pv
ORDER BY pv.dwell_ms DESC;

-- TODO 5 — per-user aggregate over the exploded array.
SELECT
  s.user_id,
  COUNT(*)          AS pageview_count,
  SUM(pv.dwell_ms)  AS total_dwell_ms
FROM ecommerce.sessions AS s, UNNEST(s.pageviews) AS pv
GROUP BY s.user_id
ORDER BY total_dwell_ms DESC;

-- Stretch #1 — a view of top pages by dwell time.
CREATE OR REPLACE VIEW ecommerce.top_pages AS
SELECT pv.url, SUM(pv.dwell_ms) AS total_dwell_ms
FROM ecommerce.sessions AS s, UNNEST(s.pageviews) AS pv
GROUP BY pv.url
ORDER BY total_dwell_ms DESC
LIMIT 10;
