# Module 11 Exercise: Forecast Demand with BigQuery ML

## Goal
Build a **time-series forecast** of daily sales entirely in SQL with BigQuery ML
(`ARIMA_PLUS`), evaluate it, and produce a 30-day forecast — the exact pattern the exam
uses for "forecast future demand."

## Tasks
Run in BigQuery (or `bq query`). Reference `solution.sql` after attempting.

### TODO 1 — Training data
Create `ml.daily_sales(sale_date DATE, revenue FLOAT64)` and populate ~60+ days of data
(generate with `GENERATE_DATE_ARRAY` + a seasonal formula, or use your own).

### TODO 2 — Train an ARIMA_PLUS model
`CREATE MODEL ml.sales_forecast` with `model_type='ARIMA_PLUS'`,
`time_series_timestamp_col='sale_date'`, `time_series_data_col='revenue'`. Let it
auto-detect seasonality.

### TODO 3 — Inspect the fit
Use `ML.ARIMA_EVALUATE` to see the chosen (p,d,q) + seasonal terms and AIC.

### TODO 4 — Forecast 30 days
Use `ML.FORECAST(MODEL ml.sales_forecast, STRUCT(30 AS horizon, 0.8 AS confidence_level))`.

### TODO 5 — Which model type?
In a comment, state why `ARIMA_PLUS` (not `LINEAR_REG` or `KMEANS`) is correct here.

## Self-Verification
```bash
bq query --use_legacy_sql=false < answers.sql

# The model exists and is ARIMA_PLUS:
bq query --use_legacy_sql=false \
  "SELECT model_type FROM ml.INFORMATION_SCHEMA.MODELS WHERE model_name='sales_forecast'"
#   → ARIMA_PLUS

# The forecast returns 30 future rows with confidence bounds:
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM ML.FORECAST(MODEL ml.sales_forecast, STRUCT(30 AS horizon, 0.8 AS confidence_level))"
#   → 30
```

## Stretch Goals
1. Add holiday effects with the `holiday_region` option and compare accuracy.
2. Build a **Looker Studio** dashboard on the forecast with a BI Engine reservation.
3. Compare against a `BOOSTED_TREE_REGRESSOR` using lagged features and discuss tradeoffs.

## Cleanup
```bash
bq rm -f -m $PROJECT_ID:ml.sales_forecast
bq rm -f -t $PROJECT_ID:ml.daily_sales
```
