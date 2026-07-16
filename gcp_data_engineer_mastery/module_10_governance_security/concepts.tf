###############################################################################
# Module 10: Governance & Security — Concepts in Action
#
# Demonstrates: a Cloud KMS key + CMEK-encrypted BigQuery dataset, a Data Catalog
#               policy-tag taxonomy for column-level security, and a Dataplex lake.
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

data "google_project" "this" {}
data "google_bigquery_default_service_account" "bq" {}

# ---------------------------------------------------------------------------
# 1. Cloud KMS key ring + key (CMEK). Rotation controlled by you.
# ---------------------------------------------------------------------------
resource "google_kms_key_ring" "ring" {
  name     = "data-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "bq" {
  name            = "bq-cmek"
  key_ring        = google_kms_key_ring.ring.id
  rotation_period = "7776000s" # 90-day rotation

  lifecycle { prevent_destroy = false } # course-only
}

# The BigQuery service agent MUST be able to use the key.
resource "google_kms_crypto_key_iam_member" "bq_use" {
  crypto_key_id = google_kms_crypto_key.bq.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_bigquery_default_service_account.bq.email}"
}

# ---------------------------------------------------------------------------
# 2. CMEK-encrypted dataset.
# ---------------------------------------------------------------------------
resource "google_bigquery_dataset" "secure" {
  dataset_id                 = "secure"
  location                   = var.region
  delete_contents_on_destroy = true

  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.bq.id
  }
  depends_on = [google_kms_crypto_key_iam_member.bq_use]
}

# ---------------------------------------------------------------------------
# 3. Policy-tag taxonomy for COLUMN-LEVEL security. Attach `pii` to sensitive
#    columns; grant fineGrainedReader only to authorized principals.
# ---------------------------------------------------------------------------
resource "google_data_catalog_taxonomy" "pii" {
  region                 = var.region
  display_name           = "pii-taxonomy"
  activated_policy_types = ["FINE_GRAINED_ACCESS_CONTROL"]
}

resource "google_data_catalog_policy_tag" "pii" {
  taxonomy     = google_data_catalog_taxonomy.pii.id
  display_name = "pii"
  description  = "Attach to columns holding personal data."
}

# ---------------------------------------------------------------------------
# 4. Dataplex lake + a raw zone governing GCS/BigQuery assets.
# ---------------------------------------------------------------------------
resource "google_dataplex_lake" "lake" {
  name     = "analytics-lake"
  location = var.region
}

resource "google_dataplex_zone" "raw" {
  name     = "raw-zone"
  lake     = google_dataplex_lake.lake.name
  location = var.region
  type     = "RAW"

  discovery_spec { enabled = true }
  resource_spec { location_type = "SINGLE_REGION" }
}

output "policy_tag" { value = google_data_catalog_policy_tag.pii.id }
output "kms_key" { value = google_kms_crypto_key.bq.id }
