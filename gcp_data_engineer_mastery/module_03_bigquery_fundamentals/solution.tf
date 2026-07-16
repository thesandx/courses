###############################################################################
# Module 3 Solution — Events Dataset (infra)
#   terraform init && terraform apply -var project_id=YOUR_PROJECT
#   Then run solution.sql for TODO 3-5.
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

# TODO 1 — dataset
resource "google_bigquery_dataset" "ecommerce" {
  dataset_id                 = "ecommerce"
  location                   = var.region
  delete_contents_on_destroy = true
}

# TODO 2 — nested sessions table
resource "google_bigquery_table" "sessions" {
  dataset_id          = google_bigquery_dataset.ecommerce.dataset_id
  table_id            = "sessions"
  deletion_protection = false

  schema = jsonencode([
    { name = "session_id", type = "STRING", mode = "REQUIRED" },
    { name = "user_id", type = "STRING" },
    { name = "started_at", type = "TIMESTAMP" },
    { name = "pageviews", type = "STRUCT", mode = "REPEATED", fields = [
      { name = "url", type = "STRING" },
      { name = "ts", type = "TIMESTAMP" },
      { name = "dwell_ms", type = "INT64" },
    ] },
  ])
}

output "dataset" { value = google_bigquery_dataset.ecommerce.dataset_id }
