# Module 13 — Migration & Hybrid Connectivity: annotated concepts
#
# This file shows the *networking substrate* that private data ingestion relies
# on: a VPC whose subnet has Private Google Access, the IAM grants Shared VPC
# pipelines need, and a Datastream private-connectivity configuration with a
# CDC stream skeleton.
#
# NOTE: an actual on-prem link (Interconnect/VPN) can't be demoed from a lab
# project; the resources below are the cloud-side halves you'd attach it to.

variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "us-central1"
}

# ------------------------------------------------------------------ network
# Custom-mode VPC: you control subnets (auto-mode is the lab shortcut, custom
# is what real orgs and the exam assume).
resource "google_compute_network" "hybrid" {
  project                 = var.project_id
  name                    = "hybrid-ingest-vpc"
  auto_create_subnetworks = false
}

# The subnet pipelines (Dataflow workers, Datastream peering) live in.
# private_ip_google_access = true  → workers WITHOUT public IPs can still call
# Google APIs (GCS, BigQuery, Pub/Sub). This single flag is what makes
# "--no_use_public_ips" Dataflow jobs work.
resource "google_compute_subnetwork" "pipelines" {
  project                  = var.project_id
  name                     = "pipelines-subnet"
  region                   = var.region
  network                  = google_compute_network.hybrid.id
  ip_cidr_range            = "10.10.0.0/20"
  private_ip_google_access = true
}

# Egress to Google APIs happens over the private range; for anything else,
# private-IP workers need Cloud NAT (no inbound exposure, outbound only).
resource "google_compute_router" "nat_router" {
  project = var.project_id
  name    = "hybrid-nat-router"
  region  = var.region
  network = google_compute_network.hybrid.id
}

resource "google_compute_router_nat" "nat" {
  project                            = var.project_id
  name                               = "hybrid-nat"
  region                             = var.region
  router                             = google_compute_router.nat_router.name
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# ------------------------------------------------- shared-vpc style grants
# In a real Shared VPC, this subnet lives in the HOST project and these
# bindings are what let a SERVICE project's pipeline attach to it.
# Without them, Dataflow jobs fail at startup with subnet permission errors —
# a classic exam scenario.
resource "google_service_account" "dataflow_worker" {
  project      = var.project_id
  account_id   = "df-hybrid-worker"
  display_name = "Dataflow worker SA for hybrid ingestion"
}

# Worker SA may use the subnet…
resource "google_compute_subnetwork_iam_member" "worker_network_user" {
  project    = var.project_id
  region     = var.region
  subnetwork = google_compute_subnetwork.pipelines.name
  role       = "roles/compute.networkUser"
  member     = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

# …and so must the Dataflow SERVICE AGENT (the Google-managed identity that
# actually creates worker VMs). Its email has the fixed form below.
data "google_project" "this" { project_id = var.project_id }

resource "google_compute_subnetwork_iam_member" "service_agent_network_user" {
  project    = var.project_id
  region     = var.region
  subnetwork = google_compute_subnetwork.pipelines.name
  role       = "roles/compute.networkUser"
  member     = "serviceAccount:service-${data.google_project.this.number}@dataflow-service-producer-prod.iam.gserviceaccount.com"
}

# -------------------------------------------- datastream private connectivity
# Datastream peers into your VPC so CDC traffic to an on-prem/VPC database
# rides your private path (Interconnect/VPN) instead of the public internet.
# It needs its own unused /29 range for the peering.
resource "google_datastream_private_connection" "to_vpc" {
  project               = var.project_id
  location              = var.region
  private_connection_id = "ds-private-conn"
  display_name          = "Datastream private connectivity"

  vpc_peering_config {
    vpc    = google_compute_network.hybrid.id
    subnet = "10.20.0.0/29"
  }
}

# Source profile: a MySQL reachable over the private path. Host is the
# database's PRIVATE address (on-prem via Interconnect, or a Cloud SQL
# private IP through a proxy VM).
resource "google_datastream_connection_profile" "mysql_source" {
  project               = var.project_id
  location              = var.region
  connection_profile_id = "mysql-onprem-source"
  display_name          = "On-prem MySQL (private path)"

  mysql_profile {
    hostname = "10.40.0.15" # private IP over Interconnect/VPN
    port     = 3306
    username = "datastream"
    password = "CHANGE-ME-use-secret-manager" # lab only; use Secret Manager refs
  }

  private_connectivity {
    private_connection = google_datastream_private_connection.to_vpc.id
  }
}

# Destination profile: BigQuery (Datastream writes CDC rows directly).
resource "google_datastream_connection_profile" "bq_destination" {
  project               = var.project_id
  location              = var.region
  connection_profile_id = "bq-analytics-destination"
  display_name          = "BigQuery destination"

  bigquery_profile {}
}

# The stream itself: which tables to replicate, where to land them, and how
# fresh (staleness limit trades cost vs latency on the BigQuery side).
resource "google_datastream_stream" "mysql_to_bq" {
  project      = var.project_id
  location     = var.region
  stream_id    = "mysql-to-bq-cdc"
  display_name = "MySQL → BigQuery CDC"

  source_config {
    source_connection_profile = google_datastream_connection_profile.mysql_source.id
    mysql_source_config {
      include_objects {
        mysql_databases {
          database = "sales"
          # empty tables list = all tables in the database
        }
      }
    }
  }

  destination_config {
    destination_connection_profile = google_datastream_connection_profile.bq_destination.id
    bigquery_destination_config {
      data_freshness = "900s" # 15 min staleness limit
      source_hierarchy_datasets {
        dataset_template {
          location = "US"
        }
      }
    }
  }

  backfill_all {} # snapshot existing rows, then stream changes

  desired_state = "NOT_STARTED" # flip to RUNNING when the private path is live
}
