###############################################################################
# outputs.tf
###############################################################################

output "raw_bucket" { value = google_storage_bucket.raw.name }
output "curated_bucket" { value = google_storage_bucket.curated.name }
output "trips_topic" { value = google_pubsub_topic.trips.id }
output "dataflow_subscription" { value = google_pubsub_subscription.dataflow.id }
output "dataflow_sa" { value = google_service_account.dataflow.email }
output "bigtable_instance" { value = google_bigtable_instance.live.name }
output "rider_pii_policy_tag" { value = google_data_catalog_policy_tag.rider_pii.id }
output "kms_key" { value = google_kms_crypto_key.bq.id }

output "dag_gcs_prefix" {
  description = "Copy DAGs here: gcloud storage cp *.py <this>"
  value       = google_composer_environment.de.config[0].dag_gcs_prefix
}
output "airflow_uri" {
  value = google_composer_environment.de.config[0].airflow_uri
}
