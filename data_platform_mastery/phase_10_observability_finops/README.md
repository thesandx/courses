# Phase 10 — Observability & FinOps (`v0.10.0`)

> **Mission:** make the platform's health — and its bill — visible and alarmed.
> Freshness SLAs published and enforced, the three monitoring pillars wired to
> alert tiers, structured logs in Cloud Logging, and a billing-export FinOps
> pipeline that is itself built on PipeForge (the platform monitoring itself is
> the elegance move).

## 1. Concepts

Read notes **§9 (monitoring, alerting & SLAs)** — this phase is that section,
implemented; plus **§15 (cost)**; GCP **M12 (reliability, monitoring & cost)**.

- **A green DAG means the code ran — not that the data is right, complete, or
  fresh (§9).** Hence three independent pillars: pipeline health (Airflow +
  `pipeline_run`), data quality (`dq_result` trends — built in P08), and
  **freshness** (checked from the *serving* side, independent of the pipeline
  that was supposed to produce it — independence is the point: a dead scheduler
  can't report itself dead).
- **SLI → SLO → SLA (§9):** SLI = `minutes_since_max_business_ts`; SLO = internal
  target (06:00); SLA = published commitment (08:00). The gap is your reaction buffer.
- **Combined freshness+completeness SLA (§17):** "orders CDP by 06:00 with ≥99.5%
  of source records; 99.9% by noon" — you can *compute* completeness because
  manifests (P03) and recon (P08) exist. Most teams can't; say why you can.
- **FinOps:** the bill is a dataset. Export billing → BigQuery → model it with
  your own Dim/Fact builder → alert on anomalies with your own DQ engine. Cost
  observability uses the same three-pillar thinking as data observability.

## 2. Build

### 2.1 The freshness monitor (the §9 "check that catches everything")

A tiny standalone Cloud Run **job** (deliberately outside Airflow), scheduled by
Cloud Scheduler every 15 min:

```sql
-- one row per CDP/FDP product, driven from the registry's sla_freshness_minutes
SELECT d.name,
       TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), f.max_business_ts, MINUTE) AS staleness_min,
       d.sla_freshness_minutes,
       TIMESTAMP_DIFF(...) > d.sla_freshness_minutes AS breached
FROM registry_datasets d JOIN freshness_probe f USING (name)
```

Breaches write to `sla_breach` + fire alerts: **freshness breaches page the
stakeholder too, not just the DE** (§9 routing — they must know before they trust
a stale dashboard).

### 2.2 Cloud Monitoring wiring (Terraform `monitoring` module)

- **Log-based metrics** from your structlog JSON: `pf_run_failed{dataset,layer}`,
  `pf_dq_block{dataset}`, `pf_recon_delta_pct{dataset}`, `pf_kafka_lag{partition}`
  (pushed by the lag checker).
- **Alert policies mapped to the §9 tier table** — implement the table literally:

| Tier | Condition | Channel |
|---|---|---|
| P0 | SLA breach on a Tier-1 product; recon delta > 1% on revenue | pager (email/SMS in dev) |
| P1 | DQ block fired; run failed after final retry; Kafka lag > 50% retention | pager + Slack |
| P2 | DQ quarantine > threshold; staleness > 50% of SLA | Slack |
| P3 | DLQ non-empty; cost anomaly < $5 | daily digest |

- Every alert body carries: dataset, layer, execution_date, observed vs threshold,
  runbook link (`docs/runbooks/<alert>.md` — write the three most likely ones now).
  The §9 standard: **debuggable in 30 seconds at 3 a.m.**
- One **dashboard** (Terraform `google_monitoring_dashboard`): runs by status,
  freshness heatmap, DQ pass rate, Kafka lag, daily cost.

### 2.3 FinOps pipeline (dogfood!)

1. Terraform: enable **billing export to BigQuery** (dataset `billing`).
2. Register it as a PipeForge dataset (source kind `db`, pattern `full` — it's
   just another source!). Onboarding takes minutes now; notice that.
3. CDP model `agg_daily_cost` (service × sku × labels.day) + DQ rule
   `VolumeAnomaly` on daily cost (±2σ) — a cost spike is a data anomaly, same math.
4. Answer with SQL, and keep the answers in `docs/finops.md`:
   - $ per service per week; $ per **pipeline** (join labels/audit)
   - BigQuery: top-10 queries by bytes billed (INFORMATION_SCHEMA.JOBS) — find
     your own worst query and fix it (partition filter? rollup? clustering?)
   - The headline number: **cost per 1M rows landed→served**, trended weekly.
     Owning a unit-economics number for your platform is a staff-level habit (§15).

### 2.4 Structured logging polish

`run_context` already logs JSON with dataset/layer/execution_date/run_id on every
line (P01/P02). Verify Cloud Logging groups by `jsonPayload.run_id`, build one
saved query per failure mode. When a Dataproc job fails, you should reach the
root-cause log line in ≤3 clicks — practice it now, not during an incident.

### 2.5 Error budget mini-exercise (M12)

Define availability for `pf_orders`: "fraction of days the 06:00 SLO was met,
trailing 30 days; target 99%". That's ~1 blown morning per quarter. Write the
policy: budget exhausted → freeze feature work, spend the sprint on reliability.
One paragraph in `docs/slo.md` — but it's the paragraph that sounds like a staff
engineer in interviews.

### 2.6 Ship it

Tag `v0.10.0`.

## 3. Prove it

- [ ] Stop the orders generator for a day → freshness monitor pages within 15 min of SLO breach **without Airflow's involvement** (kill the scheduler to prove independence)
- [ ] Alert body: dataset, dates, observed/threshold, runbook link all present
- [ ] Dashboard shows: green runs, one red DQ block (replay the Phase-8 drill), Kafka lag draining, daily cost line
- [ ] `agg_daily_cost` populated by a normal PipeForge DAG; cost anomaly rule green
- [ ] You can state your platform's cost per 1M rows and its top cost driver from memory

## 4. Break it

**Alert-fatigue simulation:** set the freshness threshold to 5 minutes for every
dataset and let it flap for an afternoon. Count the pages. Feel the §9 lesson
("alert fatigue is the #1 reason incidents go undetected"), then recalibrate:
page only P0/P1, digest the rest, delete one alert entirely. Document the
before/after page counts in `docs/incidents/011-alert-fatigue.md`.

## 5. Interview corner

- Deliver the **90-second monitoring pitch (§9)** using your own stack: "three
  pillars… freshness checked serving-side every 15 min, independent of the
  pipeline… SLO 06:00, SLA 08:00, the gap is my reaction buffer… P0 pages
  stakeholders on staleness because trust in the dashboard is the product."
- *"How do you keep platform costs down?"* — from your own FinOps data: billing
  export → cost per pipeline → top query fixed (with the before/after bytes) →
  budget alerts → serverless/auto-suspend everywhere (§15's quick wins, lived).
- *"What's your SLA for the warehouse?"* — combined freshness+completeness,
  because you can actually measure completeness (manifests + recon). That answer
  is rarer than you think.

## 6. Stretch goals

- OpenTelemetry traces across ingest→promote→build (span per layer) — see one order's day as a trace.
- Anomaly detection on cost with BigQuery ML (`ARIMA_PLUS` forecast ± band) instead of ±2σ (M11).
- Publish a public status page (Streamlit page reading `sla_breach`) — radical transparency, great README material.
