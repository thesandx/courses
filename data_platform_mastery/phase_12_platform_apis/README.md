# Phase 12 — Platform APIs, Secrets & Multi-Tenancy (`v0.12.0`)

> **Mission:** promote PipeForge from "my tool" to "a platform other teams could
> use". A FastAPI control plane (the Registration / Transformation / Workflow
> APIs from the reference architecture's second diagram), secrets done right
> (Secret Manager, the Vault stand-in), machine auth, and a real multi-tenancy
> model with quotas and isolation. This phase is where Q15 (multi-tenant SaaS
> platform) and Q19 (data mesh platform) stop being theory.

## 1. Concepts

- **The reference architecture's control plane** (image 2): Registration UX/API,
  Transformation API, Workflow service, Vault, tenant namespaces on GKE. You'll
  build the same shape with cheaper primitives: Cloud Run instead of GKE+Istio,
  Secret Manager instead of Vault, IAM instead of mTLS meshes. Being able to say
  "same architecture, right-sized runtime — here's what GKE would buy me and when
  I'd move (sidecars, network policy, long-running consumers, per-tenant node
  pools)" is precisely the staff-level judgment interviews probe.
- **Multi-tenancy is an isolation spectrum** (Q15 — memorize the ladder):
  1. **Row-level** (tenant column + row-access policies) — cheapest, weakest blast-radius story;
  2. **Schema/dataset-level** (per-tenant BQ datasets, buckets prefixes, pools) — the pragmatic middle **← PipeForge's choice**;
  3. **Project-level** (per-tenant GCP project) — hard isolation, hard ops;
  4. **Deployment-level** (per-tenant everything) — enterprise/regulated.
  Defend the choice by failure domain, noisy neighbors, compliance, and cost —
  not by fashion.
- **Secrets:** connection secrets were `connection_ref` strings since Phase 2 —
  that indirection now pays off: refs resolve to Secret Manager at runtime,
  per-tenant access via IAM conditions, rotation without touching metadata.
- **AuthN/Z for machines:** service-to-service on GCP = OIDC ID tokens, verified
  audience, caller identity mapped to tenant + role. No API keys in headers.

## 2. Build

### 2.1 FastAPI control plane — `api/`

```
api/
├── main.py            # FastAPI app, OIDC verification middleware
├── routers/
│   ├── registration.py    # POST /sources, /datasets, /contracts (compat-checked)
│   ├── transformation.py  # POST /models  (register a CDP model), GET /models/{id}
│   ├── workflow.py        # POST /runs {dataset, execution_date}, POST /backfills, GET /runs/{id}
│   ├── quality.py         # GET /datasets/{id}/dq, POST /datasets/{id}/rules
│   └── catalog.py         # GET /datasets?q=..., GET /datasets/{id}/lineage
└── schemas.py         # Pydantic request/response models — the API's own contract
```

Design rules (each is an interview line):
- **The API is the only writer to the registry from now on.** CLI and UI become
  API clients. One write path = one place for validation, authz, and audit
  (`api_audit_log`: caller, tenant, action, payload hash, timestamp).
- Contracts in, contracts out: request models are versioned Pydantic schemas;
  breaking the API contract follows the same §16 protocol as data contracts.
  Platforms eat their own dogfood.
- Idempotency keys on POST /runs and /backfills (client retries must not
  double-trigger — the §7 idempotency principle applied to control planes).
- 202 + status polling for long operations (a backfill is a job, not a request).

### 2.2 Secret Manager migration

- Terraform: secrets for MySQL source creds, metadata DB, Kafka SASL (if VM),
  webhook URLs; IAM bindings per accessor SA with **conditions on secret name
  prefix** (`tenant-a-*` readable only by tenant-a runners).
- `connection_ref: sm://novamart-mysql` now resolves via a `SecretResolver` in
  `core/` (cached, TTL, audit-logged access). Delete every password from `.env`
  and Terraform state where possible — do the sweep, it's always embarrassing.
