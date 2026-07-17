# Phase 04 — Streaming Ingestion with Kafka ② (`v0.4.0`)

> **Mission:** run Kafka for real. Produce NovaMart clickstream events with Avro +
> Schema Registry, consume them with a micro-batching consumer into RAW (and
> optionally straight to BigQuery), route poison messages to a DLQ, watch consumer
> lag, and build the Pub/Sub bridge so you can argue Kafka-vs-managed like someone
> who has operated both.

## 1. Concepts

Read notes **§30 (Kafka deep dive)**, **§18 (dedup / delivery semantics)**,
**§27 (micro-batch vs true streaming)**; GCP **M06 (Pub/Sub)**.

The five ideas this phase makes physical:

1. **Kafka is a distributed commit log, not a queue** — retention independent of
   consumption; you will replay the same topic twice into different sinks to feel it.
2. **Partition = unit of parallelism *and* ordering.** You'll key events by
   `session_id` (high cardinality, even spread — §30's good-key criteria) and
   verify per-key ordering survives while global ordering doesn't.
3. **Delivery semantics are a *sink* property as much as a broker property.**
   Your consumer is at-least-once (commit offsets AFTER the GCS write). Duplicates
   are possible by design → downstream dedup (Phase 5) makes it **effectively-once**.
   Say the §18 table from memory.
4. **Micro-batch is a deliberate choice** (§27): the SLA for clickstream analytics
   is minutes, not milliseconds → a 60s-flush consumer meets it at a fraction of
   Flink's operational cost. Know the number at which you'd graduate (<30s SLA,
   stateful event-at-a-time logic).
5. **Contracts move to the wire**: the Avro schema in the Schema Registry *is* the
   Phase-2 contract, now enforced at produce time (§16's "blocked at the
   producer's build, not your 2am failure").

## 2. Build

### 2.1 Kafka locally — `docker/docker-compose.kafka.yml`

```yaml
services:
  kafka:
    image: confluentinc/cp-kafka:7.6.1
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller        # KRaft — no ZooKeeper (say why in interviews: metadata quorum moved into Kafka itself)
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:29093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1     # RF=1 locally; say "RF=3 + min.insync=2 + acks=all" for prod (§30)
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"      # explicit topics only — prod hygiene
    ports: ["9092:9092"]
  schema-registry:
    image: confluentinc/cp-schema-registry:7.6.1
    depends_on: [kafka]
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: PLAINTEXT://kafka:9092
      SCHEMA_REGISTRY_SCHEMA_COMPATIBILITY_LEVEL: BACKWARD
    ports: ["8081:8081"]
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    environment:
      KAFKA_CLUSTERS_0_BOOTSTRAP_SERVERS: kafka:9092
      KAFKA_CLUSTERS_0_SCHEMAREGISTRY: http://schema-registry:8081
    ports: ["8080:8080"]
```

Create topics deliberately (counts are a design decision, not a default — §11):

```bash
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --create \
  --topic novamart.clickstream.v1 --partitions 6 --replication-factor 1
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --create \
  --topic novamart.clickstream.v1.dlq --partitions 1 --replication-factor 1
```

Why 6? Peak 1,500 ev/s ÷ ~10K per partition < 1 — so 6 is pure headroom +
consumer parallelism. Being able to say "the math says 1, I chose 6 for
rebalancing granularity and growth" is the point.

### 2.2 Avro contract + producer — `generators/gen_clickstream.py`

`contracts/clickstream.v1.avsc`:

```json
{"type": "record", "name": "ClickEvent", "namespace": "novamart",
 "fields": [
   {"name": "event_id",   "type": "string"},
   {"name": "session_id", "type": "string"},
   {"name": "customer_id","type": ["null", "string"], "default": null},
   {"name": "event_type", "type": {"type": "enum", "name": "EventType",
       "symbols": ["page_view","search","add_to_cart","checkout","purchase"]}},
   {"name": "url",        "type": "string"},
   {"name": "event_ts",   "type": {"type": "long", "logicalType": "timestamp-millis"}},
   {"name": "user_agent", "type": ["null","string"], "default": null}
 ]}
```

Producer essentials (`confluent-kafka[avro]`):

```python
producer = SerializingProducer({
    "bootstrap.servers": "localhost:9092",
    "key.serializer": StringSerializer(),
    "value.serializer": AvroSerializer(schema_registry_client, schema_str),
    "enable.idempotence": True,     # dedup layer 1 of 4 (§18): broker drops retry-duplicates
    "acks": "all",
    "linger.ms": 20, "batch.size": 65536,   # batching = why Kafka is fast (§30)
})
producer.produce(topic, key=event["session_id"], value=event, on_delivery=cb)
```

The generator simulates sessions (5–30 events each), configurable rate
(`--eps 200`), a `--late-fraction` that emits events with old `event_ts`
(event-time vs processing-time fodder), and `--poison-fraction` that sends
schema-invalid bytes directly with a raw producer (DLQ fodder).

### 2.3 The micro-batching consumer — `src/pipeforge/ingestion/kafka_consumer.py`

The heart of the phase. Design (write this docstring first, code second):

```
Consumer group: pf-raw-lander
Loop:
  poll() up to FLUSH_MAX_EVENTS or FLUSH_INTERVAL_S (60s), buffering per topic-partition
  deserialize Avro; failures → produce raw bytes + error header to .dlq topic
  write buffer → gs://raw/source=kafka/dataset=clickstream/ingest_date=<today>/
                 batch_id=<uuid>/part-<partition>-<first_offset>-<last_offset>.jsonl.gz
  write _MANIFEST.json (counts, offset ranges per partition)
  THEN commit offsets (manual, synchronous)          ← at-least-once boundary
Crash between GCS write and commit ⇒ batch re-lands under a new batch_id
  ⇒ duplicates in RAW ⇒ removed in ODP by (event_id) dedup. Effectively-once.
```

Implementation notes:
- `enable.auto.commit: false`, `auto.offset.reset: earliest`.
- Filenames carry offset ranges — your replay/debug breadcrumbs.
- Emit a `pipeline_run` audit row per flush (layer=`raw`, execution_date=today).
- Expose lag: `pipeforge kafka lag --group pf-raw-lander` (AdminClient: committed
  vs high-watermark per partition). **Lag per partition is THE ops metric** (§30) —
  aggregate lag hides a hot partition.

### 2.4 Drills (do all four — they're the actual learning)

1. **Ordering:** produce a session's events, consume with 2 consumers; confirm
   per-session order intact (same key → same partition), global order not.
2. **Replay (Kappa moment, §21):** `kafka-consumer-groups --reset-offsets
   --to-datetime` on a *new* group; re-land yesterday into a scratch prefix. You
   just did a streaming backfill (§13).
3. **Poison pills:** run generator with `--poison-fraction 0.01`, watch DLQ fill,
   confirm good events unaffected. Inspect DLQ headers (error, original offset).
4. **Rebalance:** start 3 consumers on 6 partitions, kill one mid-flush, watch
   partitions reassign and offsets replay. Count the duplicates in RAW — then
   *keep them*: Phase 5 dedup will prove the pipeline is effectively-once.

### 2.5 The managed alternative: Pub/Sub bridge (GCP M06)

Terraform: `pubsub` module with topic `clickstream`, a **BigQuery subscription**
writing into `raw_stream.clickstream` (schema-mapped), and a DLQ topic with
max-delivery-attempts. Then a 30-line bridge (`pipeforge kafka bridge`) consuming
Kafka → publishing to Pub/Sub.

Now compare honestly (fill the table yourself in `docs/adr/0002-kafka-vs-pubsub.md`):
ops burden, ordering (partitions vs ordering keys), replay (offsets vs
seek/retention), ecosystem (Connect/Streams), cost model, exactly-once story.
This ADR is a ready-made staff interview answer.

### 2.6 Optional cloud drill: Kafka on a GCE VM

`kafka_vm` Terraform module: `e2-small`, container-optimized OS running the same
compose file, firewall scoped to your IP. Point generator + consumer at it, feel
the latency, **then `terraform destroy -target=module.kafka_vm`**. (Managed Kafka
exists on GCP too — mention Confluent Cloud / Google Managed Kafka in the ADR.)

### 2.7 Ship it

Tests: consumer flush logic with a fake consumer (inject poll batches), DLQ
routing on deserialization error, manifest offset-range correctness. Tag `v0.4.0`.

## 3. Prove it

- [ ] 100k+ events produced; RAW has gzipped JSONL with offset-stamped filenames
- [ ] DLQ contains exactly the poison messages, with error headers
- [ ] Kill-and-restart consumer: no gaps (offset math: sum of manifest ranges == high watermark), duplicates present and *counted*
- [ ] `pipeforge kafka lag` shows per-partition lag draining to ~0
- [ ] Pub/Sub BigQuery subscription shows rows in `raw_stream.clickstream`
- [ ] Schema Registry rejects a backward-incompatible v2 (delete a required field, try to produce)

## 4. Break it

Stop the consumer for 2 hours while the generator runs (or set retention to
30 min and watch messages *expire unconsumed* — data loss you caused). Write
`docs/incidents/004-consumer-lag.md`: detection (lag alert, not consumer health —
the §23 lesson), recovery (scale consumers? reset offsets? backfill from where?),
prevention (retention sized to max tolerable outage; lag alert at 50% of retention).

## 5. Interview corner

- Draw the consumer loop and mark the **at-least-once boundary** (commit after
  write). Then say where exactly-once actually lives: "EOS covers Kafka-to-Kafka;
  my sink is GCS, so I do at-least-once + idempotent downstream MERGE —
  effectively-once" (§18, §30). This precise sentence separates seniors from juniors.
- *"Kafka or Pub/Sub?"* — answer from your ADR, both directions, with the "on GCP
  with no Kafka expertise in-house, Pub/Sub" honesty (§5 deviation table).
- *"When Flink?"* — sub-30s SLA, event-at-a-time stateful logic (fraud, CEP);
  otherwise micro-batch wins on ops cost (§27, Q13).

## 6. Stretch goals

- Kafka Connect GCS sink connector — compare with your hand-rolled consumer; argue build-vs-buy.
- Add Prometheus JMX exporter + Grafana for broker metrics.
- Implement a consumer **backpressure** test: cap GCS write speed, watch lag grow, reason about scaling (partitions vs consumers).
