###############################################################################
# storage.tf — Lake zoning + lifecycle + UBLA (Module 2)
###############################################################################

resource "google_storage_bucket" "raw" {
  name                        = "${var.project_id}-rideshare-raw-${random_id.suffix.hex}"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  versioning { enabled = true }

  lifecycle_rule {
    condition { age = 30 }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  lifecycle_rule {
    condition { age = 365 }
    action { type = "Delete" }
  }
}

resource "google_storage_bucket" "curated" {
  name                        = "${var.project_id}-rideshare-curated-${random_id.suffix.hex}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  autoclass { enabled = true }
}
