# Module 7 Exercise: Sessionize a Click Stream

## Goal
Write a Beam pipeline that reads click events from Pub/Sub and groups them into **user
sessions** (activity separated by 5 minutes of inactivity), emitting one summary row per
session to BigQuery. This exercises session windows, event time, and keyed aggregation —
prime exam material.

## Tasks
Create `pipeline.py`. Reference `solution.py` after attempting.

### TODO 1 — Read + parse
Read from a Pub/Sub subscription; parse JSON `{user_id, url, ts}`; key by `user_id`.
Drop malformed records to a tagged (dead-letter) output.

### TODO 2 — Session windows
Apply `beam.WindowInto(Sessions(5 * 60))` so each user's clicks group by 5-min gaps.

### TODO 3 — Aggregate per session
For each session, compute `user_id`, `click_count`, and `session_start` (min ts).

### TODO 4 — Write to BigQuery
Append rows to `sessions.summary` with schema
`user_id:STRING, click_count:INTEGER, session_start:TIMESTAMP`, creating the table if
needed.

### TODO 5 — Event time
Attach event timestamps from the record's `ts` (use
`beam.window.TimestampedValue`) so windowing uses **event time**, not arrival time.

## Self-Verification
```bash
pip install 'apache-beam[gcp]'

# Local smoke test on a subscription you publish a few messages to:
python pipeline.py --runner=DirectRunner --project=$PROJECT_ID \
  --subscription=projects/$PROJECT_ID/subscriptions/clicks-sub \
  --output_table=$PROJECT_ID:sessions.summary

# Publish clustered clicks for one user, wait > 5 min, publish more,
# then confirm TWO session rows appear:
bq query --use_legacy_sql=false \
  'SELECT user_id, click_count FROM sessions.summary ORDER BY session_start'
#   → two rows for the same user (two sessions)
```

## Stretch Goals
1. Add `allowed_lateness` and an accumulating trigger so late clicks update the session.
2. Deploy on Dataflow with `--enable_streaming_engine` and observe autoscaling.
3. Route dead-lettered messages to a Pub/Sub DLQ topic instead of logging.

## Cleanup
```bash
# Cancel/drain the Dataflow job if you launched one:
gcloud dataflow jobs list --region=us-central1 --status=active
gcloud dataflow jobs drain <JOB_ID> --region=us-central1
bq rm -f -t $PROJECT_ID:sessions.summary
```
