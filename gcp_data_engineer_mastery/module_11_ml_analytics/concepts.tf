###############################################################################
# Module 11: ML & Analytics — Concepts in Action
#
# Demonstrates: a dataset to hold BQML models and a BI Engine reservation that
#               accelerates dashboards over it (sub-second serving).
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

# Dataset that will hold BQML models (ml.churn, ml.segments) and serving tables.
resource "google_bigquery_dataset" "ml" {
  dataset_id                 = "ml"
  location                   = var.region
  delete_contents_on_destroy = true
}

# ---------------------------------------------------------------------------
# BI Engine reservation: in-memory acceleration for Looker/Looker Studio
# dashboards querying this location. Size = GiB of memory.
# ---------------------------------------------------------------------------
resource "google_bigquery_bi_reservation" "bi" {
  location = var.region
  size     = 1073741824 # 1 GiB (bytes)
}

# A connection to Vertex AI for REMOTE models / LLM inference from BigQuery.
resource "google_bigquery_connection" "vertex" {
  connection_id = "vertex-conn"
  location      = var.region
  cloud_resource {}
}

output "ml_dataset" { value = google_bigquery_dataset.ml.dataset_id }
output "vertex_connection" { value = google_bigquery_connection.vertex.id }
