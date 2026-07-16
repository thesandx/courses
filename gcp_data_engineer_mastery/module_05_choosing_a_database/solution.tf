###############################################################################
# Module 5 Solution — Pick & Provision the Right Store
#
# Decisions:
#   Scenario 1 (fleet telemetry) -> BIGTABLE
#     because: millions of writes/sec, KV access by id+time, single-digit-ms,
#     petabyte scale. Row key = "vehicleId#<reverse_timestamp>" so writes for
#     one vehicle stay together but the fleet spreads across nodes (no hotspot).
#   Scenario 2 (global wallet) -> SPANNER
#     because: strong GLOBAL consistency + horizontal scale + relational, no shard.
#   Scenario 3 (loyalty mobile app) -> FIRESTORE
#     because: document model, offline sync, realtime listeners on mobile.
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

# TODO 2 — Scenario 1: Bigtable
resource "google_bigtable_instance" "telemetry" {
  name                = "fleet-telemetry"
  deletion_protection = false
  cluster {
    cluster_id   = "fleet-c1"
    zone         = "${var.region}-a"
    storage_type = "SSD" # low-latency reads
    autoscaling_config {
      min_nodes      = 1
      max_nodes      = 5
      cpu_target     = 60
      storage_target = 2560
    }
  }
}

resource "google_bigtable_table" "readings" {
  name          = "sensor_readings"
  instance_name = google_bigtable_instance.telemetry.name
  column_family { family = "telemetry" }
}

# TODO 3 — Scenario 2: Spanner (global, strongly consistent relational)
resource "google_spanner_instance" "wallet" {
  name             = "global-wallet"
  config           = "regional-${var.region}" # use a multi-region config for true global
  display_name     = "Global Wallet"
  processing_units = 100 # smallest granularity (1/10 node)
}

resource "google_spanner_database" "wallet" {
  instance            = google_spanner_instance.wallet.name
  name                = "wallet"
  deletion_protection = false
  ddl = [
    "CREATE TABLE accounts (account_id STRING(36) NOT NULL, balance_cents INT64 NOT NULL) PRIMARY KEY (account_id)"
  ]
}

# TODO 4 — Scenario 3: Firestore Native
resource "google_firestore_database" "loyalty" {
  project     = var.project_id
  name        = "(default)"
  location_id = "nam5"
  type        = "FIRESTORE_NATIVE"
}

# Stretch #1 — Memorystore cache for hot balances (sub-ms).
resource "google_redis_instance" "cache" {
  name           = "wallet-cache"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
}

output "bigtable" { value = google_bigtable_instance.telemetry.name }
output "spanner_db" { value = google_spanner_database.wallet.name }
