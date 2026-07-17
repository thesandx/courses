# Phase 13 — Scale, Hardening & Chaos Drills (`v0.13.0`)

> **Mission:** stop trusting the platform; attack it. Run 10x load and find the
> real bottlenecks, fix skew with your own hands, rehearse the §8 failure domains
> as live chaos drills, and write the runbooks. This phase converts twelve phases
> of building into the scar tissue that interviews (and pages) actually test.

## 1. Concepts

Reread notes **§8 (deep dives)** — it is the syllabus for this phase — plus
**§19 (numbers)** and **§29 (skew/AQE)**.

- **10x is an engineering problem, 100x is an architecture problem (§8).** You'll
  prove the first half empirically and *argue* the second half in a design doc —
  which is exactly the split interviews expect: measured facts near 10x,
  structured reasoning at 100x.
- **Bottleneck first, fix second.** The §8 answer structure: identify the
  bottleneck → incremental fix → acknowledge the ceiling → quantify cost →
  timeline. Every drill below ends with those five sentences written down.
- **Chaos drills = war stories on demand.** The interview question "tell me about
  a production incident" is unanswerable from tutorials. After this phase you'll
  have ten first-person incidents in `docs/incidents/`, each in the §8 shape:
  what broke → impact → detection → fix → prevention.

## 2. Build

### 2.1 The 10x load test

Crank the generators: clickstream `--eps 2000` for 2 hours (≈15M events), orders
×10 (1M lines/day), churn ×10. Before running, **write predictions** (where will
it hurt first? Kafka? consumer flush? Spark shuffle? BQ MERGE? Cloud SQL audit
writes?). Then run and measure against predictions — the gap between your model
and reality is the lesson.

Measure (and record in `docs/scale-report.md` — a genuinely great README artifact):

| Stage | Metric | 1x | 10x | Bottleneck? |
|---|---|---|---|---|
| Kafka produce | msgs/s, p99 latency | | | |
| Consumer | lag drain time, flush duration | | | |
| RAW→ODP Spark | wall time, shuffle bytes, task skew | | | |
| SCD2 changeset + MERGE | wall time, slot-ms | | | |
| CDP build | bytes billed, wall time | | | |
| Audit DB | write latency, connections | | | |

Likely findings (verify, don't assume): consumer GCS-write flushes become the
lag driver (fix: more partitions + consumers, bigger flush buffers); small-file
explosion in ODP (fix: compaction cadence); Cloud SQL audit inserts become chatty
(fix: batch the writes); one BQ model missing a partition filter (fix: you know).

### 2.2 Skew surgery (§29, prepared since Phase 5)

The sessionization job's bot customers (100x events) make a handful of tasks run
minutes while 199 finish in seconds. Do all three fixes and compare wall time:
1. **AQE on** (already) — measure how far `skewJoin` gets you alone.
2. **Salting**: explode hot keys into `customer_id || '_' || rand(0..15)`,
   aggregate twice (partial per salt → final). Classic, fiddly, worth doing once by hand.
3. **Isolate-and-broadcast**: split hot keys into their own small frame,
   broadcast-join it, union results.

Write the numbers. "I fixed a 40-minute skewed stage down to 6 with salting, and
AQE alone got me to 15" is an interview sentence money can't buy.

### 2.3 Chaos drills — the §8 failure domains, live

Run each as a formal game day (predict → break → observe detection latency →
recover → write the incident file). You built the safety nets; now certify them:

1. **Source down:** stop MySQL for 6 hours through two schedule windows. Circuit
   breaker (P07) should open; other datasets unaffected (graceful degradation);
   recovery = watermark catch-up with zero manual steps.
2. **Poison at volume:** 20% malformed clickstream for 30 min. DLQ absorbs;
   good-path latency unaffected; quarantine conservation law holds.
3. **Mid-write kill:** SIGKILL the Spark ODP job repeatedly at random offsets.
   Partitions never half-visible (dynamic overwrite is atomic per partition);
   retries converge; audit shows attempt trail.
4. **Schema break at the gate:** producer bumps clickstream to an incompatible v3.
   Registry + Schema Registry both reject; pipeline keeps consuming v2; the
   *change protocol* (§16) — not heroics — unblocks it.
5. **The silent stale (THE DE failure mode, §1):** disable the orders DAG on a
   Friday evening. How long until a human knows? (Freshness monitor: ≤15 min past
   SLO. Without it: Monday.) Feel that difference; it's the reason Phase 10 exists.
6. **Backfill under load:** 30-day backfill *while* daily schedules run. Pools
   protect the dailies; recent-first ordering heals dashboards first; no
   duplicate rows anywhere afterward (spot-check with the recon forensic mode).

### 2.4 The 100x design doc — `docs/design/100x.md`

You will not build 100x; you will *design* it, with numbers (§4/§19 math shown):
clickstream 50K ev/s, orders 100M lines/day, 50 tenants. Address, with chosen
options and rejected alternatives: regional sharding, Kafka scaling (partitions,
tiered storage) vs Pub/Sub, Flink vs bigger micro-batch for the hot path,
Iceberg/lakehouse for ODP/FDP, BQ slot reservations vs on-demand, metadata DB
scale-out (the registry becomes the hot spot — read replicas? cache? move audit
to BQ?), and org design (platform team vs mesh, §25). 3–5 pages, ADR tone. This
document is Q10/Q18/Q20-grade preparation and the single best thing to bring up
in a staff interview when asked "how would your system scale?"

### 2.5 Runbooks + on-call pack

For the top 5 alerts: symptom → dashboard link → diagnosis queries → remediation
→ escalation. Test one by handing it to a friend (or following it yourself,
cold, at the terminal) — a runbook you haven't executed is fiction. Tag `v0.13.0`.

## 3. Prove it

- [ ] `docs/scale-report.md` with real 1x/10x numbers and 3 identified bottlenecks, each with its five-sentence §8 analysis
- [ ] Skew: three fixes measured; you can explain *why* AQE alone wasn't enough for your case
- [ ] All 6 chaos drills have incident files with detection latency measured
- [ ] Recon + dedup checks pass after every drill (correctness survived the violence — the point of the whole course)
- [ ] `docs/design/100x.md` reviewed out loud against a 45-minute timer
- [ ] A stranger could handle your top alert with runbook alone

## 4. Break it

This phase *is* Break It. Meta-drill: pick the one component you're most
confident in and design a failure you haven't tested. Confidence without a drill
is exactly where production bites.

## 5. Interview corner

- You now hold **ten first-person war stories**. Practice telling three of them
  in 2 minutes each (what broke → impact → detection → fix → prevention). This is
  the highest-leverage interview asset you own.
- *"What happens at 10x?"* — answer with measurements, then pivot: "at 100x the
  architecture changes — here's my design" (your doc). The measured-then-designed
  structure reads unmistakably staff.
- Run **Q10 (Uber surge — the final boss)** and **Q18 (ad click stream)** as full
  mock sessions now; your late-data, dedup, skew, and hot-path/cold-path
  experience maps directly.

## 6. Stretch goals

- Locust/k6 load test against the Phase-12 API (control planes have SLOs too).
- A `pipeforge chaos` command that injects the drills reproducibly (chaos-as-code — superb README material).
- Cost the 10x run precisely from the FinOps pipeline: $ per extra million events; extrapolate to 100x and sanity-check your design doc's budget.
