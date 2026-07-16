###############################################################################
# Module 12 Solution — Instrument for Reliability & Cost
#
# TODO 5: Budgets only ALERT. To hard-stop spend, set
#   all_updates_rule { pubsub_topic = <topic> } on the budget, subscribe a Cloud
#   Function, and have it call billing.projects.updateBillingInfo to DETACH the
#   billing account when the 100% threshold message arrives.
#
#   terraform init && terraform apply -var project_id=YOUR_PROJECT \
#     -var billing_account=XXXXXX-XXXXXX-XXXXXX -var alert_email=you@example.com
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

# TODO 1 — email channel
resource "google_monitoring_notification_channel" "oncall" {
  display_name = "on-call"
  type         = "email"
  labels       = { email_address = var.alert_email }
}

# TODO 2 — freshness SLO: watermark age > 15 min
resource "google_monitoring_alert_policy" "freshness" {
  display_name = "Dataflow freshness SLO (lag > 15m)"
  combiner     = "OR"
  conditions {
    display_name = "data_watermark_age > 900s"
    condition_threshold {
      filter          = "resource.type=\"dataflow_job\" AND metric.type=\"dataflow.googleapis.com/job/data_watermark_age\""
      comparison      = "COMPARISON_GT"
      threshold_value = 900
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.oncall.id]
}

# TODO 3 — error-rate: log-based metric + alert
resource "google_logging_metric" "errors" {
  name   = "pipeline_errors"
  filter = "severity>=ERROR"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

resource "google_monitoring_alert_policy" "error_rate" {
  display_name = "Pipeline error spike"
  combiner     = "OR"
  conditions {
    display_name = "errors > 10 / 5m"
    condition_threshold {
      filter          = "resource.type=\"global\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.errors.name}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      duration        = "300s"
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.oncall.id]
}

# TODO 4 — budget with 50/90/100% alerts
resource "google_billing_budget" "project" {
  billing_account = var.billing_account
  display_name    = "project-monthly-100"
  budget_filter { projects = ["projects/${var.project_id}"] }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = "100"
    }
  }
  dynamic "threshold_rules" {
    for_each = [0.5, 0.9, 1.0]
    content { threshold_percent = threshold_rules.value }
  }
}
