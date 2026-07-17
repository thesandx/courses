# Phase 07 — Orchestration: the DAG Factory ⑩ (`v0.7.0`)

> **Mission:** Airflow ties the platform together — but you will not write DAGs.
> You'll write a **DAG factory** that generates one standardized pipeline per
> registered dataset from the metadata core. Onboarding a source in Phase 2 now
> means a DAG *appears*. Plus: real backfills, sensors, pools, and the
> cross-cutting audit wiring.

## 1. Concepts

Read notes **§31 (Airflow deep dive)**, **§7 (pipeline design)**, **§13 (backfill)**;
GCP **M09 (Composer)**.

- **Airflow orchestrates; it does not process (§31).** Every task here *submits*
  work (Dataproc batch, BQ job, ingestion CLI) and records audit rows. If you find
  pandas in a PythonOperator, you've failed the phase.
- **One DAG per business process (§7)** → one DAG per dataset, uniform shape
  (charter §5). Uniformity is the win: on-call can debug *any* pipeline because
  they all look identical.
- **Parse-time vs run-time (the §31 scheduler lesson):** the factory must NOT
  query Cloud SQL at parse time (the scheduler re-parses constantly; a slow/down
  DB would take down *all* scheduling). Instead, `pipeforge registry export`
  writes `dags/registry_snapshot.json`; the factory builds DAGs from the file;
  CI/CD refreshes it on registry change. Metadata-driven, but parse-safe — a
  genuinely staff-level detail.
