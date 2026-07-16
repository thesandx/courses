-- ===========================================================================
-- Module 11: BigQuery ML — Concepts in Action
--   bq query --use_legacy_sql=false < concepts.sql
--   (Assumes a dataset `ml` with a `customers` table you can adapt.)
-- ===========================================================================

-- 0. Sample training data (replace with your real table).
CREATE SCHEMA IF NOT EXISTS ml;
CREATE OR REPLACE TABLE ml.customers AS
SELECT * FROM UNNEST([
  STRUCT(12 AS tenure_months, 80.0 AS monthly_spend, 1 AS support_tickets, FALSE AS churned),
  STRUCT( 2, 20.0, 6, TRUE),
  STRUCT(36, 120.0, 0, FALSE),
  STRUCT( 1, 15.0, 9, TRUE),
  STRUCT(24, 95.0, 2, FALSE)
]);

-- 1. CLASSIFICATION with a boosted tree. TRANSFORM bakes feature engineering into
--    the model so training and serving use identical features (no skew).
CREATE OR REPLACE MODEL ml.churn
  TRANSFORM(
    ML.STANDARD_SCALER(monthly_spend) OVER () AS spend_z,
    tenure_months, support_tickets, churned
  )
  OPTIONS(
    model_type       = 'BOOSTED_TREE_CLASSIFIER',
    input_label_cols = ['churned'],
    auto_class_weights = TRUE
  ) AS
SELECT tenure_months, monthly_spend, support_tickets, churned
FROM ml.customers;

-- 2. EVALUATE — AUC, precision, recall, etc.
SELECT * FROM ML.EVALUATE(MODEL ml.churn);

-- 3. PREDICT — score customers; predicted_churned + probabilities returned.
SELECT tenure_months, predicted_churned, predicted_churned_probs
FROM ML.PREDICT(MODEL ml.churn,
  (SELECT tenure_months, monthly_spend, support_tickets FROM ml.customers));

-- 4. EXPLAIN — per-feature attributions for a prediction.
SELECT *
FROM ML.EXPLAIN_PREDICT(MODEL ml.churn,
  (SELECT tenure_months, monthly_spend, support_tickets FROM ml.customers),
  STRUCT(3 AS top_k_features));

-- 5. UNSUPERVISED segmentation with KMEANS (no label column).
CREATE OR REPLACE MODEL ml.segments
  OPTIONS(model_type='KMEANS', num_clusters=3) AS
SELECT tenure_months, monthly_spend, support_tickets FROM ml.customers;

SELECT centroid_id, feature, numerical_value
FROM ML.CENTROIDS(MODEL ml.segments)
ORDER BY centroid_id, feature;
