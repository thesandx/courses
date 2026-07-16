###############################################################################
# Module 10 Solution — Secure a Customer Dataset (CMEK + column-level security)
#   terraform init && terraform apply -var project_id=YOUR_PROJECT -var reader=user:you@example.com
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
variable "reader" {
  type        = string
  description = "Principal allowed to read PII columns, e.g. group:compliance@example.com"
  default     = "user:CHANGE_ME@example.com"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_bigquery_default_service_account" "bq" {}

# TODO 1 — KMS key + grant BQ agent
resource "google_kms_key_ring" "ring" {
  name     = "pii-keyring"
  location = var.region
}
resource "google_kms_crypto_key" "key" {
  name            = "pii-cmek"
  key_ring        = google_kms_key_ring.ring.id
  rotation_period = "7776000s"
}
resource "google_kms_crypto_key_iam_member" "bq_use" {
  crypto_key_id = google_kms_crypto_key.key.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_bigquery_default_service_account.bq.email}"
}

# TODO 3 — taxonomy + policy tag (create before table so we can reference it)
resource "google_data_catalog_taxonomy" "pii" {
  region                 = var.region
  display_name           = "pii-taxonomy"
  activated_policy_types = ["FINE_GRAINED_ACCESS_CONTROL"]
}
resource "google_data_catalog_policy_tag" "pii" {
  taxonomy     = google_data_catalog_taxonomy.pii.id
  display_name = "pii"
}

# TODO 5 — only the compliance principal can read tagged columns
resource "google_data_catalog_policy_tag_iam_member" "reader" {
  policy_tag = google_data_catalog_policy_tag.pii.id
  role       = "roles/datacatalog.categoryFineGrainedReader"
  member     = var.reader
}

# TODO 2 — CMEK dataset
resource "google_bigquery_dataset" "pii" {
  dataset_id                 = "pii"
  location                   = var.region
  delete_contents_on_destroy = true
  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.key.id
  }
  depends_on = [google_kms_crypto_key_iam_member.bq_use]
}

# TODO 4 — table with policy tags on email + ssn (column-level security)
resource "google_bigquery_table" "customers" {
  dataset_id          = google_bigquery_dataset.pii.dataset_id
  table_id            = "customers"
  deletion_protection = false

  schema = jsonencode([
    { name = "id", type = "STRING" },
    { name = "email", type = "STRING",
    policyTags = { names = [google_data_catalog_policy_tag.pii.id] } },
    { name = "ssn", type = "STRING",
    policyTags = { names = [google_data_catalog_policy_tag.pii.id] } },
    { name = "country", type = "STRING" },
  ])
}

output "kms_key" { value = google_kms_crypto_key.key.id }
output "policy_tag" { value = google_data_catalog_policy_tag.pii.id }
