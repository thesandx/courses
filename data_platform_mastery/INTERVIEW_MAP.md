# Interview Map — Every Concept → Where You Built It

Use this two ways:
1. **While building:** after each phase, find its rows here and rehearse the claim out loud.
2. **Before interviews:** this is your evidence index — for any topic, you have a
   story, a commit, and a demo.

Notation: **§n** = section in `system_design_notes.md`; **Mnn** = GCP course module; **Pnn** = PipeForge phase.

## Part A — The framework itself

| Interview skill | Where you practice it |
|---|---|
| 7-step delivery framework (§2) | The PROJECT_CHARTER is written in it; every phase's Interview Corner ends with a timed 45-min run |
| Requirements gathering, 7 NFR dimensions (§3) | Charter §1; re-derived for each new NovaMart source in P02/P03 |
| Volume estimation (§4, §19) | P00 exercise; P04 Kafka sizing (partitions ≈ peak ÷ 10K); P13 10x load test |
| High-level architecture, 6 layers (§5) | The platform *is* the 6-layer diagram; you redraw it from memory in P00, P07, P14 |
| Data model & grain (§6) | P06: you declare grain for `fct_order_lines` before writing DDL |
| Pipeline design & idempotency (§7) | P03 (overwrite), P05 (MERGE), P07 (DAG factory, backfill) |
| Deep dives: scaling/failures/quality (§8) | Every phase's **Break it** drill; consolidated in P13 |
| Monitoring, alerting, SLAs (§9) | P10 end-to-end; the 90-second monitoring pitch uses *your* dashboards |

## Part B/C — Core concepts & patterns

| Concept | Built in | Your one-line evidence |
|---|---|---|
| Partitioning strategies (§11) | P03, P05, P06 | "RAW by ingestion date, FDP by business date + clustering — and I've measured the pruning difference in bytes billed" |
| Ingestion patterns (§12) | P03 (full/incr/API), P04 (streaming), P05 (CDC/SCD2) | "One engine, five patterns, chosen per dataset in metadata" |
| Backfill & reprocessing (§13) | P07 | "`pipeforge backfill` — 14 days, one command, zero duplicates" |
| Lineage & impact analysis (§14) | P09, P11 | "OpenLineage events per task; the catalog shows blast radius before a schema change" |
| Cost optimization (§15) | P06, P10 | "Billing export → BQ → my own FinOps page; rollups cut dashboard scans ~90%" |
| Data contracts & schema validation (§16) | P02, P04 | "Contracts versioned in the registry; Kafka Schema Registry blocks breaking changes at the producer" |
| Late-arriving data (§17) | P05 | "Event-time partitions + 2-day lookback MERGE; dashboards show 'complete through X'" |
| Deduplication at scale (§18) | P04, P05 | "Four layers: idempotent producer, ROW_NUMBER, MERGE, dedup-safe rollups" |
| Numbers to know (§19) | P00, P13 | You re-derive them from your own runs (rows/s, $/TB scanned, Parquet ratio) |
| Lambda vs Kappa (§20–21) | P04+P05 | "Streaming hot path + lake replay = the lakehouse hybrid; I reconcile the two daily" |
| Medallion (§22) | P03–P06 | "RAW/ODP/FDP/CDP — enterprise names for bronze/silver/gold, plus a landing zone" |
| CDC patterns (§23) | P05 | "Watermark incremental misses hard deletes — my recon caught it; that's why CDC exists" |
| Micro-batch vs streaming (§27) | P04 | "5-min micro-batch met the SLA at 1/3 the ops cost of Flink — chosen deliberately" |
| Reverse ETL (§28) | P12 stretch | Segments from CDP pushed to a mock CRM endpoint |

## Part D — Technology deep dives

