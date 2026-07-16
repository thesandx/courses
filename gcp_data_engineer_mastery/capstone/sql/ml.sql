-- ===========================================================================
-- Capstone — Demand Forecast with BigQuery ML (Module 11)
--   bq query --use_legacy_sql=false < ml.sql
-- ===========================================================================

-- Train an ARIMA_PLUS model on daily trip counts (trend + weekly seasonality).
CREATE OR REPLACE MODEL rideshare_ml.demand
OPTIONS(
  model_type                = 'ARIMA_PLUS',
  time_series_timestamp_col = 'trip_date',
  time_series_data_col      = 'trips',
  data_frequency            = 'DAILY',
  auto_arima                = TRUE,
  holiday_region            = 'US'
) AS
SELECT trip_date, trips
FROM rideshare_marts.daily_kpis
WHERE trips IS NOT NULL;

-- Inspect the fitted model.
SELECT * FROM ML.ARIMA_EVALUATE(MODEL rideshare_ml.demand);

-- 7-day demand forecast with 80% confidence intervals — feeds Looker Studio.
CREATE OR REPLACE TABLE rideshare_marts.demand_forecast AS
SELECT
  forecast_timestamp,
  ROUND(forecast_value) AS forecast_trips,
  ROUND(prediction_interval_lower_bound) AS lo,
  ROUND(prediction_interval_upper_bound) AS hi
FROM ML.FORECAST(MODEL rideshare_ml.demand,
                 STRUCT(7 AS horizon, 0.8 AS confidence_level));
