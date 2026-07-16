"""
Module 7 Solution — Sessionize a Click Stream
=============================================
Pub/Sub clicks -> event-time session windows (5-min gap) -> per-session summary
-> BigQuery.

  pip install 'apache-beam[gcp]'
  python solution.py --runner=DirectRunner --project=$PROJECT_ID \
    --subscription=projects/$PROJECT_ID/subscriptions/clicks-sub \
    --output_table=$PROJECT_ID:sessions.summary
"""
import argparse
import json
import logging

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions
from apache_beam.transforms.window import Sessions, TimestampedValue


class ParseClick(beam.DoFn):
    """TODO 1 + TODO 5: parse and stamp EVENT time from the record."""

    def process(self, element):
        try:
            rec = json.loads(element.decode("utf-8"))
            # TimestampedValue attaches event time so windows use it, not arrival.
            yield TimestampedValue((rec["user_id"], rec), float(rec["ts"]))
        except Exception:
            yield beam.pvalue.TaggedOutput("dead", element)


def summarize(user_and_clicks, window=beam.DoFn.WindowParam):
    """TODO 3: one summary row per (user, session window)."""
    user_id, clicks = user_and_clicks
    clicks = list(clicks)
    return {
        "user_id": user_id,
        "click_count": len(clicks),
        # window.start is the session start in event time (epoch seconds).
        "session_start": float(window.start),
    }


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
            | "Parse" >> beam.ParDo(ParseClick()).with_outputs("dead", main="ok")
        )

        (
            parsed.ok
            # TODO 2: 5-minute inactivity gap sessions, per user (keyed already).
            | "Sessions" >> beam.WindowInto(Sessions(5 * 60))
            | "Group" >> beam.GroupByKey()
            | "Summarize" >> beam.Map(summarize)
            # TODO 4: write session summaries to BigQuery.
            | "WriteBQ" >> beam.io.WriteToBigQuery(
                known.output_table,
                schema="user_id:STRING,click_count:INTEGER,session_start:TIMESTAMP",
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
            )
        )

        # Stretch #3 — dead-letter unparseable messages.
        parsed.dead | "Bad" >> beam.Map(lambda b: logging.warning("bad: %r", b))


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
