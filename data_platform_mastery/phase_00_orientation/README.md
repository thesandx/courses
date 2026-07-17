# Phase 00 — Orientation & Ground School

> **Mission:** set up your machine, your GCP project, and your head. No PipeForge
> code yet — but you leave this phase with cost guardrails armed, tooling verified,
> the target architecture drawn from memory, and your first volume-estimation done.

## 1. Concepts

**Read now (in this order):**
- System-design notes **§1–§2** — how DE interviews differ from SWE, and the 7-step framework. This course is the framework made physical.
- Notes **§5** — the 6-layer architecture. PipeForge is that diagram.
- GCP course **M01 Foundations** — projects, IAM, resource hierarchy, `gcloud`.
- The two docs at the course root: **PROJECT_CHARTER.md** and **INTERVIEW_MAP.md**.

**The mental model for the whole course:**

> DE system design starts from the **source** and works **forward** (§1). So does
> this course: phases 2–4 are sources and ingestion, 5–6 are processing and
> serving, 7–10 are the cross-cutting spine (orchestration, quality, governance,
> observability), 11–12 are the product surface, 13–14 are scale and launch.

**Why "metadata-driven" is the theme:** the staff-level version of almost every
platform question (Q7, Q15, Q19) is "how do you make the *N+1th* source cost ~zero
engineering?" The answer is always: a registry + a generic engine + generated
orchestration. Hold that sentence; you'll implement it for 12 phases.

## 2. Build

### 2.1 Local tooling

```bash
# Python 3.11+, uv (or pipx/poetry), Docker Desktop / Engine, Terraform >= 1.7, git
python3 --version          # 3.11+
docker --version && docker compose version
terraform -version
# gcloud CLI (includes bq + gsutil): https://cloud.google.com/sdk/docs/install
gcloud init
gcloud auth login
gcloud auth application-default login    # ADC — what Terraform & client libs use
```

### 2.2 GCP project + THE BUDGET (do this before anything else)

```bash
export PROJECT_ID="pipeforge-$(whoami)-dev"    # must be globally unique
gcloud projects create "$PROJECT_ID"
gcloud billing accounts list                    # note ACCOUNT_ID
gcloud billing projects link "$PROJECT_ID" --billing-account=ACCOUNT_ID
gcloud config set project "$PROJECT_ID"

# Budget with alerts at 50/90/100% of $25 — the seatbelt for the entire course
gcloud services enable billingbudgets.googleapis.com
gcloud billing budgets create \
  --billing-account=ACCOUNT_ID \
  --display-name="pipeforge-guardrail" \
  --budget-amount=25USD \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
```

In Phase 1 you'll re-create this budget in Terraform — clicking first, codifying
second is the allowed workflow (course ground rule #1).

**Cost model of the course** (so nothing surprises you):

| Resource | Phase | Cost behavior | Guardrail |
|---|---|---|---|
| GCS + BigQuery storage | 3+ | pennies at demo volume | lifecycle rules (P09) |
| BigQuery queries | 6+ | $6.25/TB scanned | partition filters + `maximum_bytes_billed` |
| Cloud SQL db-f1-micro | 2+ | ~$9/mo if left running | `gcloud sql instances patch ... --activation-policy=NEVER` when idle |
| Dataproc **Serverless** | 5+ | per-second while a batch runs | nothing idles; still, small data |
| Kafka VM (e2-small, optional) | 4 | ~$13/mo if left running | run Kafka in Docker locally; VM only for the cloud drill, then stop |
| Airflow | 7 | $0 (local Docker) | Composer is a read-only excursion unless you accept ~$300+/mo |
| Cloud Run (API+UI) | 11–12 | scale-to-zero ≈ $0 | min instances = 0 |

### 2.3 Estimation drill (your first interview rep — §4, §19)

On paper, no calculator, estimate for NovaMart (numbers in the charter §2):

1. Clickstream: 500 ev/s × 400 B → GB/day raw? Parquet (÷5–10)? Events/day?
2. If peak = 3× average, how many Kafka partitions at ~10K msgs/s each?
3. `orders` at 100k rows/day × 1 KB — does this need Spark? (Scale thresholds, §3.)
4. 90 days of RAW clickstream in GCS Standard at $0.02/GB-mo — monthly cost?

<details><summary>Answers</summary>

1. 500×400 B = 200 KB/s ≈ **17 GB/day** raw ≈ 2–3.5 GB/day Parquet; 43.2M events/day.
2. Peak 1,500 ev/s → **1–2 partitions** suffice; provision 6 for headroom/keyed parallelism (small numbers are a *correct* answer — say so).
3. 100 MB/day — **pandas/BQ load, no Spark needed** for ingestion; Spark earns its place on clickstream + SCD2 merges.
4. ~1.5 TB × $0.02 ≈ **$30/mo at full production volume**; at demo volume (~5%) ≈ $1.5. This is why the course caps generator throughput.
</details>

### 2.4 Architecture redraw

Close everything. On a whiteboard/paper, redraw the PipeForge architecture:
6 layers left→right, the metadata core underneath driving ingestion, the
cross-cutting bar (workflow, DQ, recon, audit, tokenization, archival, lineage).
Compare against the README diagram. Repeat until the redraw takes < 3 minutes —
you will draw exactly this in interviews.

### 2.5 Create your empty GitHub repo

Create a **public** repo named `pipeforge` (or your own name — check it's not
taken if you care about uniqueness), empty, no README. Phase 1 makes the first commit.

## 3. Prove it

- [ ] `gcloud config get-value project` prints your project; budget visible in console
- [ ] `terraform -version` ≥ 1.7; Docker runs `hello-world`
- [ ] ADC works: `python -c "import google.auth; print(google.auth.default()[1])"` prints the project
- [ ] Estimation drill answers within 2× of the key
- [ ] Architecture redraw < 3 min
- [ ] Empty GitHub repo exists

## 4. Interview corner

Rehearse the opening move you'll use in every real interview (§2 power move):

> "I'll walk through requirements, sources and volumes, architecture, data model,
> pipeline design, deep dives, then monitoring and SLAs. Does that work for you?"

Then deliver a 2-minute overview of PipeForge as if the interviewer asked
"design an ETL platform" — using only the charter. Record yourself. Cringe. Repeat.

## 5. Stretch goals

- Read notes **§10 (Top 15 mistakes)** and pin it above your desk.
- Do GCP course **M01 practice questions**; start a PDE-exam error log.
