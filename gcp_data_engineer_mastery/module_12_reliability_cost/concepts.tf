###############################################################################
# Module 12: Reliability, Monitoring & Cost — Concepts in Action
#
# Demonstrates: a log-based error metric, an email notification channel, an
#               alert policy on Pub/Sub backlog, and a billing budget with
#               threshold alerts.
# Apply: terraform init && terraform apply \
#          -var project_id=YOUR_PROJECT \
#          -var billing_account=XXXXXX-XXXXXX-XXXXXX \
#          -var alert_email=you@example.com
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
variable "billing_account" { type = string }
variable "alert_email" { type = string }

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# 1. Notification channel (email). Alerts route here.
# ---------------------------------------------------------------------------
resource "google_monitoring_notification_channel" "email" {
  display_name = "DE on-call email"
  type         = "email"
  labels       = { email_address = var.alert_email }
}

# ---------------------------------------------------------------------------
# 2. Log-based metric: count ERROR-severity pipeline logs.
# ---------------------------------------------------------------------------
resource "google_logging_metric" "pipeline_errors" {
  name   = "pipeline_errors"
  filter = "severity>=ERROR AND resource.type=(\"dataflow_step\" OR \"cloud_composer_environment\")"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

# ---------------------------------------------------------------------------
# 3. Alert policy: Pub/Sub subscription backlog growing = pipeline falling behind.
# ---------------------------------------------------------------------------
resource "google_monitoring_alert_policy" "backlog" {
  display_name = "Pub/Sub backlog too high"
  combiner     = "OR"

  conditions {
    display_name = "undelivered messages > 1000"
    condition_threshold {
      filter          = "resource.type=\"pubsub_subscription\" AND metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1000
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.email.id]
}

# ---------------------------------------------------------------------------
# 4. Billing budget with threshold alerts. NOTE: budgets ALERT, they do not cap.
# ---------------------------------------------------------------------------
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account
  display_name    = "data-platform-monthly"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = "200"
    }
  }
  dynamic "threshold_rules" {
    for_each = [0.5, 0.9, 1.0]
    content { threshold_percent = threshold_rules.value }
  }
  # To ENFORCE a cap, add all_updates_rule.pubsub_topic and a function that
  # disables billing when the 100% alert fires.
}
