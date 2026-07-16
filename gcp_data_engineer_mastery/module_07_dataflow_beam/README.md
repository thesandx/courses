# Module 7: Dataflow & Apache Beam

## Learning Objectives
- Understand Beam's **unified batch + streaming** model: `PCollection`, `PTransform`,
  `ParDo`, `GroupByKey`.
- Apply **windowing** (fixed, sliding, session), **watermarks**, **triggers**, and
  **late-data** handling.
- Run pipelines on **Dataflow** with autoscaling, and know when to use **Dataflow vs
  Dataproc vs BigQuery**.
- Achieve **exactly-once** processing and use **Dataflow templates** for reuse.
- Tune for cost/throughput (Streaming Engine, Dataflow Prime, shuffle).

---

## 1. The Beam Model

Beam is a portable API; **Dataflow** is Google's managed runner. One pipeline runs on
bounded (batch) *or* unbounded (streaming) data.

```mermaid
flowchart LR
    R[Read source] --> T1[ParDo: parse]
    T1 --> W[Window]
    W --> G[GroupByKey / Combine]
    G --> T2[ParDo: enrich]
    T2 --> Wr[Write sink]
```

| Primitive | Role |
|-----------|------|
| `PCollection` | Distributed, immutable dataset (bounded or unbounded) |
| `PTransform` | An operation producing a new `PCollection` |
| `ParDo` / `DoFn` | Per-element processing (like map/flatMap) |
| `GroupByKey` / `Combine` | Shuffle + aggregate by key |
| `Window` | Slice unbounded data by event time |

## 2. Windowing & Time

Streaming aggregates need **windows** because the data never ends.

| Window | Shape | Use |
|--------|-------|-----|
| **Fixed (tumbling)** | Non-overlapping N-min buckets | Per-minute counts |
| **Sliding** | Overlapping (size + period) | Moving averages |
| **Session** | Gap-based, per key | User activity sessions |
| **Global** | One window (+ triggers) | Custom triggering |

- **Event time** (when it happened) vs **processing time** (when observed). Beam
  aggregates on **event time**.
- **Watermark:** the system's estimate of "event time completeness." When it passes a
  window's end, the window fires.
- **Triggers:** when to emit results (at watermark, early/speculative, on late data).
- **Late data:** allowed via `allowed_lateness`; handle with accumulation mode.

> **Pitfall:** using **processing-time** windows for late-arriving data produces wrong
> aggregates. Aggregate on **event time** + watermarks + allowed lateness.

## 3. Dataflow vs Dataproc vs BigQuery

| | Dataflow | Dataproc | BigQuery |
|--|----------|----------|----------|
| Paradigm | Beam (unified batch/stream) | Spark/Hadoop | SQL |
| Ops | Fully managed, autoscaling | You manage clusters (or Serverless) | Serverless |
| Best for | Streaming ETL, complex transforms | Existing Spark/Hadoop, ML libs | Set-based SQL transforms (ELT) |
| Migrate to it when | New streaming/portable pipelines | Lift-and-shift Spark jobs | Transform stays in SQL |

> **Exam tip:** "existing **Spark/Hadoop** jobs" → Dataproc. "New **streaming** pipeline,
> no cluster management" → Dataflow. "Transformation expressible in **SQL**" → BigQuery.

## 4. Running on Dataflow

- **Autoscaling** + **Streaming Engine** (moves state/shuffle off workers → cheaper,
  faster scaling).
- **Dataflow Prime**: vertical autoscaling + right-fitting.
- **Templates**: package a pipeline (classic or **Flex**) so others run it with params —
  great for Terraform/Composer-triggered jobs.
- **Exactly-once**: Dataflow dedupes with Pub/Sub message IDs + checkpointing.

```python
with beam.Pipeline(options=opts) as p:
  (p | beam.io.ReadFromPubSub(subscription=sub)
     | beam.WindowInto(FixedWindows(60))
     | beam.Map(parse)
     | beam.CombinePerKey(sum)
     | beam.io.WriteToBigQuery(table))
```

## 5. Cost & Performance Knobs

| Knob | Effect |
|------|--------|
| `--enableStreamingEngine` | Offload shuffle/state → cheaper, faster autoscale |
| `--maxNumWorkers` / autoscaling | Cap cost / control scale |
| `--numWorkers` (batch) | Starting parallelism |
| FlexRS (batch) | Discounted, delay-tolerant batch |
| Fusion / `Reshuffle` | Break fusion to rebalance skew |

---

## 🎯 Exam Focus

| Scenario | Answer |
|----------|--------|
| "Streaming ETL from Pub/Sub to BigQuery, no clusters" | **Dataflow** (Beam) |
| "Migrate existing Spark jobs with minimal change" | **Dataproc** |
| "Per-user activity grouped by inactivity gaps" | **Session windows** |
| "Late events must still be counted correctly" | Event-time windows + **watermarks** + `allowed_lateness` |
| "Reuse a pipeline with different params via CI/Composer" | **Flex template** |
| "Cut streaming cost & speed autoscaling" | **Streaming Engine** |
| "Exactly-once from Pub/Sub" | Dataflow's built-in dedupe (message IDs) |

### Practice Questions
1. **Stream events from Pub/Sub, aggregate per minute, write to BigQuery, no cluster
   ops.** → **Dataflow** with `FixedWindows(60)` reading a Pub/Sub subscription.
2. **You must compute per-user sessions separated by 30 min of inactivity.** → **Session
   windows** with a 30-min gap, keyed by user.
3. **Events arrive up to 10 minutes late; counts must be correct.** → Event-time windows +
   watermark + `allowed_lateness=10min`, accumulating trigger.
4. **A large fleet of on-prem Spark jobs must move to GCP with little rewrite.** →
   **Dataproc** (Spark), not Dataflow.
5. **Your streaming job's autoscaling is slow and workers hold huge state.** → Enable
   **Streaming Engine** (offloads state/shuffle).
6. **Analysts want to run the same pipeline with a different date param from Composer.** →
   Publish a **Flex template**; trigger it with parameters.

---

## Key Takeaways
- Beam unifies batch + streaming; **Dataflow** runs it fully managed with autoscaling.
- Aggregate streams on **event time** with **windows + watermarks + triggers**; allow
  lateness.
- **Dataflow** for new/streaming/portable, **Dataproc** for existing Spark/Hadoop,
  **BigQuery** for SQL transforms.
- Use **Flex templates** for reuse and **Streaming Engine** for cost/scale.

Next: [Module 8 — Dataproc & Spark](../module_08_dataproc_spark/README.md).

---

## Files in This Module
- `concepts.py` — a Beam pipeline: Pub/Sub → fixed windows → per-key sum → BigQuery
- `concepts.tf` — deploy it as a Dataflow Flex template job with autoscaling
- `exercise.md` — build a sessionizing streaming pipeline
- `solution.py` — reference solution
