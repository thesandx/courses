###############################################################################
# composer.tf — Cloud Composer 2 for the daily rollup DAG (Module 9)
#
# WARNING: a Composer environment bills continuously (~$300+/mo) and takes
# ~25 min to create. It's included so the capstone is complete; comment this
# file out if you only want to practice the cheaper components.
###############################################################################

resource "google_service_account" "composer" {
  account_id   = "rideshare-composer"
  display_name = "RideShare Composer worker"
}

resource "google_project_iam_member" "composer" {
  for_each = toset([
    "roles/composer.worker",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
    "roles/dataproc.editor",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.composer.email}"
}

resource "google_composer_environment" "de" {
  name   = "rideshare-orchestration"
  region = var.region

  config {
    software_config {
      image_version = "composer-2-airflow-2"
      env_variables = {
        GCP_PROJECT    = var.project_id
        CURATED_BUCKET = google_storage_bucket.curated.name
      }
    }
    node_config {
      service_account = google_service_account.composer.email
    }
    environment_size = "ENVIRONMENT_SIZE_SMALL"
  }
  depends_on = [google_project_service.apis]
}
