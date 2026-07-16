###############################################################################
# Module 2 Solution — Tiered Data Lake
#   terraform init && terraform apply -var project_id=YOUR_PROJECT
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

resource "random_id" "suffix" { byte_length = 3 }

# TODO 2 — raw bucket
resource "google_storage_bucket" "raw" {
  name                        = "${var.project_id}-lake-raw-${random_id.suffix.hex}"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced" # TODO 4
  versioning { enabled = true }
  force_destroy = true

  lifecycle_rule {
    condition { age = 90 }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  lifecycle_rule {
    condition { age = 400 }
    action { type = "Delete" }
  }

  # Stretch #1 — clean up dangling uploads
  lifecycle_rule {
    condition { age = 7 }
    action { type = "AbortIncompleteMultipartUpload" }
  }
}

# TODO 3 — compliance bucket with retention policy
resource "google_storage_bucket" "compliance" {
  name                        = "${var.project_id}-compliance-${random_id.suffix.hex}"
  location                    = var.region
  storage_class               = "ARCHIVE"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  retention_policy {
    retention_period = 2592000 # 30 days, in seconds
    # is_locked = true         # IRREVERSIBLE — leave commented for the lab
  }
  # NOTE: with a retention policy, objects can't be deleted before expiry, so
  # force_destroy will fail while objects are locked — expected behavior.
}

# Stretch #2 — Autoclass bucket. Autoclass manages CLASS transitions, so you must
# NOT also add SetStorageClass lifecycle rules here (mutually exclusive).
resource "google_storage_bucket" "curated" {
  name                        = "${var.project_id}-lake-curated-${random_id.suffix.hex}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  autoclass { enabled = true }
}

output "raw_bucket" { value = google_storage_bucket.raw.url }
output "compliance_bucket" { value = google_storage_bucket.compliance.url }
