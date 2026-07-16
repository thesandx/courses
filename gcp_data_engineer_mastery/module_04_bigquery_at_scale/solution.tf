###############################################################################
# Module 4 Solution — Redesign a Table for Scale
#   terraform init && terraform apply -var project_id=YOUR_PROJECT
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

# TODO 1
resource "google_bigquery_dataset" "logs" {
  dataset_id                 = "logs"
  location                   = var.region
  delete_contents_on_destroy = true
}

# TODO 2 — partition by day, cluster by host+status, guardrails on.
resource "google_bigquery_table" "weblogs" {
  dataset_id          = google_bigquery_dataset.logs.dataset_id
  table_id            = "weblogs"
  deletion_protection = false

  schema = jsonencode([
    { name = "request_ts", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "status", type = "INT64" },
    { name = "host", type = "STRING" },
    { name = "path", type = "STRING" },
    { name = "bytes", type = "INT64" },
  ])

  require_partition_filter = true # top-level (block-level field is deprecated)
  time_partitioning {
    type          = "DAY"
    field         = "request_ts"
    expiration_ms = 2592000000 # 30 days
  }
  clustering = ["host", "status"]
}

# TODO 3 — daily 5xx errors per host.
resource "google_bigquery_table" "errors_mv" {
  dataset_id          = google_bigquery_dataset.logs.dataset_id
  table_id            = "errors_per_host_daily"
  deletion_protection = false

  materialized_view {
    enable_refresh = true
    query          = <<-SQL
      SELECT DATE(request_ts) AS day, host, COUNTIF(status >= 500) AS errors
      FROM `${var.project_id}.logs.weblogs`
      GROUP BY day, host
    SQL
  }
  depends_on = [google_bigquery_table.weblogs]
}
