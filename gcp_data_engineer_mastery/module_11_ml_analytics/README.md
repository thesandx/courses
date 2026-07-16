# Module 11: ML & Analytics Integration

## Learning Objectives
- Build, evaluate, and predict with **BigQuery ML** models using pure SQL.
- Know **which model type** fits which problem and when to use **AutoML / Vertex AI**
  instead of BQML.
- Serve features and predictions to **Vertex AI** and understand training/serving skew.
- Present results with **Looker / Looker Studio** and **BI Engine**.
- Recognize the exam's ML-on-GCP decision points.

---

## 1. BigQuery ML — ML Where the Data Lives

Train models with `CREATE MODEL` — no data movement, no infra. Great when your data is
already in BigQuery and the model type is supported.

```sql
CREATE OR REPLACE MODEL ml.churn
OPTIONS(model_type='LOGISTIC_REG', input_label_cols=['churned']) AS
SELECT tenure_months, monthly_spend, support_tickets, churned
FROM ml.customers;
```

| Function | Purpose |
|----------|---------|
| `ML.EVALUATE` | Metrics (AUC, precision, RMSE…) |
| `ML.PREDICT` | Score new rows |
| `ML.EXPLAIN_PREDICT` | Feature attributions |
| `TRANSFORM(...)` | Bake feature engineering into the model (no serving skew) |

## 2. Choosing a Model Type

| Problem | BQML model_type |
|---------|-----------------|
| Binary/multiclass classification | `LOGISTIC_REG`, `BOOSTED_TREE_CLASSIFIER`, `DNN_CLASSIFIER` |
| Regression | `LINEAR_REG`, `BOOSTED_TREE_REGRESSOR` |
| Clustering | `KMEANS` |
| Forecasting | `ARIMA_PLUS` |
| Recommendation | `MATRIX_FACTORIZATION` |
| Deep/AutoML | `DNN_*`, `AUTOML_CLASSIFIER/REGRESSOR` |
| Use a remote LLM | `CREATE MODEL ... REMOTE WITH CONNECTION` (Vertex endpoint) |

> **Exam tip:** demand forecasting → **ARIMA_PLUS**; customer segmentation → **KMEANS**;
> product recs → **MATRIX_FACTORIZATION**.

## 3. BQML vs AutoML vs Custom Vertex AI

| Approach | Use when |
|----------|----------|
| **BigQuery ML** | Data in BQ, standard model, SQL team, fast iteration |
| **AutoML (Vertex)** | Need high accuracy with little ML code, images/text/tabular |
| **Custom training (Vertex)** | Custom frameworks (TF/PyTorch), full control, large-scale DL |
| **Pre-trained APIs** | Vision/Speech/NL/Translation — don't train at all |

> **Trap:** don't build a model when a **pre-trained API** (Vision, Document AI, Natural
> Language) already solves it.

## 4. Vertex AI Integration & Serving Skew

- Export BQML models to **Vertex AI** for online serving, or register/monitor them.
- **Vertex Feature Store** serves consistent features to training *and* online inference —
  prevents **training/serving skew** (features computed differently in each path).
- **Vertex Pipelines** orchestrate ML workflows; **Model Monitoring** watches for drift.

> **Exam tip:** "features differ between training and production" = **training/serving
> skew** → use a **Feature Store** / shared transformation (`TRANSFORM` in BQML).

## 5. Serving Analytics: Looker & BI Engine

| Tool | Role |
|------|------|
| **Looker** | Governed semantic layer (LookML), enterprise BI, embedded analytics |
| **Looker Studio** | Free, self-serve dashboards on BigQuery & others |
| **BI Engine** | In-memory acceleration for sub-second dashboard queries |
| **Connected Sheets** | Analyze BigQuery from Google Sheets, no SQL |

---

## 🎯 Exam Focus

| Scenario | Answer |
|----------|--------|
| "Predict churn, data already in BigQuery, SQL team" | **BigQuery ML** (`LOGISTIC_REG`/boosted tree) |
| "Forecast next quarter demand" | BQML **ARIMA_PLUS** |
| "Segment customers" | BQML **KMEANS** |
| "Recommend products" | BQML **MATRIX_FACTORIZATION** |
| "Detect objects in images" | **Vision API** (pre-trained) — don't train |
| "High-accuracy tabular model, little ML code" | **AutoML Tabular** (Vertex) |
| "Features differ train vs serve" | **Feature Store** / `TRANSFORM` to fix skew |
| "Sub-second executive dashboards on BQ" | **Looker/Looker Studio + BI Engine** |

### Practice Questions
1. **Churn prediction on data already in BigQuery, team knows SQL not Python.** →
   **BigQuery ML** logistic regression / boosted tree — no data movement.
2. **Forecast daily sales for the next 30 days.** → BQML **ARIMA_PLUS**.
3. **Group customers into unlabeled segments.** → BQML **KMEANS** (unsupervised).
4. **Classify support images of damaged parts.** → **Vertex AutoML Vision** or the
   pre-trained **Vision API** if generic labels suffice.
5. **Model works in training but is wrong in production because features are computed
   differently.** → **Training/serving skew** → use **Vertex Feature Store** / bake
   features into `TRANSFORM`.
6. **Executives need sub-second dashboards over a huge BigQuery table.** → **Looker (or
   Looker Studio) with BI Engine**.

---

## Key Takeaways
- **BQML** brings ML to the data with SQL; pick the `model_type` from the problem
  (ARIMA_PLUS/KMEANS/MATRIX_FACTORIZATION are common exam answers).
- Escalate to **AutoML** for accuracy-with-little-code, **custom Vertex** for full
  control, **pre-trained APIs** when they already solve it.
- Prevent **training/serving skew** with a Feature Store or `TRANSFORM`.
- Serve insights with **Looker/Looker Studio** accelerated by **BI Engine**.

Next: [Module 12 — Reliability, Monitoring & Cost](../module_12_reliability_cost/README.md).

---

## Files in This Module
- `concepts.sql` — train/evaluate/predict a churn model + a KMEANS segmentation in BQML
- `concepts.tf` — a BI Engine reservation and a BQML-backed dataset
- `exercise.md` — build and evaluate a forecasting model
- `solution.sql` — reference solution
