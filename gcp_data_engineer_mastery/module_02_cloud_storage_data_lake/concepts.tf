###############################################################################
# Module 2: Cloud Storage & Data Lakes — Concepts in Action
#
# Demonstrates: lakehouse-zoned buckets, storage-class lifecycle tiering,
#               object versioning, uniform bucket-level access.
# Apply: terraform init && terraform apply -var project_id=YOUR_PROJECT
###############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
    random = { source = "hashicorp/random", version = ">= 3.0" }
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

# Bucket names are globally unique — suffix keeps the example collision-free.
resource "random_id" "suffix" {
  byte_length = 3
}

# ---------------------------------------------------------------------------
# RAW zone: as-ingested, immutable. Versioning protects against bad overwrites;
# a lifecycle rule expires noncurrent versions after 30 days.
# ---------------------------------------------------------------------------
resource "google_storage_bucket" "raw" {
  name                        = "${var.project_id}-lake-raw-${random_id.suffix.hex}"
  location                    = var.region # colocate with compute + BigQuery
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true # UBLA: IAM only, no ACLs
  force_destroy               = true # course-only convenience

  versioning { enabled = true }

  # Tier cold data down, then expire it.
  lifecycle_rule {
    condition { age = 30 }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  lifecycle_rule {
    condition { age = 90 }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  # Expire old (noncurrent) versions so versioning doesn't grow unbounded.
  lifecycle_rule {
    condition {
      age                = 30
      with_state         = "ARCHIVED" # i.e. noncurrent versions
      num_newer_versions = 3
    }
    action { type = "Delete" }
  }
}

# ---------------------------------------------------------------------------
# CURATED zone: cleaned, columnar output of ETL. Autoclass handles tiering
# automatically based on access (mutually exclusive with class lifecycle rules).
# ---------------------------------------------------------------------------
resource "google_storage_bucket" "curated" {
  name                        = "${var.project_id}-lake-curated-${random_id.suffix.hex}"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  autoclass { enabled = true }
}

output "raw_bucket" { value = google_storage_bucket.raw.url }
output "curated_bucket" { value = google_storage_bucket.curated.url }
