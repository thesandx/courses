# Solution 13 — Private Ingestion Path (reference)
#
# Part A answers (short form):
#  A1. 250 TB at 200 Mbps * 0.8 ≈ 160 Mbps effective ≈ 20 MB/s
#      → 250e6 MB / 20 MB/s ≈ 145 days. Misses the month by ~5x →
#      TRANSFER APPLIANCE. STS can't beat the link's physics.
#  A2. DATASTREAM with PRIVATE CONNECTIVITY (VPC peering) riding the
#      Interconnect. Allowlisting/forward-SSH traverse public networks.
#  A3. roles/compute.networkUser on the shared subnetwork for BOTH the
#      Dataflow worker service account AND the Dataflow service agent
#      (service-<project-number>@dataflow-service-producer-prod.iam.gserviceaccount.com).
#  A4. BigQuery OMNI (query in AWS) + BIGLAKE tables over the S3 data —
#      users query tables, never the bucket.
#
# Part C answers:
#  C1. The networkUser grant for the Dataflow/Datastream SERVICE AGENT on the
#      host project's subnetwork (granting only the worker SA is the classic miss).
#  C2. DATABASE MIGRATION SERVICE (DMS) — same private path (Interconnect +
#      private connectivity), different destination: Cloud SQL as a database.
#  C3. Pub/Sub Kafka connector mirroring topics into Pub/Sub; or Dataflow
#      KafkaIO reading their brokers directly (or move brokers to Managed
#      Service for Apache Kafka).

variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "us-central1"
}

data "google_project" "this" { project_id = var.project_id }

# B1 — VPC + PGA subnet -----------------------------------------------------
resource "google_compute_network" "retail_hybrid" {
  project                 = var.project_id
  name                    = "retail-hybrid-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "ingest" {
  project                  = var.project_id
  name                     = "ingest-subnet"
  region                   = var.region
  network                  = google_compute_network.retail_hybrid.id
  ip_cidr_range            = "10.50.0.0/20"
  private_ip_google_access = true # the flag that makes no-public-IP workers viable
}

# B2 — outbound-only internet for private workers ---------------------------
resource "google_compute_router" "router" {
  project = var.project_id
  name    = "retail-hybrid-router"
  region  = var.region
  network = google_compute_network.retail_hybrid.id
}

resource "google_compute_router_nat" "nat" {
  project                            = var.project_id
  name                               = "retail-hybrid-nat"
  region                             = var.region
  router                             = google_compute_router.router.name
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# B3 — the two networkUser grants ------------------------------------------
resource "google_service_account" "worker" {
  project      = var.project_id
  account_id   = "retail-df-worker"
  display_name = "Dataflow worker SA (retail ingestion)"
}

resource "google_compute_subnetwork_iam_member" "worker" {
  project    = var.project_id
  region     = var.region
  subnetwork = google_compute_subnetwork.ingest.name
  role       = "roles/compute.networkUser"
  member     = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_compute_subnetwork_iam_member" "dataflow_agent" {
  project    = var.project_id
  region     = var.region
  subnetwork = google_compute_subnetwork.ingest.name
  role       = "roles/compute.networkUser"
  member     = "serviceAccount:service-${data.google_project.this.number}@dataflow-service-producer-prod.iam.gserviceaccount.com"
}

# B4 — Datastream private path + CDC stream --------------------------------
resource "google_datastream_private_connection" "peering" {
  project               = var.project_id
  location              = var.region
  private_connection_id = "retail-ds-private"
  display_name          = "Datastream peering into retail-hybrid-vpc"

  vpc_peering_config {
    vpc    = google_compute_network.retail_hybrid.id
    subnet = "10.60.0.0/29" # unused /29 reserved for the peering
  }
}

resource "google_datastream_connection_profile" "mysql" {
  project               = var.project_id
  location              = var.region
  connection_profile_id = "retail-mysql-src"
  display_name          = "On-prem orders MySQL"

  mysql_profile {
    hostname = "10.70.0.10" # private address reachable over the Interconnect
    port     = 3306
    username = "datastream"
    password = "CHANGE-ME" # lab placeholder; production: Secret Manager
  }

  private_connectivity {
    private_connection = google_datastream_private_connection.peering.id
  }
}

resource "google_datastream_connection_profile" "bigquery" {
  project               = var.project_id
  location              = var.region
  connection_profile_id = "retail-bq-dest"
  display_name          = "BigQuery analytics destination"

  bigquery_profile {}
}

resource "google_datastream_stream" "orders_cdc" {
  project      = var.project_id
  location     = var.region
  stream_id    = "orders-mysql-to-bq"
  display_name = "orders CDC → BigQuery"

  source_config {
    source_connection_profile = google_datastream_connection_profile.mysql.id
    mysql_source_config {
      include_objects {
        mysql_databases {
          database = "orders"
        }
      }
    }
  }

  destination_config {
    destination_connection_profile = google_datastream_connection_profile.bigquery.id
    bigquery_destination_config {
      data_freshness = "900s" # 15-minute freshness requirement
      source_hierarchy_datasets {
        dataset_template {
          location = "US"
        }
      }
    }
  }

  backfill_all {}

  desired_state = "NOT_STARTED" # start once the private path is verified
}
