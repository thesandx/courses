variable "project_id" {
  type        = string
  description = "Target GCP project for the RideShare platform."
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "billing_account" {
  type        = string
  description = "Billing account ID (XXXXXX-XXXXXX-XXXXXX) for the budget."
}

variable "alert_email" {
  type        = string
  description = "Where reliability/cost alerts are sent."
}
