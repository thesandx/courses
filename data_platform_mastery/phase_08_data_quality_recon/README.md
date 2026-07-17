# Phase 08 — Data Quality & Reconciliation Frameworks ④⑦ (`v0.8.0`)

> **Mission:** the platform learns to distrust itself. A declarative DQ engine
> evaluates rules across the **6 dimensions of data quality** at every layer
> boundary, with calibrated severity actions (warn / quarantine / block). A
> reconciliation framework proves source↔RAW↔ODP↔FDP↔CDP agreement every day —
> and catches the hard-delete drift you've been quietly accumulating since Phase 3.

## 1. Concepts

Read notes **§8 (quality deep dive)**, **§9 (three pillars)**, **Q9 (DQ monitoring
framework)**; GCP **M10** (Dataplex data quality — the managed comparison).

**The 6 dimensions ④** (the reference architecture names them explicitly; know
them cold, with one NovaMart example each):

| Dimension | Question | NovaMart rule example |
|---|---|---|
| **Completeness** | Is everything there? | orders row count within ±2σ of trailing 30-day mean; null-rate(customer_id) < 0.1% |
| **Accuracy** | Does it match reality? | `SUM(line_amount_usd)` reconciles to source manifest ±0.1% |
| **Consistency** | Does it agree with itself/other data? | every `fct_order_lines.customer_sk` exists in `dim_customers` (referential); ODP count == FDP count |
| **Timeliness** | Is it fresh? | `MAX(order_ts)` within SLA window; partition for D exists by 06:00 |
| **Validity** | Does it conform to rules/formats? | `status ∈ enum`, `quantity ≥ 1`, `order_ts` not in future |
| **Uniqueness** | No duplicates? | zero duplicate `order_line_id` per partition |

**The golden rule (§8):** every check either passes-and-proceeds,
fails-and-alerts, or fails-and-quarantines-the-bad-rows. **Never block silently.**
Severity is calibrated to impact: 0.01% null PKs → quarantine+alert; 50% row-count
drop → block+page. Your engine encodes this as `severity: warn|quarantine|block`.

