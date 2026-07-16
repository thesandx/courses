-- ===========================================================================
-- Module 11 Solution — Forecast Demand with BigQuery ML (ARIMA_PLUS)
--   bq query --use_legacy_sql=false < solution.sql
--
-- TODO 5: ARIMA_PLUS is correct because this is UNIVARIATE TIME-SERIES
-- FORECASTING with trend + seasonality. LINEAR_REG ignores autocorrelation/
-- seasonality; KMEANS is unsupervised clustering, not forecasting.
-- ===========================================================================

CREATE SCHEMA IF NOT EXISTS ml;

-- TODO 1 — ~90 days of synthetic seasonal daily sales.
CREATE OR REPLACE TABLE ml.daily_sales AS
SELECT
  d AS sale_date,
  -- trend + weekly seasonality + noise
  500
    + 3 * DATE_DIFF(d, DATE '2026-01-01', DAY)
    + 80 * SIN(2 * ACOS(-1) * EXTRACT(DAYOFWEEK FROM d) / 7)
    + 20 * RAND() AS revenue
FROM UNNEST(GENERATE_DATE_ARRAY(DATE '2026-01-01', DATE '2026-03-31')) AS d;

-- TODO 2 — train ARIMA_PLUS; auto seasonality detection.
CREATE OR REPLACE MODEL ml.sales_forecast
OPTIONS(
  model_type                = 'ARIMA_PLUS',
  time_series_timestamp_col = 'sale_date',
  time_series_data_col      = 'revenue',
  auto_arima                = TRUE,
  data_frequency            = 'DAILY',
  holiday_region            = 'US'        -- Stretch #1: holiday effects
) AS
SELECT sale_date, revenue FROM ml.daily_sales;

-- TODO 3 — inspect the chosen ARIMA terms + fit stats.
SELECT * FROM ML.ARIMA_EVALUATE(MODEL ml.sales_forecast);

-- TODO 4 — 30-day forecast with 80% confidence bounds.
SELECT
  forecast_timestamp,
  ROUND(forecast_value, 2)       AS forecast_revenue,
  ROUND(prediction_interval_lower_bound, 2) AS lo,
  ROUND(prediction_interval_upper_bound, 2) AS hi
FROM ML.FORECAST(MODEL ml.sales_forecast,
                 STRUCT(30 AS horizon, 0.8 AS confidence_level))
ORDER BY forecast_timestamp;
