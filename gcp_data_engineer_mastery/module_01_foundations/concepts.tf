###############################################################################
# Module 1: Foundations — Concepts in Action
#
# Demonstrates: enabling data-platform APIs, a least-privilege pipeline service
#               account, and additive (safe) IAM bindings.
#
# Apply:   terraform init && terraform apply -var project_id=YOUR_PROJECT
# Inspect: terraform plan   (see exactly what would change)
# Destroy: terraform destroy -var project_id=YOUR_PROJECT
###############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

variable "project_id" {
  type        = string
  description = "Target GCP project."
}

variable "region" {
  type    = string
  default = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# 1. Enable the APIs the whole course needs.
#    disable_on_destroy=false so `terraform destroy` doesn't rip APIs out from
#    under other resources that may still be settling.
# ---------------------------------------------------------------------------
locals {
  data_apis = [
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "dataflow.googleapis.com",
    "dataproc.googleapis.com",
    "composer.googleapis.com",
    "iam.googleapis.com",
  ]
}

resource "google_project_service" "enabled" {
  for_each           = toset(local.data_apis)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# 2. A dedicated pipeline identity. Automation should NEVER run as a human
#    or as the default (over-privileged) service account.
# ---------------------------------------------------------------------------
resource "google_service_account" "pipeline" {
  project      = var.project_id
  account_id   = "data-pipeline"
  display_name = "Data pipeline (least-privilege automation)"
}

# ---------------------------------------------------------------------------
# 3. Least-privilege bindings. Note the split: jobUser lets it RUN queries,
#    dataEditor lets it write results — but it is NOT project Editor/Owner.
#    google_project_iam_member is ADDITIVE (safe in shared projects).
# ---------------------------------------------------------------------------
locals {
  pipeline_roles = [
    "roles/bigquery.jobUser",     # run query/load jobs
    "roles/bigquery.dataEditor",  # write to datasets it owns
    "roles/storage.objectViewer", # read source files
  ]
}

resource "google_project_iam_member" "pipeline" {
  for_each = toset(local.pipeline_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.pipeline.email}"
}

output "pipeline_sa_email" {
  description = "Attach this SA to Dataflow/Dataproc/Composer in later modules."
  value       = google_service_account.pipeline.email
}