- **`execution_date`/`data_interval` is the spine of correctness:** every task gets
  the logical date via Jinja (`{{ ds }}`), which is what makes `airflow dags
  backfill` equal "re-run history safely" (§13's parameter-change-not-code-change).

## 2. Build

### 2.1 Local Airflow — `docker/docker-compose.airflow.yml`

Use the official Airflow 2.9+ compose (LocalExecutor, Postgres metadata DB),
mounting `./dags` and your wheel. Add `PF_*` env vars. `docker compose up` →
http://localhost:8082. (Composer would cost ~$300+/mo idle; local is where DE
teams actually develop DAGs anyway. You'll do a Composer excursion in 2.6.)

### 2.2 The factory — `dags/dag_factory.py`

```python
"""Generates one standardized DAG per active dataset from registry_snapshot.json.

DAG shape (charter §5):
  preflight >> ingest_raw >> dq_raw >> promote_odp >> promote_fdp
            >> dq_fdp >> build_cdp >> reconcile >> publish
DQ/recon tasks are no-op stubs until Phase 8 flips them on. Tenant → pool.
"""
import json, pendulum
from pathlib import Path
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.dataproc import DataprocCreateBatchOperator

SNAPSHOT = json.loads((Path(__file__).parent / "registry_snapshot.json").read_text())

def make_dag(ds_cfg: dict) -> DAG:
    dag = DAG(
        dag_id=f"pf_{ds_cfg['name']}",
        schedule=ds_cfg["schedule_cron"],
        start_date=pendulum.parse(ds_cfg["start_date"]),
        catchup=False,                      # backfills are explicit, never accidental
        max_active_runs=1,                  # serialize per-dataset (SCD2 must not race itself)
        default_args={
            "retries": 2,
            "retry_delay": pendulum.duration(minutes=5),
            "retry_exponential_backoff": True,
            "execution_timeout": pendulum.duration(hours=1),
            "sla": pendulum.duration(minutes=ds_cfg["sla_freshness_minutes"]),
        },
        tags=["pipeforge", ds_cfg["tenant"], ds_cfg["load_pattern"]],
    )
    with dag:
        ingest = PythonOperator(
            task_id="ingest_raw",
            python_callable=run_ingest,      # thin wrapper: pipeforge ingest --dataset X --execution-date {{ ds }}
            op_kwargs={"dataset": ds_cfg["name"], "execution_date": "{{ ds }}"},
            pool=f"tenant_{ds_cfg['tenant']}",
        )
        promote_odp = DataprocCreateBatchOperator(          # submit; don't process (§31)
            task_id="promote_odp",
            batch=standardize_batch_spec(ds_cfg, "{{ ds }}"),
            region="us-central1",
        )
        ...
        chain(preflight, ingest, dq_raw, promote_odp, promote_fdp, dq_fdp,
              build_cdp, reconcile, publish)
    return dag

for cfg in SNAPSHOT["datasets"]:
    if cfg["active"]:
        globals()[f"pf_{cfg['name']}"] = make_dag(cfg)     # module-level = discoverable
```

Details that matter (each is an interview point):
- **`catchup=False` + explicit backfill** — accidental catchup on a new DAG with a
  2-year start_date is a classic self-inflicted incident.
- **`max_active_runs=1`** — MERGE-based FDP jobs must not run concurrently for
  overlapping keys; serialization is the cheap correctness fix.
- **Pools per tenant** — your first multi-tenancy control (fairness; one tenant's
  backfill can't starve another). Expanded in Phase 12.
- File-drop datasets get a **deferrable GCS sensor** (`GCSObjectsWithPrefixExistenceSensorAsync`)
  as preflight — deferrable = doesn't occupy a worker slot while waiting (know why).
- Streaming datasets get a different template: a sensor-style DAG that *monitors*
  the Kafka consumer (lag threshold → alert) rather than moving data.

### 2.3 Audit + lineage wiring

Task callbacks (`on_success_callback` / `on_failure_callback` / `sla_miss_callback`)
write to `pipeline_run` (adding `airflow_dag_id`, `airflow_run_id`) — the ⑧ audit
model now captures orchestration reality. The `publish` task stamps dataset
freshness in the registry (consumed by the Phase 10 SLA monitor and the Phase 11 catalog).

### 2.4 Backfill, first-class — `pipeforge backfill`

```bash
pipeforge backfill --dataset orders --start 2026-06-01 --end 2026-06-14 \
  --layers odp,fdp,cdp --parallelism 3 --priority recent-first
```

Implementation: either drive `airflow dags backfill` or (better, and more
portable) invoke the same task functions directly with the date range, pooled by
`--parallelism`, **recent-first** by default (§13: stakeholder-visible dashboards
heal fastest). It works *because* every phase before this one was idempotent —
backfill is where your discipline pays out. Log a `pipeline_run` row per
(date, layer) like any other run; notify downstream (print the §13 mantra:
"never backfill silently").

### 2.5 Failure-handling hardening

- Alerting callback → Slack webhook (or just structured log locally) containing:
  DAG, task, execution_date, error, retry count, **runbook link**, log link — the
  §9 "debuggable at 3am in 30 seconds" alert.
- Circuit breaker in preflight: if the same source failed ≥3 consecutive runs,
  short-circuit to `source_down` state and alert P1 instead of hammering (§8 failure domain 1).

### 2.6 Composer excursion (half a day, then destroy)

Terraform a `composer-3` small environment **or** just read M09 + price it out and
write `docs/adr/0004-airflow-hosting.md`: local/self-managed vs Composer vs
Astronomer/MWAA — cost, upgrade burden, IAM integration, DAG deploy story
(`gcloud storage cp dags/ …/dags/`). If you create it, upload your factory,
watch it run once, **destroy it the same day**. The ADR is the deliverable; the
$15 of Composer time is optional.

### 2.7 Ship it

Tests: factory produces a DAG per active dataset with correct schedule/pool/tags
(`DagBag(include_examples=False).import_errors == {}` — the classic Airflow CI
test), Jinja dates land in op_kwargs, disabled dataset → no DAG. Tag `v0.7.0`.

## 3. Prove it

- [ ] `docker compose up` → all NovaMart DAGs visible, zero import errors, parse time < 2s (no DB at parse!)
- [ ] Trigger `pf_orders` for yesterday: all 9 tasks green; `pipeline_run` has one row per layer with matching `airflow_run_id`
- [ ] Register a brand-new dataset (any public CSV) end-to-end: `pipeforge register …` → export snapshot → **DAG appears and runs with zero new Python** ← this is the money demo
- [ ] 14-day backfill completes; spot-check 3 dates for idempotency (counts unchanged on re-run)
- [ ] Kill a Dataproc task mid-run: retry fires with backoff, audit shows attempt trail

## 4. Break it

Set `catchup=True` on a copy of a DAG with `start_date` 60 days ago and watch the
scheduler queue 60 runs (in a scratch dataset). Kill it, clean up, then write
`docs/incidents/007-accidental-catchup.md` — including how pools and
`max_active_runs` contained the blast radius.

## 5. Interview corner

- **Q7 is now fully yours.** Rehearse the 45-min "ETL framework for 100 sources"
  answer: registry → contract ceremony → parameter-driven engines → DAG factory →
  uniform DQ/audit → onboarding = config. You can demo it live.
- *"How do you do backfills?"* → parameterized dates, idempotent writes,
  recent-first, capped parallelism, notify downstream (§13 verbatim — but from experience).
- *"Airflow limits?"* — parse-time bottleneck (hence snapshot file), no streaming
  (hence the monitor-DAG pattern), XCom size (pass GCS paths, not data) (§31).
- *"Airflow vs Dagster?"* — you can now argue asset-orientation honestly: your
  YAML models + registry ARE software-defined assets; Dagster makes that the
  first-class primitive (§38).

## 6. Stretch goals

- Airflow **Datasets** (data-aware scheduling): `build_cdp` publishes a Dataset;
  a downstream "ML features" DAG is triggered by it instead of cron.
- Add a `pipeforge doctor` command: checks registry↔DAG snapshot drift, orphaned DAGs, missing contracts.
- OpenLineage Airflow provider (preview of Phase 9): task-level lineage events emitted automatically.
