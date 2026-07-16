###############################################################################
# Module 8 Solution — Serverless Spark ETL + ephemeral cluster
#
# For a SCHEDULED NIGHTLY job, prefer the Serverless BATCH: zero idle cost, no
# cluster sizing. The ephemeral cluster is here to contrast (use it when you need
# notebooks or ecosystem components like HBase/Trino).
#
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

# TODO 3 — Serverless Spark batch (preferred for scheduled ETL)
resource "google_dataproc_batch" "category_revenue" {
  batch_id = "category-revenue"
  location = var.region

  runtime_config { version = "2.2" }
  pyspark_batch {
    main_python_file_uri = "gs://${var.project_id}-lake-raw/jobs/agg.py"
    args = [
      "gs://${var.project_id}-lake-raw/sales",
      "gs://${var.project_id}-lake-curated/category_revenue",
    ]
  }
}

# TODO 4 — ephemeral autoscaling cluster with Spot secondaries (the alternative)
resource "google_dataproc_cluster" "ephemeral" {
  name   = "etl-ephemeral"
  region = var.region

  cluster_config {
    master_config {
      num_instances = 1
      machine_type  = "n2-standard-2"
    }
    worker_config {
      num_instances = 2 # on-demand primaries hold shuffle safely
      machine_type  = "n2-standard-2"
    }
    preemptible_worker_config {
      num_instances  = 2
      preemptibility = "SPOT" # cheap, reclaimable
    }
    lifecycle_config {
      idle_delete_ttl = "1800s" # auto-delete when idle
    }
  }
}

output "batch" { value = google_dataproc_batch.category_revenue.batch_id }