- Rotation drill: rotate the MySQL password via Terraform, confirm pipelines pick
  it up with zero metadata changes. Rotation-without-redeploy is the whole point
  of the indirection.

### 2.3 Multi-tenancy: `tenant` becomes real

`tenant` has been a column since Phase 2. Now enforce it end to end:
1. **Onboard a second tenant** ("acmecorp") with one dataset (any public CSV).
2. **Storage isolation:** per-tenant BQ datasets (`cdp_novamart`, `cdp_acmecorp`)
   and GCS prefixes; Terraform generates them from a `tenants.yaml` (`for_each` —
   adding a tenant is a PR with one YAML line — say that sentence in interviews).
3. **Compute fairness:** per-tenant Airflow pools (P07 groundwork) + per-tenant
   Dataproc batch quotas (max concurrent batches in dataset config).
4. **Access:** per-tenant reader groups; API resolves caller→tenant and scopes
   every query (`WHERE tenant = :caller_tenant` enforced in the repo layer, not
   ad hoc in routes — one chokepoint).
5. **Cost attribution:** `tenant` label on every GCP resource your Terraform
   creates + every Dataproc batch → the Phase-10 FinOps model now reports
   **cost per tenant**. Chargeback-ready is a phrase platform interviewers love.

### 2.4 Deploy + CI/CD completion

- `cloudrun_service` for the API (min 0, `--no-allow-unauthenticated`); UI calls
  it with an ID token.
- GitHub Actions: build+push images on tag, `terraform plan` on PR via
  **Workload Identity Federation** (no SA keys in GitHub — keyless CI is current
  best practice and a strong interview aside), apply on merge with manual approval
  environment.

### 2.5 Ship it

Tests: authz (tenant A token cannot read tenant B dataset — write the test that
proves it), idempotency-key replay, secret resolver caching, contract-versioned
API schemas. Tag `v0.12.0`.

## 3. Prove it

- [ ] `curl` with tenant-A ID token: sees only tenant-A datasets; tenant-B's return 404 (not 403 — don't leak existence; small detail, real security habit)
- [ ] Wizard (P11) now writes through the API; `api_audit_log` shows the human's action chain
- [ ] Both tenants' DAGs run concurrently; pools prevent starvation when tenant A backfills 30 days
- [ ] FinOps dashboard shows cost split by tenant
- [ ] Password rotation with zero pipeline edits
- [ ] `git grep -iE 'password|secret_key'` finds nothing but Secret Manager refs

## 4. Break it

Noisy-neighbor drill: give tenant B a pathological dataset (10x volume, a
cross-join-ish model) and run both tenants' schedules. Where does contention
actually appear first — Airflow pool? Dataproc quota? BQ slots? Cloud SQL
connections? Measure, fix the weakest fence, write
`docs/incidents/013-noisy-neighbor.md`. (Interviewers ask "how do you isolate
tenants?" — you'll answer with where isolation *actually broke first*.)

## 5. Interview corner

- **Q15 (multi-tenant SaaS data platform)** — full 45-min run. Your isolation
  ladder + the noisy-neighbor incident + per-tenant cost attribution is a
  staff-grade answer; most candidates have never operated tenancy at all.
- **Q19 (data mesh)** — you now hold all four pillars concretely: domain
  ownership (owner per dataset), data-as-product (catalog cards + SLAs),
  self-serve platform (wizard/API), federated governance (contracts + policy tags
  + central DQ minimums). Argue *when mesh is premature* (§25's <50-engineer rule)
  — restraint impresses more than enthusiasm.
- *"How do services authenticate to each other on GCP?"* — SA identity + OIDC ID
  tokens + audience verification; secrets only for third-party systems.

## 6. Stretch goals

- Reverse ETL (§28): `POST /syncs` pushing a CDP segment to a mock CRM webhook, idempotent upserts on business key, rate-limited.
- Per-tenant CMEK (tenant-supplied keys) — the enterprise ask; design doc even if you don't build it.
- Migrate the API+UI to GKE Autopilot with the Terraform module — experience the reference architecture's actual runtime, then destroy it.
