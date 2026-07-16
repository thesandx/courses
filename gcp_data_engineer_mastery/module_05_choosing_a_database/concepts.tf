###############################################################################
# Module 5: Choosing the Right Database — Concepts in Action
#
# Demonstrates provisioning of THREE stores side by side so you can compare the
# knobs each exposes. NOTE: Cloud SQL, Bigtable, and Spanner all bill while
# running — destroy promptly (see Cleanup).
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

# ---------------------------------------------------------------------------
# 1. Cloud SQL (PostgreSQL): classic single-region OLTP. Scaling knob = tier.
# ---------------------------------------------------------------------------
resource "google_sql_database_instance" "oltp" {
  name             = "oltp-pg"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-custom-1-3840" # 1 vCPU / 3.75 GB — smallest custom
    availability_type = "ZONAL"            # REGIONAL for HA (costs ~2x)
    disk_autoresize   = true
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
  }
  deletion_protection = false # course-only
}

# ---------------------------------------------------------------------------
# 2. Bigtable: wide-column, high-throughput. Scaling knob = node count / autoscale.
#    Column families group columns; the ROW KEY (chosen at write time, not here)
#    is what prevents hotspotting.
# ---------------------------------------------------------------------------
resource "google_bigtable_instance" "ts" {
  name                = "timeseries"
  deletion_protection = false

  cluster {
    cluster_id   = "ts-c1"
    zone         = "${var.region}-a"
    storage_type = "SSD"
    autoscaling_config {
      min_nodes      = 1
      max_nodes      = 3
      cpu_target     = 60
      storage_target = 2560
    }
  }
}

resource "google_bigtable_table" "readings" {
  name          = "sensor_readings"
  instance_name = google_bigtable_instance.ts.name
  # Column family for the metric values. Row key design (e.g. sensorId#reverseTs)
  # happens in the client write path — the single most important perf decision.
  column_family {
    family = "metrics"
  }
}

# ---------------------------------------------------------------------------
# 3. Firestore (Native mode): document store for app backends / offline sync.
#    One database per project location; location is immutable.
# ---------------------------------------------------------------------------
resource "google_firestore_database" "app" {
  project     = var.project_id
  name        = "(default)"
  location_id = "nam5" # multi-region; immutable
  type        = "FIRESTORE_NATIVE"
}

output "cloudsql_conn" { value = google_sql_database_instance.oltp.connection_name }
output "bigtable" { value = google_bigtable_instance.ts.name }
