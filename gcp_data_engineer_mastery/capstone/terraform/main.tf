###############################################################################
# Capstone — RideShare Analytics Platform
# main.tf: providers, APIs, and least-privilege service accounts (Module 1).
###############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    google      = { source = "hashicorp/google", version = ">= 5.0" }
    google-beta = { source = "hashicorp/google-beta", version = ">= 5.0" }
    random      = { source = "hashicorp/random", version = ">= 3.0" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
provider "google-beta" {
  project = var.project_id
  region  = var.region
}

data "google_project" "this" {}

resource "random_id" "suffix" { byte_length = 3 }

# --- Enable every API the platform uses --------------------------------------
locals {
  apis = [
    "bigquery.googleapis.com", "storage.googleapis.com", "pubsub.googleapis.com",
    "dataflow.googleapis.com", "dataproc.googleapis.com", "composer.googleapis.com",
    "bigtable.googleapis.com", "bigtableadmin.googleapis.com",
    "cloudkms.googleapis.com", "datacatalog.googleapis.com",
    "monitoring.googleapis.com", "logging.googleapis.com", "billingbudgets.googleapis.com",
  ]
}
resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# --- Dedicated, least-privilege pipeline identities (Module 1) ---------------
resource "google_service_account" "dataflow" {
  account_id   = "rideshare-dataflow"
  display_name = "RideShare Dataflow worker"
}

resource "google_project_iam_member" "dataflow" {
  for_each = toset([
    "roles/dataflow.worker",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/pubsub.subscriber",
    "roles/bigtable.user",
    "roles/storage.objectAdmin",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dataflow.email}"
}
