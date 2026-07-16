###############################################################################
# Module 6: Pub/Sub — Concepts in Action
#
# Demonstrates: Avro schema on a topic, a dead-letter topic, a pull subscription
#               with exactly-once + DLQ, and a code-free BigQuery subscription.
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

# ---------------------------------------------------------------------------
# 1. Schema: enforce the event contract at publish time.
# ---------------------------------------------------------------------------
resource "google_pubsub_schema" "event" {
  name = "event-schema"
  type = "AVRO"
  definition = jsonencode({
    type = "record", name = "Event",
    fields = [
      { name = "event_id", type = "string" },
      { name = "user_id", type = "string" },
      { name = "action", type = "string" },
      { name = "ts", type = "long" },
    ]
  })
}

# ---------------------------------------------------------------------------
# 2. Main topic bound to the schema.
# ---------------------------------------------------------------------------
resource "google_pubsub_topic" "events" {
  name                       = "events"
  message_retention_duration = "86400s" # 1 day topic retention
  schema_settings {
    schema   = google_pubsub_schema.event.id
    encoding = "JSON"
  }
}

# ---------------------------------------------------------------------------
# 3. Dead-letter topic + its subscription (so DLQ messages are retained).
# ---------------------------------------------------------------------------
resource "google_pubsub_topic" "dlq" { name = "events-dlq" }
resource "google_pubsub_subscription" "dlq" {
  name  = "events-dlq-sub"
  topic = google_pubsub_topic.dlq.id
}

# ---------------------------------------------------------------------------
# 4. Pull subscription: exactly-once, ordered, dead-lettered, tuned ack deadline.
# ---------------------------------------------------------------------------
resource "google_pubsub_subscription" "dataflow" {
  name  = "events-dataflow"
  topic = google_pubsub_topic.events.id

  ack_deadline_seconds         = 60
  enable_exactly_once_delivery = true
  enable_message_ordering      = true
  message_retention_duration   = "604800s" # 7 days

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# ---------------------------------------------------------------------------
# 5. BigQuery subscription: write straight to a table, NO pipeline code.
# ---------------------------------------------------------------------------
resource "google_bigquery_dataset" "stream" {
  dataset_id                 = "stream_ingest"
  location                   = var.region
  delete_contents_on_destroy = true
}

resource "google_bigquery_table" "events" {
  dataset_id          = google_bigquery_dataset.stream.dataset_id
  table_id            = "events_raw"
  deletion_protection = false
  schema = jsonencode([
    { name = "event_id", type = "STRING" },
    { name = "user_id", type = "STRING" },
    { name = "action", type = "STRING" },
    { name = "ts", type = "INT64" },
  ])
}

# The Pub/Sub service agent must be able to write to BigQuery.
resource "google_project_iam_member" "ps_to_bq" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription" "to_bq" {
  name  = "events-to-bq"
  topic = google_pubsub_topic.events.id
  bigquery_config {
    table            = "${var.project_id}.${google_bigquery_dataset.stream.dataset_id}.${google_bigquery_table.events.table_id}"
    use_topic_schema = true
  }
  depends_on = [google_project_iam_member.ps_to_bq]
}
