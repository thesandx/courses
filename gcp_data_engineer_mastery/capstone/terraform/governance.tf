###############################################################################
# governance.tf — CMEK encryption + column-level policy tags (Module 10)
###############################################################################

data "google_bigquery_default_service_account" "bq" {}

resource "google_kms_key_ring" "ring" {
  name     = "rideshare-keyring-${random_id.suffix.hex}"
  location = var.region
}

resource "google_kms_crypto_key" "bq" {
  name            = "rideshare-bq-cmek"
  key_ring        = google_kms_key_ring.ring.id
  rotation_period = "7776000s" # 90 days
}

# BigQuery service agent must use the key or CMEK dataset creation fails.
resource "google_kms_crypto_key_iam_member" "bq_use" {
  crypto_key_id = google_kms_crypto_key.bq.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_bigquery_default_service_account.bq.email}"
}

# Policy-tag taxonomy: tag rider PII columns (rider_id) for column-level security.
resource "google_data_catalog_taxonomy" "pii" {
  region                 = var.region
  display_name           = "rideshare-pii-${random_id.suffix.hex}"
  activated_policy_types = ["FINE_GRAINED_ACCESS_CONTROL"]
}

resource "google_data_catalog_policy_tag" "rider_pii" {
  taxonomy     = google_data_catalog_taxonomy.pii.id
  display_name = "rider-pii"
  description  = "Rider-identifying columns; masked/blocked except for compliance."
}
