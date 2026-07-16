"""
Module 7: Dataflow & Apache Beam — Concepts in Action
=====================================================
A streaming pipeline: Pub/Sub -> parse JSON -> fixed 60s windows ->
per-action counts -> BigQuery.

Run locally (bounded test) with the DirectRunner, or on Dataflow:

  pip install 'apache-beam[gcp]'

  # Local direct run (uses a Pub/Sub subscription you own):
  python concepts.py \
    --runner=DirectRunner \
    --project=$PROJECT_ID \
    --subscription=projects/$PROJECT_ID/subscriptions/events-dataflow \
    --output_table=$PROJECT_ID:stream_ingest.action_counts

  # On Dataflow (managed, autoscaling, Streaming Engine):
  python concepts.py \
    --runner=DataflowRunner \
    --project=$PROJECT_ID --region=us-central1 \
    --temp_location=gs://$PROJECT_ID-lake-raw/tmp \
    --streaming --enable_streaming_engine \
    --subscription=projects/$PROJECT_ID/subscriptions/events-dataflow \
    --output_table=$PROJECT_ID:stream_ingest.action_counts
"""
import argparse
import json
import logging

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.transforms.window import FixedWindows


# ---------------------------------------------------------------------------
# 1. A DoFn: parse a raw Pub/Sub bytes message into (action, 1). Bad messages
#    are dropped to a side output so a poison record can't crash the pipeline.
# ---------------------------------------------------------------------------
class ParseEvent(beam.DoFn):
    def process(self, element):
        try:
            rec = json.loads(element.decode("utf-8"))
            yield (rec["action"], 1)
        except Exception:  # malformed -> tagged output for a dead-letter sink
            yield beam.pvalue.TaggedOutput("dead", element)


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--output_table", required=True)
    known, pipeline_args = parser.parse_known_args(argv)

    opts = PipelineOptions(pipeline_args)
    opts.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=opts) as p:
        parsed = (
            p
            | "Read" >> beam.io.ReadFromPubSub(subscription=known.subscription)
            # 2. Event-time FIXED windows: one bucket per 60s.
            | "Window" >> beam.WindowInto(FixedWindows(60))
            | "Parse" >> beam.ParDo(ParseEvent()).with_outputs("dead", main="ok")
        )

        # 3. Aggregate per action within each window, then shape for BigQuery.
        (
            parsed.ok
            | "CountPerAction" >> beam.CombinePerKey(sum)
            | "ToRow" >> beam.Map(lambda kv: {"action": kv[0], "count": kv[1]})
            | "WriteBQ" >> beam.io.WriteToBigQuery(
                known.output_table,
                schema="action:STRING,count:INTEGER",
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            )
        )

        # 4. Dead-letter the unparseable messages (here: log; in prod -> Pub/Sub/GCS).
        parsed.dead | "LogBad" >> beam.Map(
            lambda b: logging.warning("dropped bad message: %r", b)
        )


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
