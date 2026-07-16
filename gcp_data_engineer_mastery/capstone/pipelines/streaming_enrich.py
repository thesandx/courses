"""
Capstone — Streaming Enrichment (Apache Beam / Dataflow)
========================================================
Pub/Sub trips -> validate/parse (bad -> dead-letter) -> 1-min event-time windows
-> write raw trips to BigQuery AND upsert latest driver location to Bigtable.

Applies Modules 6 (Pub/Sub), 7 (Beam windowing), 4/3 (BigQuery), 5 (Bigtable).

Run on Dataflow:
  pip install 'apache-beam[gcp]'
  python streaming_enrich.py \
    --runner=DataflowRunner --project=$PROJECT --region=us-central1 \
    --streaming --enable_streaming_engine \
    --subscription=projects/$PROJECT/subscriptions/trips-dataflow \
    --bq_table=$PROJECT:rideshare.trips_raw \
    --bt_instance=rideshare-live \
    --temp_location=gs://$PROJECT-rideshare-raw/tmp
"""
import argparse
import datetime
import json
import logging

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.transforms.window import FixedWindows


class ParseTrip(beam.DoFn):
    """Validate + parse. Malformed messages go to the 'dead' output."""

    REQUIRED = ("trip_id", "driver_id", "fare_cents", "lat", "lng", "event_ts")

    def process(self, element):
        try:
            rec = json.loads(element.decode("utf-8"))
            if not all(k in rec for k in self.REQUIRED):
                raise ValueError("missing field")
            yield rec
        except Exception as e:
            yield beam.pvalue.TaggedOutput("dead", (str(e), element))


def to_bq_row(rec):
    ts = datetime.datetime.utcfromtimestamp(rec["event_ts"]).isoformat()
    return {
        "trip_id": rec["trip_id"],
        "driver_id": rec["driver_id"],
        "rider_id": rec.get("rider_id"),
        "fare_cents": int(rec["fare_cents"]),
        "lat": float(rec["lat"]),
        "lng": float(rec["lng"]),
        "event_ts": ts,
    }


def to_bigtable_row(rec):
    """Row key = driverId#<reverse_timestamp> to avoid write hotspotting (Module 5)."""
    from google.cloud.bigtable.row import DirectRow

    reverse_ts = (2 ** 63 - 1) - int(rec["event_ts"])
    key = f"{rec['driver_id']}#{reverse_ts}".encode()
    row = DirectRow(row_key=key)
    row.set_cell("loc", b"lat", str(rec["lat"]).encode())
    row.set_cell("loc", b"lng", str(rec["lng"]).encode())
    return row


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--bq_table", required=True)
    parser.add_argument("--bt_instance", required=True)
    known, beam_args = parser.parse_known_args(argv)

    opts = PipelineOptions(beam_args)
    opts.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=opts) as p:
        parsed = (
            p
            | "Read" >> beam.io.ReadFromPubSub(subscription=known.subscription)
            | "Window" >> beam.WindowInto(FixedWindows(60))
            | "Parse" >> beam.ParDo(ParseTrip()).with_outputs("dead", main="ok")
        )

        # Raw trips -> BigQuery (partitioned/clustered table already exists).
        (
            parsed.ok
            | "ToBQ" >> beam.Map(to_bq_row)
            | "WriteBQ" >> beam.io.WriteToBigQuery(
                known.bq_table,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            )
        )

        # Latest location -> Bigtable for low-latency lookups.
        try:
            from apache_beam.io.gcp.bigtableio import WriteToBigTable

            (
                parsed.ok
                | "ToBT" >> beam.Map(to_bigtable_row)
                | "WriteBT" >> WriteToBigTable(
                    project_id=opts.get_all_options().get("project"),
                    instance_id=known.bt_instance,
                    table_id="driver_locations",
                )
            )
        except ImportError:
            logging.warning("bigtableio unavailable in this env; skipping BT sink")

        # Dead-letter bad messages (in prod, publish to trips-dlq).
        parsed.dead | "LogBad" >> beam.Map(lambda x: logging.warning("bad: %s", x[0]))


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