| Tech | Built in | Depth you gain |
|---|---|---|
| Spark internals (§29) | P05, P13 | Shuffle boundaries in *your* SCD2 job's plan; AQE + salting on skewed clickstream |
| Kafka (§30) | P04 | Partitions/keys/consumer groups/lag/EOS boundary — on a broker you run |
| Airflow (§31) | P07 | DAG factory, TaskFlow, datasets, backfills, executor limits |
| dbt (§32) | P06 note | You build the same incremental+merge patterns in raw SQL, then map them to dbt vocabulary |
| Warehouse internals (§33 Snowflake / M04 BigQuery) | P06 | Micro-partitions↔BQ partitions, clustering, slots vs on-demand |
| Delta/Iceberg (§34–35) | P05 | ODP as Parquet vs Iceberg-on-BigLake; time travel for rollback |
| Flink (§36) | P04 Interview Corner | When you'd graduate from micro-batch (state, event-at-a-time) |
| Debezium/CDC tooling (§37) | P05 concepts + stretch | Datastream/Debezium tradeoffs vs your watermark loader |
| Orchestrators (§38) | P07 | Airflow vs Dagster/Prefect — argued from DAG-factory experience |

## Part E — The 20-question bank → your platform

| Q | Question | Your PipeForge answer anchor |
|---|---|---|
| Q1 | Log aggregation & search | Clickstream pipeline (P04) + partitioned RAW + BQ search patterns |
| Q2 | URL shortener analytics | Mini-version of clickstream → rollups (P06) |
| Q3 | E-commerce warehouse (most asked) | **Literally NovaMart** — P03→P06 end-to-end |
| Q4 | Real-time metrics dashboard | Kafka → micro-batch → CDP rollups → Streamlit (P04/P06/P11) |
| Q5 | CDC replication | P05 SCD2 + watermark-vs-CDC tradeoff + recon safety net |
| Q6 | Medallion data lake | P03–P06 layer design, promotion rules, access tiers |
| Q7 | **ETL framework for 100 sources** | **The whole platform** — registration + DAG factory (P02/P07) |
| Q8 | Feature store | P06 CDP feature tables + P12 low-latency serving discussion |
| Q9 | DQ monitoring framework | P08 — 6 dimensions, severity actions, scorecard |
| Q10 | Uber surge pricing | Gauntlet drill: hot path via Kafka + your late-data/reconciliation patterns |
| Q11 | Spotify royalties | Exactness discussion: effectively-once + recon + audit (P05/P08) |
| Q12 | Netflix recommendations | Lakehouse + training data from RAW replay (P05) |
| Q13 | Real-time fraud | Where micro-batch is NOT enough — argue the Flink graduation (P04) |
| Q14 | Twitter timeline analytics | Sessionization job + skew handling (P05/P13) |
| Q15 | Multi-tenant SaaS platform | P12 tenancy model (row vs schema vs project isolation) |
| Q16 | Real-time recommendation engine | Two-phase: batch features (CDP) + online lookup (P12 discussion) |
| Q17 | LinkedIn activity feed | Fan-out math + partitioning (gauntlet) |
| Q18 | Ad click stream | Dedup + late attribution windows — your P05 lookback MERGE |
| Q19 | Data mesh platform | P12 tenants + P09 catalog = "self-serve platform" pillar, argued honestly (§25) |
| Q20 | IoT pipeline | Volume math + device skew + DLQ patterns from P04 |

## Staff-level signals checklist (rehearse until reflexive)

- [ ] I state the freshness SLA as a number before choosing batch vs streaming (§3, §27)
- [ ] I justify every technology with "capability ← requirement" (§5)
- [ ] I declare table grain before listing columns (§6)
- [ ] "How do you handle failures?" → idempotency mechanics, not "we retry" (§7)
- [ ] I proactively offer deep dives at minute 25 (§8)
- [ ] I quantify: partitions, $/TB, events/s, % saved (§19)
- [ ] I know what I would NOT build (Composer vs local Airflow; Flink vs micro-batch; mesh vs monolith)
- [ ] I can tell 5 first-person war stories (one per Break-it drill) in what-broke → impact → detection → fix → prevention shape (§8)
