###############################################################################
# Module 8: Dataproc & Spark — Concepts in Action
#
# Demonstrates: an autoscaling cluster with SPOT secondary workers + max-idle
#               auto-delete, and a Serverless Spark batch (no cluster to size).
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
# Ephemeral, autoscaling cluster. Primary workers on-demand (hold shuffle);
# secondary workers are SPOT (cheap, preemptible). max-idle auto-deletes it.
# ---------------------------------------------------------------------------
resource "google_dataproc_cluster" "ephemeral" {
  name   = "etl-ephemeral"
  region = var.region

  cluster_config {
    master_config {
      num_instances = 1
      machine_type  = "n2-standard-2"
    }
    worker_config {
      num_instances = 2 # on-demand primaries for shuffle stability
      machine_type  = "n2-standard-2"
    }
    preemptible_worker_config {
      num_instances  = 2 # SPOT secondaries — cheap, reclaimable
      preemptibility = "SPOT"
    }
    # Auto-delete when idle: no paying for an idle cluster.
    lifecycle_config {
      idle_delete_ttl = "1800s" # 30 min
    }
    software_config {
      # Store data in GCS, not HDFS — set the connector-friendly defaults.
      override_properties = {
        "dataproc:dataproc.allow.zero.workers" = "false"
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Serverless Spark batch: submit a PySpark job, no cluster to manage.
# ---------------------------------------------------------------------------
resource "google_dataproc_batch" "serverless_etl" {
  batch_id = "wordcount-batch"
  location = var.region

  runtime_config {
    version = "2.2"
  }
  pyspark_batch {
    main_python_file_uri = "gs://${var.project_id}-lake-raw/jobs/job.py"
    args                 = ["gs://${var.project_id}-lake-raw/input", "gs://${var.project_id}-lake-curated/wordcount"]
  }
}

output "cluster" { value = google_dataproc_cluster.ephemeral.name }
