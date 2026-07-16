###############################################################################
# streaming.tf — Pub/Sub ingest: schema, DLQ, exactly-once + ordered sub,
#                and a code-free BigQuery subscription (Module 6)
###############################################################################

resource "google_pubsub_schema" "trip" {
  name = "trip-schema"
  type = "AVRO"
  definition = jsonencode({
    type = "record", name = "Trip", fields = [
      { name = "trip_id", type = "string" },
      { name = "driver_id", type = "string" },
      { name = "rider_id", type = "string" },
      { name = "fare_cents", type = "long" },
      { name = "lat", type = "double" },
      { name = "lng", type = "double" },
      { name = "event_ts", type = "long" },
    ]
  })
}

resource "google_pubsub_topic" "trips" {
  name = "trips"
  schema_settings {
    schema   = google_pubsub_schema.trip.id
    encoding = "JSON"
  }
}

resource "google_pubsub_topic" "dlq" { name = "trips-dlq" }
resource "google_pubsub_subscription" "dlq" {
  name  = "trips-dlq-sub"
  topic = google_pubsub_topic.dlq.id
}

# Pub/Sub service agent must publish to the DLQ for dead-lettering to work.
resource "google_pubsub_topic_iam_member" "sa_dlq" {
  topic  = google_pubsub_topic.dlq.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Pull subscription consumed by the Dataflow streaming pipeline.
resource "google_pubsub_subscription" "dataflow" {
  name  = "trips-dataflow"
  topic = google_pubsub_topic.trips.id

  ack_deadline_seconds         = 60
  enable_exactly_once_delivery = true
  enable_message_ordering      = true

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }
  depends_on = [google_pubsub_topic_iam_member.sa_dlq]
}
