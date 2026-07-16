###############################################################################
# Module 9: Cloud Composer — Concepts in Action
#
# Demonstrates: a small Cloud Composer 2 (managed Airflow) environment with a
#               dedicated service account. Upload dag.py to the env's DAG bucket.
#
# WARNING: Composer environments bill continuously (~$300+/mo). Create only to
#          practice, and DESTROY promptly.
#
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

# Dedicated least-privilege identity for the Airflow workers.
resource "google_service_account" "composer" {
  account_id   = "composer-worker"
  display_name = "Cloud Composer worker"
}

# Composer's agent needs to act as this SA.
resource "google_project_iam_member" "composer_worker" {
  for_each = toset([
    "roles/composer.worker",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.composer.email}"
}

resource "google_composer_environment" "de" {
  name   = "de-orchestration"
  region = var.region

  config {
    software_config {
      image_version = "composer-2-airflow-2"
      # Ship pipeline config as Airflow variables/env if needed.
      env_variables = {
        DATA_BUCKET = "${var.project_id}-lake-raw"
      }
    }
    node_config {
      service_account = google_service_account.composer.email
    }
    # Smallest preset to minimize cost while practicing.
    workloads_config {
      scheduler {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
        count      = 1
      }
      web_server {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
      }
      worker {
        cpu        = 0.5
        memory_gb  = 2
        storage_gb = 1
        min_count  = 1
        max_count  = 3
      }
    }
    environment_size = "ENVIRONMENT_SIZE_SMALL"
  }
}

# Airflow reads DAGs from this GCS bucket — copy dag.py here:
#   gcloud storage cp dag.py <dag_gcs_prefix>
output "dag_gcs_prefix" {
  value = google_composer_environment.de.config[0].dag_gcs_prefix
}
output "airflow_uri" {
  value = google_composer_environment.de.config[0].airflow_uri
}
