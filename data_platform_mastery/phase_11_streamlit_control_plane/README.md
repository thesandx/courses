# Phase 11 — The Streamlit Control Plane (`v0.11.0`)

> **Mission:** give the platform a face. A multi-page Streamlit app — the "UI: DQ
> Scorecard / Search Catalog / Build Job / Operations" block from the reference
> architecture — that turns 10 phases of backend into something a stakeholder can
> *see*: search the catalog, read a dataset's health, watch pipelines run, trigger
> a backfill, and onboard a brand-new source through a wizard. This app is also
> your interview demo and the screenshots in your README.

## 1. Concepts

- **The control plane reads metadata, never the data plane directly.** Every page
  is a query against the registry/audit/DQ/recon/lineage tables (Cloud SQL) plus
  the `cdp.dq_scorecard` and `agg_*` tables (BigQuery). If a page needs raw data,
  the design is wrong — this discipline is why the app stays fast and safe.
- **Why a UI matters for a platform (Q7/Q15/§25):** self-serve is the difference
  between "a framework" and "a platform". The mesh pillar "self-serve data
  platform" concretely means: a domain engineer onboards a source *without
  talking to you*. The wizard is that promise.
- Streamlit's tradeoff (say it honestly in interviews): fastest possible
  data-team UI, fine for internal tools at modest concurrency; you'd reach for
  React+API at product scale. Knowing the boundary is the senior signal.

## 2. Build

### 2.1 App skeleton — `ui/`

```
ui/
├── Home.py                      # platform overview: datasets, runs today, SLA status, cost sparkline
├── pages/
│   ├── 1_🔍_Catalog.py          # search + dataset detail
│   ├── 2_✅_DQ_Scorecard.py     # the ④ scorecard
│   ├── 3_⚙️_Operations.py       # runs, failures, backfill trigger
│   ├── 4_🧬_Lineage.py          # graph from lineage_edge
│   ├── 5_🧾_Recon.py            # reconciliation results
│   └── 6_➕_Onboard_Source.py   # the wizard
├── lib/                         # cached data access (st.cache_data over repo calls)
└── Dockerfile
```

Data access rules: `st.cache_data(ttl=60)` on every query function; a read-only
DB role for the UI (`pf_ui_readonly` — least privilege applies to your own apps
too); BigQuery via the builder's client with `maximum_bytes_billed` set. 

### 2.2 The pages (what "done" looks like)

**Home:** counts (datasets, sources, runs today by status), SLA breach banner,
7-day cost sparkline, DQ pass-rate big-number. One screen that answers "is the
platform healthy?" — your Phase 10 pillars, humanized.

**Catalog 🔍 (the ⑪ face):** search box over name/owner/tags/columns (contract
JSON makes column search free); dataset page shows: description, owner, layer
badges, freshness ("data complete through 2026-07-16 23:59" — the §17 honesty
stamp), schema table from the current contract with PII 🔒 badges on tokenized
columns, SLA, retention policy, last 14 runs as a status strip, and its DQ score.
This page **is** a data-product card (§25) — it should read like documentation you'd
be proud to hand an analyst.

**DQ Scorecard ✅:** heatmap dataset × dimension (pass rate, 14 days); drill-down
to failing rules with observed-vs-threshold history charts and sample bad rows
(from `dq_result.sample_rows`). Mirror of the reference architecture's "DQ
Scorecard" panel.

**Operations ⚙️:** live runs table (auto-refresh), failure drill-down (error,
attempt count, log link), and two write actions behind a confirm dialog:
*trigger run* and *backfill date-range* (calls the Phase-12 API — for now, the
Airflow REST API / `pipeforge` subprocess). Write actions are logged to
`ui_action_log` (who clicked what — the audit habit extends to humans).

**Lineage 🧬:** `graphviz_chart` (or streamlit-agraph) of `lineage_edge`,
clickable from the catalog. Select a node → upstream/downstream lists — the §14
impact-analysis workflow as a picture.

**Recon 🧾:** per dataset/day: left vs right values, delta%, pass/fail history —
the page you'd pull up in the "are the numbers right?" meeting.

**Onboard Source ➕ (the money page):** a 4-step wizard — source details →
dataset config (pattern, keys, dates, PII multiselect, SLA) → contract upload
(validated live, compat-checked against any previous version) → review & submit.
Submit calls the registration layer, then shows: "✅ registered — DAG `pf_<name>`
will appear on next snapshot export." Then demo it end-to-end with a fresh
public dataset and time yourself. **Under 10 minutes from wizard to queryable CDP
data is the platform's headline claim — measure it honestly.**

### 2.3 Deploy — Cloud Run

Dockerfile (multi-stage, `pip install .` + `streamlit run ui/Home.py`), Artifact
Registry, `cloudrun_service` Terraform module: min-instances 0 (scale-to-zero ≈
free), Cloud SQL connector, service account `pf-ui`, and **do not make it
public** — either IAP/identity-aware access or `--no-allow-unauthenticated` +
`gcloud run services proxy` for demos. An open control plane with a backfill
button is an incident generator; saying *why* it's locked down is part of the demo.

### 2.4 Ship it

Screenshot every page into `docs/img/` (Phase 14 README uses them). Tag `v0.11.0`.

## 3. Prove it

- [ ] Catalog search "email" finds `customers` via column-level match, PII badge shown
- [ ] Scorecard reproduces the Phase-8 incidents visually (the 10%-volume day is red)
- [ ] Backfill triggered from Operations actually runs and appears in the runs table
- [ ] Lineage page answers "what breaks if `dim_customers` changes?" in one click
- [ ] Wizard onboarding of a never-seen dataset → queryable in CDP in < 10 min, zero code
- [ ] App on Cloud Run, locked down, cold-starts under ~10s, costs ~$0 idle

## 4. Break it

Let the UI's BigQuery queries run without `maximum_bytes_billed` and add an
innocent-looking "All time" filter to the scorecard → watch a full-table scan.
Set the cap, watch the query get rejected, add date-bounded defaults. Small
lesson, real habit: **UIs are query-cost amplifiers** (50 users × auto-refresh ×
unbounded scan = the §15 horror story). `docs/incidents/012-ui-cost-amplifier.md`.

## 5. Interview corner

- The 10-minute live demo script (write it, rehearse it): Home health → catalog
  card → wizard onboard → DAG appears → run flows → scorecard updates → lineage →
  backfill. This demo IS your answer to Q7 — bring a laptop to onsites.
- *"How do analysts discover and trust data?"* — catalog card: owner, SLA,
  freshness stamp, DQ score, lineage, contract. Trust is *shown*, not asserted.
- *"How do you expose platform capabilities to other teams?"* — UI for humans,
  API for machines (Phase 12), both over the same metadata core. Clean answer,
  and literally your architecture.

## 6. Stretch goals

- "Playground" page: run a template-guarded query against any CDP product (dropdown, date range) with bytes-billed shown after — teaches users cost visibly.
- Dark-launch a "Request access" button writing to a `access_request` table — governance workflow seed.
- Usage analytics: log page views into BigQuery, build `agg_ui_usage` with your own builder (dogfood again).
