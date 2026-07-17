# Phase 14 — Open-Source Launch, Docs & the Resume Payload (`v1.0.0`)

> **Mission:** ship it to the world. Turn fourteen phases of engineering into a
> polished open-source project (docs, demo mode, contribution guide, release),
> and convert the whole journey into resume bullets, a portfolio narrative, and
> interview-day logistics. The code was the work; this phase is the career payoff.

## 1. Concepts

Open-source credibility signals reviewers actually check, in order: a README
that explains the architecture in 90 seconds, a way to try it in minutes, CI
badges that are green, docs that show operational maturity (runbooks, incident
files — you have these!), a license, and evidence of real releases. Stars are
vanity; *"I read the code and it's clearly production-shaped"* is the reaction
you're engineering.

## 2. Build

### 2.1 The README (the most-read file you'll write this year)

Structure — study 3 good platform READMEs first (Airflow, Dagster, DataHub) —
then write:
1. One-paragraph pitch (charter §0) + badges (CI, license, release).
2. **Architecture diagram** (clean mermaid or draw.io export of the course
   diagram) + the 11-capability table with ✅s.
3. 90-second feature tour with the Phase-11 screenshots (catalog, scorecard,
   wizard, lineage).
4. **Quickstart** (see demo mode below) — a reader must reach "wow" in <15 min.
5. Design docs index: link the ADRs, the 100x doc, the scale report, incidents.
   (Publishing your incident files is unusual and *deeply* credible.)
6. Roadmap + contributing + license.

### 2.2 Demo mode — `pipeforge demo up`

The single highest-ROI feature for an open-source data platform: one command
that runs the whole thing **locally without a GCP account** where possible:
docker compose (Kafka, MySQL, Postgres, Airflow, Marquez, MinIO standing in for
GCS via its S3/GCS-ish interface — or a `--local-fs` storage backend you add
behind the storage client), seeded generators, and a `--with-gcp` flag for the
real thing. Write the storage backend as an interface (`GcsStore | LocalStore`)
— a refactor that also makes unit tests faster. Budget 2–3 days; it's worth it.

### 2.3 Docs site — `mkdocs-material` on GitHub Pages

`docs/`: Getting started · Concepts (layers, registration, contracts) · Operator
guide (runbooks, alerts) · API reference (FastAPI's OpenAPI embedded) ·
Design/ADRs · Incident library. Deploy via the existing Actions on tag.

### 2.4 Release engineering

- `CHANGELOG.md` from your phase tags (you have a real history — flaunt it).
- `release.yml`: on tag → tests → build wheel + images → GitHub Release notes.
- Cut **`v1.0.0`** with the definition-of-done demo (charter §9) recorded as a
  5-minute screen capture linked in the README. The video is your async interview.

### 2.5 The resume payload (do not skip this — it's why you came)

**Resume bullets** — adapt, keep the numbers honest, one line each:

- Built and open-sourced **PipeForge**, a metadata-driven data platform on GCP
  (Terraform, Kafka, Spark/Dataproc, Airflow, BigQuery, Streamlit): source
  onboarding to queryable star-schema data in <10 minutes with zero per-source code.
- Designed a lakehouse (RAW/ODP/FDP/CDP) with SCD Type-2 history, deterministic
  surrogate keys, and idempotent MERGE/partition-overwrite writes — verified
  effectively-once delivery from an at-least-once Kafka pipeline.
- Implemented a 6-dimension data-quality framework and cross-layer reconciliation
  that caught hard-delete drift and silent semantic corruption in chaos drills;
  DQ scorecard and lineage served via a Streamlit control plane.
- Ran 10x load and chaos testing (source outages, poison messages, mid-write
  kills, schema breaks); cut a skewed Spark stage 40→6 min via salting + AQE;
  documented 10+ incidents with runbooks.
- Built platform FinOps: billing export modeled in the platform itself, cost per
  tenant and per million rows tracked; partition/rollup tuning cut dashboard
  bytes-billed >10x.

**The portfolio narrative** (write `docs/story.md`, 1 page): why → constraints
(solo, $25/mo) → key decisions with tradeoffs → what broke and what it taught →
what you'd do differently. Interviewers who read it will spend the hour on *your*
territory.

**Interview-day logistics:** pin the repo on GitHub; put the demo video link in
your resume header; prepare the 10-min live demo (P11) and a 2-min no-laptop
whiteboard version; print your three best war stories.

### 2.6 Announce it

LinkedIn post + a technical blog post ("How I built a metadata-driven data
platform on GCP for $25/month" — outline: the Q7 problem, the registry insight,
3 hardest bugs from your incident files, the numbers). Submit to
r/dataengineering. Expect silence or feedback; both are useful. Respond to every
issue like a maintainer — that thread is *also* interview evidence.

## 3. Prove it

- [ ] A friend (not you) goes README → demo mode → onboards a source in <30 min without help — watch them, fix every stumble
- [ ] Docs site live; CI badges green; `v1.0.0` released with the demo video
- [ ] `pipeforge demo up` works on a clean machine (test in a fresh VM/container)
- [ ] Resume updated; story doc written; demo rehearsed twice cold
- [ ] All 11 capability boxes in the README checked, each linking to code + docs

## 4. Break it

Have your reviewer friend file their confusion as GitHub issues, then triage and
fix like a maintainer for a week. Open source is a support commitment; feeling a
little of it is part of the education.

## 5. Interview corner — the endgame

Now go to the **[Interview Gauntlet](../interview_gauntlet/README.md)** and run
all 20 questions against a timer over 3–4 weeks. Then re-read the *entire*
system-design notes end-to-end one last time: it will read like a description of
your own repo — which was the plan all along.

## 6. Stretch goals (post-1.0 roadmap = your "future work" interview answer)

- Debezium-based CDC connector as a first-class load pattern (§23/§37)
- Iceberg-native ODP/FDP with time travel as the rollback story (§35)
- Flink hot path for a sub-second fraud demo (§36, Q13)
- dbt adapter: let teams bring dbt projects as CDP builders (§32)
- Data-diff CI: PR-time recon between prod and dev model outputs
