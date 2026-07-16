###############################################################################
# bigtable.tf — Live driver locations: low-latency KV store (Module 5)
#
# ROW KEY DESIGN (in the write path, not here): "driverId#<reverse_timestamp>"
# so each driver's recent points are contiguous while the fleet spreads across
# nodes — avoids the monotonic-timestamp write hotspot.
###############################################################################

resource "google_bigtable_instance" "live" {
  name                = "rideshare-live"
  deletion_protection = false

  cluster {
    cluster_id   = "live-c1"
    zone         = "${var.region}-a"
    storage_type = "SSD" # single-digit-ms reads
    autoscaling_config {
      min_nodes      = 1
      max_nodes      = 3
      cpu_target     = 60
      storage_target = 2560
    }
  }
}

resource "google_bigtable_table" "driver_locations" {
  name          = "driver_locations"
  instance_name = google_bigtable_instance.live.name
  column_family { family = "loc" }
}
