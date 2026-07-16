###############################################################################
# Module 3: BigQuery Fundamentals — Concepts in Action
#
# Demonstrates: dataset (with location), native table with a nested/repeated
#               schema, and a BigLake external table over GCS.
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

# ---------------------------------------------------------------------------
# 1. Dataset — location is IMMUTABLE. Everything inside must stay in it.
# ---------------------------------------------------------------------------
resource "google_bigquery_dataset" "analytics" {
  dataset_id                 = "analytics"
  location                   = var.region
  description                = "Core analytics dataset"
  delete_contents_on_destroy = true # course-only convenience
}

# ---------------------------------------------------------------------------
# 2. Native table with NESTED (STRUCT) and REPEATED (ARRAY) fields — avoids
#    joins by modeling line-items inline.
# ---------------------------------------------------------------------------
resource "google_bigquery_table" "orders" {
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "orders"
  deletion_protection = false

  schema = jsonencode([
    { name = "order_id", type = "STRING", mode = "REQUIRED" },
    { name = "order_ts", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "customer", type = "STRUCT", mode = "NULLABLE", fields = [
      { name = "id", type = "STRING" },
      { name = "country", type = "STRING" },
    ] },
    { name = "items", type = "STRUCT", mode = "REPEATED", fields = [
      { name = "sku", type = "STRING" },
      { name = "qty", type = "INT64" },
      { name = "price", type = "NUMERIC" },
    ] },
  ])
}

# ---------------------------------------------------------------------------
# 3. Connection + BigLake external table over GCS (governed, no BQ storage).
# ---------------------------------------------------------------------------
resource "google_bigquery_connection" "lake" {
  connection_id = "lake-conn"
  location      = var.region
  cloud_resource {}
}

resource "google_bigquery_table" "raw_events" {
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "raw_events_ext"
  deletion_protection = false

  external_data_configuration {
    autodetect    = true
    source_format = "PARQUET"
    connection_id = google_bigquery_connection.lake.id # BigLake (governed)
    source_uris   = ["gs://${var.project_id}-lake-curated/events/*.parquet"]
  }
}

output "dataset" { value = google_bigquery_dataset.analytics.dataset_id }
