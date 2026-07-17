# 🎯 The Interview Gauntlet — 20 Drills to Staff-Level

> The final unit. You've built the platform; now you convert it into interview
> performance. This gauntlet re-runs **Part E of the system-design notes** (all 20
> question breakdowns) as timed, out-loud mock sessions — each anchored to what
> you built, each scored against the 5 dimensions interviewers actually grade
> (§1): requirements thinking, architecture reasoning, trade-off awareness,
> depth, production knowledge.

## How to run a drill

1. **45-minute timer, out loud, standing at a whiteboard** (or excalidraw +
   screen recording). No notes during; notes review after.
2. Open with the framework declaration (§2 power move), then run all 7 steps —
   checkpoints: architecture drawn by minute 15, deep dives offered by minute 30.
3. Record yourself. Afterwards, score 1–5 on each of the 5 dimensions and re-read
   the corresponding question breakdown in the notes. Log scores in
   `gauntlet_log.md` — you're looking for trend, not perfection.
4. **Use PipeForge evidence sparingly but decisively:** one first-person proof
   per deep dive ("when I built this, the consumer rebalance duplicated 0.3% of
   events — here's the dedup layer that absorbed it") lands harder than ten.
5. Every question: end with monitoring + one SLA sentence, even if unasked (§9).

## Schedule (3–4 weeks, don't binge)

| Week | Drills | Theme |
|---|---|---|
| 1 | Q1, Q2, Q3, Q6, Q7 | Warm-ups + your home turf (warehouse, medallion, platform) |
| 2 | Q4, Q5, Q8, Q9, Q18 | Streaming, CDC, quality, dedup — your Phase 4/5/8 muscles |
| 3 | Q10, Q11, Q13, Q14, Q20 | Hard mode: hot paths, exactness, skew, IoT volume |
| 4 | Q12, Q15, Q16, Q17, Q19 | Staff mode: multi-tenant, mesh, two-phase serving, feeds |

Re-run your three weakest at the end. A drill that went badly and was repeated is
worth five that went fine.

## Per-question anchors (your PipeForge evidence base)

**Q1 Log aggregation (Easy):** Your clickstream pipeline *is* one. Anchor: RAW
ingestion-date partitions + offset-stamped files (replay/debug story). Watch for:
don't over-engineer — this is a batch-tolerant use case unless they say otherwise.

**Q2 URL shortener analytics (Easy):** Tiny volume — say so with the §3 threshold
table and design small (the restraint is the test). Anchor: your rollup pattern.

**Q3 E-commerce warehouse (the most-asked):** This is NovaMart. Grain declaration,
star schema, SCD2 as-of joins, idempotent daily loads, 5 baseline DQ checks.
You should score 5/5 here or repeat it until you do — it's your home game.

**Q4 Real-time metrics dashboard:** SLA-number-first (§27). Anchor: micro-batch
consumer + rollups + freshness stamp. Trap: "real-time" usually means minutes —
ask, then say why you're *not* reaching for Flink.

**Q5 CDC replication:** Anchor: the hard-delete drift incident (P08) — tell it,
then the log-based CDC design (§23), snapshot + ordering + lag monitoring
("monitor consumer lag, not connector status").

**Q6 Medallion lake:** RAW/ODP/FDP/CDP with the layer-contract table (charter §3).
Anchor: "bronze a little clean" mistake and why your RAW is verbatim + manifests.

**Q7 ETL framework for 100 sources (the platform question):** Your thesis
statement. Registry → contracts → parameter-driven engines → DAG factory →
uniform DQ/audit → onboarding in minutes. Deep dives: parse-time safety of the
DAG factory, tenant fairness, contract change protocol. This should be your
single strongest 45 minutes on Earth.

**Q8 Feature store:** Anchor: `customer_features` CDP table (offline) + the
online/offline consistency problem; dual-store pattern, point-in-time-correct
training data (your SCD2/as-of machinery is exactly this).

**Q9 DQ monitoring framework:** Phase 8 verbatim: 6 dimensions, severity ladder,
golden rule, calibration, scorecard. Include the silent-semantic-corruption story
(schema-valid but wrong by 100x).

**Q10 Uber surge pricing (final boss):** Hot path (sub-minute aggregates per geo
cell) + cold path (batch correctness + reconciliation) — the hybrid §5 pattern.
Anchors: your lag math, skew surgery (hot cells = hot keys!), late-data honesty.
Geo-cell partitioning is the new element — think H3/S2 cells as partition keys.

**Q11 Spotify royalties:** Money = exactness talk: effectively-once (at-least-once
+ idempotent MERGE), immutable audit, recon with tolerance zero, backfill with
restatement protocol. Anchor: your recon framework + append-only `pipeline_run`.

**Q12 Netflix recommendations:** Lakehouse replay for training sets (RAW retention
as the "lambda-lite insurance", §13), feature freshness tiers, offline/online split.

**Q13 Real-time fraud:** The one where micro-batch genuinely loses — argue the
Flink/stateful-streaming graduation honestly (§27/§36): sub-second scoring,
event-at-a-time state, then batch reconciliation behind it. Knowing where your
own architecture stops is the staff signal.

**Q14 Twitter timeline analytics:** Sessionization + celebrity skew — your salting
numbers from P13 are the star. Fan-out math up front (§4).

**Q15 Multi-tenant SaaS platform (staff favorite):** Phase 12 verbatim: isolation
ladder with a chosen rung and reasons, noisy-neighbor incident, per-tenant cost,
quotas. Add schema-evolution-per-tenant and compliance variance as deep dives.

**Q16 Real-time recommendation engine (two-phase):** Batch candidate generation
(CDP) + online ranking store; your rollup + key-value serving discussion. Focus
on the handoff: how offline features reach the online store (reverse ETL, §28).

**Q17 LinkedIn activity feed:** Estimation-heavy (§4): events/day → fan-out
write vs read tradeoff → storage math out loud. Then standard lake + hot path.

**Q18 Ad click stream:** Dedup at billing-grade + late attribution (30-day
windows): your lookback-MERGE pattern generalizes; discuss watermark vs
append-and-compact for a 30-day revision window (§17), and click-fraud DLQ.

**Q19 Data mesh platform (staff/principal):** Argue the *organizational* problem
first (§25: central-team bottleneck), then your platform as the self-serve layer,
contracts as the federation mechanism, catalog as discovery. Be the candidate who
says when mesh is wrong.

**Q20 IoT pipeline:** Volume math (500K devices × 30s), device clock skew (§17
late data at 20–30%!), per-device ordering (Kafka keys), DLQ for corrupt
firmware payloads, downsampling tiers for retention cost. All patterns you own.

## The five war stories (rehearse until they're 2 minutes each)

From your `docs/incidents/`, pick five spanning different failure classes, e.g.:
1. Hard-delete drift caught by recon (ingestion correctness)
2. Append double-count (idempotency)
3. Silent semantic corruption — prices ÷100 (why schema checks aren't enough)
4. Consumer lag / retention near-miss (streaming ops)
5. Token key rotation breaking joins (governance meets correctness)

Format (§8): what broke → impact → how detected → fix → prevention. These answer
"tell me about a hard bug", "a production incident", "a time you improved
reliability" — behavioral rounds are system-design rounds in disguise for DEs.

## Final calibration

- Re-read the **entire notes file** in one sitting; skim **§41 rapid recap** the
  night before any interview.
- Do one full mock with a human (peer, mentor, or paid) for Q3, Q7, and one hard
  question — external calibration catches habits self-review can't.
- The bar you're aiming for, in one line: **every claim in your interview is
  something you can open a terminal and prove.** That's what this course bought you.

Good luck. You did the work — now go collect.
