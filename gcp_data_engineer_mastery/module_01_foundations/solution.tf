###############################################################################
# Module 1 Solution — Project Baseline
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

# TODO 2 — enable APIs
resource "google_project_service" "apis" {
  for_each           = toset(["bigquery.googleapis.com", "storage.googleapis.com"])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# TODO 3 — analytics reader SA
resource "google_service_account" "reader" {
  project      = var.project_id
  account_id   = "analytics-reader"
  display_name = "Read-only analytics identity"
}

# TODO 4 — least-privilege, additive bindings (Stretch #2: single for_each)
resource "google_project_iam_member" "reader" {
  for_each = toset(["roles/bigquery.dataViewer", "roles/bigquery.jobUser"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.reader.email}"
}

# Stretch #1 — Deny policy: block bucket deletion regardless of any allow grant.
# IAM Deny policies attach to the resource-manager resource, not the project IAM policy.
resource "google_iam_deny_policy" "no_bucket_delete" {
  parent   = urlencode("cloudresourcemanager.googleapis.com/projects/${var.project_id}")
  name     = "deny-bucket-delete"
  provider = google

  rules {
    deny_rule {
      denied_principals  = ["principalSet://goog/serviceAccount/${google_service_account.reader.email}"]
      denied_permissions = ["storage.googleapis.com/buckets.delete"]
    }
  }
}

# TODO 5
output "reader_sa_email" {
  value = google_service_account.reader.email
}
