###############################################################################
# Module 7: Dataflow — Concepts in Action (deploy the Beam pipeline)
#
# Demonstrates: running a Dataflow FLEX TEMPLATE job with autoscaling +
#               Streaming Engine, using a dedicated worker service account.
#
# NOTE: build the flex template image first (out of scope for TF):
#   gcloud dataflow flex-template build gs://BUCKET/templates/events.json \
#     --image-gcr-path REGION-docker.pkg.dev/PROJECT/repo/events:latest \
#     --sdk-language PYTHON --flex-template-base-image PYTHON3 \
#     --py-path . --env FLEX_TEMPLATE_PYTHON_PY_FILE=concepts.py
#
# Apply: terraform init && terraform apply -var project_id=YOUR_PROJECT \
#          -var template_gcs_path=gs://BUCKET/templates/events.json
###############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    # Flex-template jobs are exposed via the google-beta provider.
    google-beta = { source = "hashicorp/google-beta", version = ">= 5.0" }
  }
}

variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "us-central1"
}
variable "template_gcs_path" {
  type        = string
  description = "gs:// path to the built Flex Template spec JSON."
}
variable "worker_sa_email" {
  type        = string
  description = "Dedicated Dataflow worker service account (from Module 1)."
  default     = null
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

resource "google_dataflow_flex_template_job" "events" {
  provider                = google-beta
  name                    = "events-streaming"
  container_spec_gcs_path = var.template_gcs_path
  region                  = var.region

  # Autoscaling + Streaming Engine = cheaper, faster scaling.
  parameters = {
    subscription = "projects/${var.project_id}/subscriptions/events-dataflow"
    output_table = "${var.project_id}:stream_ingest.action_counts"
  }
  additional_experiments = ["enable_streaming_engine"]
  max_workers            = 5
  service_account_email  = var.worker_sa_email # least-privilege worker identity

  # Streaming jobs run until drained/cancelled.
  on_delete = "drain"
}
