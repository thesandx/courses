###############################################################################
# Module 6 Solution — Ordered, Dead-Lettered Ingestion
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

data "google_project" "this" {}

# TODO 1 — schema + topic
resource "google_pubsub_schema" "payment" {
  name = "payment-schema"
  type = "AVRO"
  definition = jsonencode({
    type = "record", name = "Payment", fields = [
      { name = "payment_id", type = "string" },
      { name = "account_id", type = "string" },
      { name = "amount_cents", type = "long" },
      { name = "ts", type = "long" },
    ]
  })
}

resource "google_pubsub_topic" "payments" {
  name = "payments"
  schema_settings {
    schema   = google_pubsub_schema.payment.id
    encoding = "JSON"
  }
}

# TODO 2 — DLQ topic + subscription
resource "google_pubsub_topic" "dlq" { name = "payments-dlq" }
resource "google_pubsub_subscription" "dlq" {
  name  = "payments-dlq-sub"
  topic = google_pubsub_topic.dlq.id
}

# TODO 4 — Pub/Sub service agent needs publish on the DLQ.
resource "google_pubsub_topic_iam_member" "sa_dlq_publish" {
  topic  = google_pubsub_topic.dlq.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# TODO 3 — main worker subscription
resource "google_pubsub_subscription" "worker" {
  name  = "payments-worker"
  topic = google_pubsub_topic.payments.id

  ack_deadline_seconds         = 30
  enable_message_ordering      = true
  enable_exactly_once_delivery = true

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }
  depends_on = [google_pubsub_topic_iam_member.sa_dlq_publish]
}

# Stretch #1 — BigQuery subscription for valid payments.
resource "google_bigquery_dataset" "pay" {
  dataset_id                 = "payments_ds"
  location                   = var.region
  delete_contents_on_destroy = true
}
resource "google_bigquery_table" "pay" {
  dataset_id          = google_bigquery_dataset.pay.dataset_id
  table_id            = "payments_raw"
  deletion_protection = false
  schema = jsonencode([
    { name = "payment_id", type = "STRING" },
    { name = "account_id", type = "STRING" },
    { name = "amount_cents", type = "INT64" },
    { name = "ts", type = "INT64" },
  ])
}
resource "google_project_iam_member" "ps_bq" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_pubsub_subscription" "to_bq" {
  name  = "payments-to-bq"
  topic = google_pubsub_topic.payments.id
  bigquery_config {
    table            = "${var.project_id}.${google_bigquery_dataset.pay.dataset_id}.${google_bigquery_table.pay.table_id}"
    use_topic_schema = true
  }
  depends_on = [google_project_iam_member.ps_bq]
}