**Reconciliation ⑦ is a different discipline than DQ** — DQ asks "is this dataset
internally healthy?"; recon asks "did anything get lost or invented **between**
systems?" Banks run recon as a dedicated framework because at-least-once pipelines
+ incremental extracts *will* drift (§12: watermarks miss hard deletes — today you
finally catch the ones Phase 3's churn generator has been deleting).

**Recon check types** (cheapest first — run cheap ones always, expensive ones sampled/weekly):
1. **Count**: rows per execution_date across layer pairs.
2. **Aggregate**: SUM/MIN/MAX of key measures (revenue!) across layers.
3. **Hash/checksum**: `BIT_XOR(FARM_FINGERPRINT(CONCAT(cols)))` per partition — near-free row-level comparison without moving data.
4. **Full outer diff** (forensic, on demand): which keys differ — the drill-down tool once 1–3 flag a delta.

## 2. Build

### 2.1 DQ engine — `src/pipeforge/quality/`

Rules already live in the registry (Phase 2 `dq_rule` table + model YAML `tests:`
blocks — unify them now: the builder registers model tests as dq_rules).
Implement `rule_types` as small classes that compile to SQL:

```python
class NotNull(Rule):
    dimension = "completeness"
    def to_sql(self, target: Table) -> str:
        return f"""SELECT COUNTIF({self.column} IS NULL) AS bad, COUNT(*) AS total
                   FROM `{target.fqn}` WHERE {target.partition_filter}"""

class VolumeAnomaly(Rule):
    dimension = "completeness"
    # observed vs trailing N-day mean/stddev from pipeline_run history — the audit
    # model ⑧ feeding the DQ framework ④: platform components compound.

class Freshness(Rule):
    dimension = "timeliness"   # MAX(business_ts) vs now, threshold from dataset.sla_freshness_minutes

class AcceptedValues(Rule): dimension = "validity"
class Unique(Rule):         dimension = "uniqueness"
class ForeignKeyExists(Rule): dimension = "consistency"
class ReconcilesTo(Rule):   dimension = "accuracy"
```

`engine.py` — evaluate all active rules for (dataset, layer, execution_date),
write `dq_result` rows (observed value, threshold, pass/fail, sample bad rows as
JSON ≤ 20), then **apply the action ladder**:

```python
def enforce(results: list[DqResult]) -> None:
    blockers = [r for r in results if r.failed and r.severity == "block"]
    quarantines = [r for r in results if r.failed and r.severity == "quarantine"]
    for r in quarantines:
        move_bad_rows(r)        # DELETE ... to quarantine table with rule_id + run_id attached
        alert(r, level="P2")
    if blockers:
        alert(blockers, level="P1")
        raise DqGateFailed(blockers)      # Airflow task fails -> downstream never runs on bad data
```

Flip on the Phase-7 stub tasks: `dq_raw` (baseline five: rowcount, null PKs,
freshness, volume anomaly, dup PKs — §8 says these catch ~80%) and `dq_fdp`
(referential integrity, accuracy recons, business rules).

### 2.2 Scorecard data

A nightly job aggregates `dq_result` into `cdp.dq_scorecard`
(dataset × dimension × day → pass rate, worst offenders, trend). This table *is*
the Phase 11 DQ dashboard's backend — and mirrors the "DQ Scorecard" panel in the
reference architecture's UI block.

### 2.3 Reconciliation framework — `src/pipeforge/recon/`

```python
CHECKS = [
    ReconCheck("orders", "count",  left=("raw", "manifest_rows"), right=("odp", "count(*)")),
    ReconCheck("orders", "count",  left=("odp",), right=("fdp",)),
    ReconCheck("orders", "sum",    left=("fdp", "SUM(quantity*unit_price_usd)"),
                                   right=("cdp.fct_order_lines", "SUM(line_amount_usd)"), tol_pct=0.1),
    ReconCheck("customers", "count", left=("source_mysql", "SELECT COUNT(*) ..."),
                                     right=("fdp.dim_customers", "COUNTIF(is_current)")),  # ← the delete-catcher
    ReconCheck("clickstream", "hash", left=("odp",), right=("fdp.fct_sessions", "events_sum")),
]
```

Results → `recon_result` table; failures alert with **both values and delta_pct**
(an alert that says "left=1,000,000 right=999,400 (-0.06%)" is debuggable; "recon
failed" is not — §9 alert anatomy). Add `pipeforge recon run --dataset X --date D`
and wire the Phase-7 `reconcile` task to it.

**The payoff moment of the course:** the `customers` source-vs-FDP count check
FAILS — the churn generator has been hard-deleting customers since Phase 3 and
your watermark loader never saw them (§12's exact warning). Handle it properly:
quantify drift, add a weekly full-extract reconciliation-and-repair job (or the
Debezium stretch from Phase 5), document in
`docs/incidents/008-hard-delete-drift.md`. This incident is *the* CDC interview
story (Q5) — you lived it.

### 2.4 Calibration pass

Run everything for 7 generated days, then **tune**: which rules flapped? Loosen
thresholds where noise, tighten where real. Delete one useless rule. Alert
fatigue is the #1 reason incidents go undetected (§9) — practicing calibration is
practicing the job.

### 2.5 Ship it

Tests: each rule type compiles + evaluates against fixtures; action ladder
(block raises, quarantine moves exactly the bad rows and preserves conservation
`good + quarantined == input`); recon math incl. tolerance edges. Tag `v0.8.0`.

## 3. Prove it

- [ ] All NovaMart datasets have the baseline-5 auto-attached (registered datasets get defaults — config, not code)
- [ ] Inject 5% null customer_ids in the generator → quarantine fills, pipeline proceeds, P2 logged
- [ ] Drop the day's file volume to 10% → **block** fires, downstream tasks never ran, P1 alert has observed/threshold/history
- [ ] `dq_scorecard` shows 7 days of per-dimension pass rates
- [ ] Hard-delete recon failure detected, root-caused, repaired; counts converge after the repair job
- [ ] Re-run a blocked date after fixing data → gate passes, everything downstream heals with no manual cleanup

## 4. Break it

The subtle one: make the generator produce *valid but wrong* data — every
`unit_price_usd` divided by 100 (the cents/dollars semantic bug, §16). Schema
passes, nulls pass, uniqueness passes… only the **accuracy** recon
(sum-vs-manifest) and **distribution** check (avg order value 85→0.85) catch it.
Write `docs/incidents/009-silent-semantic-corruption.md`. Lesson: schema
validation is necessary, never sufficient — the reason the 6 dimensions exist.

## 5. Interview corner

- **Q9 (DQ framework) is now a lived answer**: rules as metadata → compiled to SQL
  → evaluated at layer boundaries → severity ladder → scorecard → calibration.
  Deliver it in 45 minutes with your architecture as the diagram.
- *"How do you know your numbers are right?"* (staff favorite, usually asked
  casually) → three-part answer: DQ dimensions at boundaries, cross-layer
  reconciliation with tolerances, and the audit model making every row count
  traceable end-to-end.
- Recite: "every check passes-and-proceeds, fails-and-alerts, or
  fails-and-quarantines — never block silently" and give your 10%-volume story.
- Compare build-vs-buy honestly: your engine vs dbt tests vs Great Expectations vs
  Dataplex auto-DQ vs Monte Carlo (§8 tools + M10) — you now know exactly what
  the paid tools are selling.

## 6. Stretch goals

- Anomaly detection v2: seasonality-aware bands (day-of-week means) instead of flat ±2σ.
- Recon "forensic mode": key-level FULL OUTER diff materialized to a debug table.
- Publish DQ results as OpenLineage facets (feeds Phase 9 lineage).
