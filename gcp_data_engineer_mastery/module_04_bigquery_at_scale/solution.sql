-- ===========================================================================
-- Module 4 Solution — queries proving the redesign
-- ===========================================================================

-- TODO 4a — GOOD query: single-day partition + clustered host. Small scan.
SELECT path, COUNT(*) AS hits
FROM logs.weblogs
WHERE request_ts >= TIMESTAMP('2026-07-01')
  AND request_ts <  TIMESTAMP('2026-07-02')
  AND host = 'api'
GROUP BY path
ORDER BY hits DESC;

-- TODO 4b — BAD query: no partition predicate. REJECTED because the table sets
-- require_partition_filter = TRUE. This is the guardrail doing its job:
-- SELECT COUNT(*) FROM logs.weblogs;
--   -> Error: Cannot query over table 'logs.weblogs' without a filter over
--      column(s) 'request_ts' that can be used for partition elimination.

-- Stretch #3 — search index for needle lookups on path.
-- CREATE SEARCH INDEX path_idx ON logs.weblogs(path);
-- SELECT * FROM logs.weblogs
-- WHERE request_ts >= TIMESTAMP('2026-07-01') AND SEARCH(path, '/checkout');
