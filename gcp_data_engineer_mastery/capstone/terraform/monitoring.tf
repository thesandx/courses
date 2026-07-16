###############################################################################
# monitoring.tf — Freshness/backlog alerts + billing budget (Module 12)
###############################################################################

resource "google_monitoring_notification_channel" "oncall" {
  display_name = "RideShare on-call"
  type         = "email"
  labels       = { email_address = var.alert_email }
}

# Alert when the streaming pipeline falls behind (Pub/Sub backlog grows).
resource "google_monitoring_alert_policy" "backlog" {
  display_name = "Trips ingest backlog"
  combiner     = "OR"
  conditions {
    display_name = "undelivered > 5000"
    condition_threshold {
      filter          = "resource.type=\"pubsub_subscription\" AND metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\""
      comparison      = "COMPARISON_GT"
      threshold_value = 5000
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  notification_channels = [google_monitoring_notification_channel.oncall.id]
}

# Project budget with 50/90/100% alerts (does not cap; see README stretch).
resource "google_billing_budget" "platform" {
  billing_account = var.billing_account
  display_name    = "rideshare-monthly"
  budget_filter { projects = ["projects/${var.project_id}"] }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = "300"
    }
  }
  dynamic "threshold_rules" {
    for_each = [0.5, 0.9, 1.0]
    content { threshold_percent = threshold_rules.value }
  }
}
