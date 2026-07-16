###############################################################################
# Module 4: BigQuery at Scale — Concepts in Action
#
# Demonstrates: time-partitioning + clustering + partition guardrails, and an
#               incrementally-maintained materialized view.
# Apply: terraform init && terraform apply -var project_id=YOUR_PROJECT
###############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
  }
}

variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_bigquery_dataset" "analytics" {
  dataset_id                 = "analytics_scale"
  location                   = var.region
  delete_contents_on_destroy = true
}

# ---------------------------------------------------------------------------
# Partitioned BY DAY on event_ts, CLUSTERED by the high-cardinality filter cols.
# require_partition_filter blocks accidental full scans.
# ---------------------------------------------------------------------------
resource "google_bigquery_table" "events" {
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "events"
  deletion_protection = false

  schema = jsonencode([
    { name = "event_ts", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING" },
    { name = "sku", type = "STRING" },
    { name = "amount", type = "NUMERIC" },
  ])

  require_partition_filter = true # top-level (block-level field is deprecated)
  time_partitioning {
    type          = "DAY"
    field         = "event_ts"
    expiration_ms = 7776000000 # 90 days
  }

  clustering = ["customer_id", "sku"] # order = most-filtered first
}

# ---------------------------------------------------------------------------
# Materialized view: precomputed daily revenue rollup, auto-refreshed.
# Queries against `events` can be transparently served from this MV.
# ---------------------------------------------------------------------------
resource "google_bigquery_table" "daily_revenue_mv" {
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "daily_revenue_mv"
  deletion_protection = false

  materialized_view {
    enable_refresh      = true
    refresh_interval_ms = 1800000 # 30 min
    query               = <<-SQL
      SELECT
        DATE(event_ts)  AS day,
        customer_id,
        SUM(amount)     AS revenue,
        COUNT(*)        AS n_events
      FROM `${var.project_id}.analytics_scale.events`
      GROUP BY day, customer_id
    SQL
  }

  depends_on = [google_bigquery_table.events]
}
