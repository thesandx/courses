###############################################################################
# bigquery.tf — Datasets, partitioned+clustered tables, MV, BI Engine, and a
#               CMEK-encrypted raw table (Modules 3, 4, 10, 11)
###############################################################################

# Raw landing dataset — CMEK-encrypted (key defined in governance.tf).
resource "google_bigquery_dataset" "rideshare" {
  dataset_id                 = "rideshare"
  location                   = var.region
  delete_contents_on_destroy = true
  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.bq.id
  }
  depends_on = [google_kms_crypto_key_iam_member.bq_use]
}

# Partitioned by day, clustered by the columns we filter on (Module 4).
resource "google_bigquery_table" "trips_raw" {
  dataset_id          = google_bigquery_dataset.rideshare.dataset_id
  table_id            = "trips_raw"
  deletion_protection = false

  schema = jsonencode([
    { name = "trip_id", type = "STRING", mode = "REQUIRED" },
    { name = "driver_id", type = "STRING" },
    { name = "rider_id", type = "STRING" },
    { name = "fare_cents", type = "INT64" },
    { name = "lat", type = "FLOAT64" },
    { name = "lng", type = "FLOAT64" },
    { name = "event_ts", type = "TIMESTAMP", mode = "REQUIRED" },
  ])

  require_partition_filter = true # top-level (block-level field is deprecated)
  time_partitioning {
    type          = "DAY"
    field         = "event_ts"
    expiration_ms = 15552000000 # 180 days
  }
  clustering = ["driver_id", "rider_id"]
}

# Curated + marts datasets.
resource "google_bigquery_dataset" "curated" {
  dataset_id                 = "rideshare_curated"
  location                   = var.region
  delete_contents_on_destroy = true
}
resource "google_bigquery_dataset" "marts" {
  dataset_id                 = "rideshare_marts"
  location                   = var.region
  delete_contents_on_destroy = true
}
resource "google_bigquery_dataset" "ml" {
  dataset_id                 = "rideshare_ml"
  location                   = var.region
  delete_contents_on_destroy = true
}

# Materialized view: hourly revenue per driver, auto-refreshed (Module 4).
resource "google_bigquery_table" "hourly_revenue_mv" {
  dataset_id          = google_bigquery_dataset.marts.dataset_id
  table_id            = "hourly_revenue_mv"
  deletion_protection = false
  materialized_view {
    enable_refresh      = true
    refresh_interval_ms = 1800000
    query               = <<-SQL
      SELECT TIMESTAMP_TRUNC(event_ts, HOUR) AS hour, driver_id,
             SUM(fare_cents) AS revenue_cents, COUNT(*) AS trips
      FROM `${var.project_id}.rideshare.trips_raw`
      GROUP BY hour, driver_id
    SQL
  }
  depends_on = [google_bigquery_table.trips_raw]
}

# BI Engine acceleration for Looker Studio dashboards (Module 11).
resource "google_bigquery_bi_reservation" "bi" {
  location = var.region
  size     = 1073741824 # 1 GiB
}
