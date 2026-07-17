# Phase 09 — Governance: Tokenization, Lineage, Archival, Catalog ③⑨⑪ (`v0.9.0`)

> **Mission:** the platform grows a conscience. PII is tokenized before it leaves
> RAW ③, every job emits lineage that answers "who breaks if I change this?" ⑪,
> data ages through storage tiers and dies on schedule ⑨, and everything is
> discoverable in a governed catalog. This phase is what makes the project
> credible to anyone who has worked in a bank — which is exactly what the
> reference architecture is.

## 1. Concepts

Read notes **§14 (lineage)**, **§16 (contracts/PII)**, compliance bullets in
**§3**; GCP **M10 (governance & security)** — this phase is M10 made real.

**Tokenization ③ — why tokens and not just masking/encryption?**
- *Masking* destroys utility (can't join on `j***@x.com`).
- *Plain encryption* is reversible wherever the key is — and ciphertext differs
  per row/nonce, so joins break.
- **Deterministic tokenization** replaces `email` with a stable token: same input
  → same token, so **joins, GROUP BYs, and COUNT DISTINCTs still work** across
  every table, while re-identification requires the KMS-held key. That property —
  *referential integrity preserved, PII removed* — is the whole point, and a
  sentence interviewers reward.
- Where: at ODP→FDP promotion. RAW keeps original (locked-down bucket, short
  retention); FDP/CDP — the layers analysts touch — carry only tokens. Tightly
  scoped detokenization on demand.
- GDPR **right-to-delete** becomes: delete the customer's row in the token
  vault / crypto-key material and the tokens across 200 tables become permanently
  meaningless — **crypto-shredding**. Compare with the alternative (DELETE across
  every derived table + backfills) and you understand why this pattern exists.

**Lineage ⑪ (§14):** table-level first (70% of value, 20% of effort). You have an
unfair advantage: every movement already flows through *your* framework code, so
lineage capture is one emit call per task — no log parsing. OpenLineage is the
open standard (job/run/dataset events); Dataplex catalogs the BigQuery side
automatically.

**Archival & purge ⑨ (§15 storage tiers):** hot → Nearline/Coldline/Archive →
delete, driven by the `archival_policy` metadata per dataset. Partition expiry
handles BigQuery; lifecycle rules handle GCS; a purge job handles
right-to-delete. "Data has a lifecycle" is a cost story AND a compliance story —
tell it as both.

## 2. Build

### 2.1 Tokenization service — `src/pipeforge/tokenization/`

```python
class DeterministicTokenizer:
    """HMAC-SHA256(value, key) -> token. Key lives in Cloud KMS (never in code/env).
    Deterministic => joinable. Keyed => not rainbow-table-able (unlike bare SHA256
    of an email — low-entropy inputs make unsalted hashes reversible; say this)."""
    def __init__(self, key_ref: str):        # e.g. kms://.../cryptoKeys/pf-tokenize
        self._key = kms_unwrap(key_ref)
    def tokenize(self, value: str) -> str:
        return "tok_" + hmac.new(self._key, value.lower().encode(), "sha256").hexdigest()[:32]
```

- Terraform: KMS keyring + key; `token_vault` table (token → encrypted original,
  KMS-wrapped) for *authorized* detokenization; IAM so only the pipeline SA and a
  dedicated `pf-detokenize` SA can use the key.
- Wire into ODP→FDP: `dataset.pii_columns` (declared at registration — the Phase-2
  ceremony pays off) are tokenized in the Spark job via a UDF-free approach where
  possible (precompute with `F.sha2` + key via `expr`? No — keyed HMAC needs the
  key; use a pandas_udf and note the §29 UDF cost, or tokenize in the BQ MERGE with
  `AEAD`/`DETERMINISTIC_ENCRYPT` — implement one, document the other).
- **DLP excursion:** run one Cloud DLP inspection job over a RAW sample; let it
  *discover* PII you forgot to declare (it will find the user_agent IPs). Auto-DQ
  rule: "DLP finds PII in a non-PII column → P1". Discovery (DLP) vs enforcement
  (your tokenizer) — two halves of the control.

### 2.2 GDPR purge — `pipeforge purge --customer C12345`

1. Look up tokens via vault; 2. crypto-shred vault row (and/or per-customer key);
3. DELETE from RAW (the only place originals live) + expire from quarantine;
4. record an immutable `purge_log` row (who, what, when, legal basis) — deletion
itself must be auditable. Run it against a churned demo customer and verify
CDP aggregates still work (tokens now orphaned-but-meaningless).

### 2.3 Lineage — `src/pipeforge/lineage/openlineage_emitter.py`

Emit OpenLineage RunEvents (START/COMPLETE/FAIL) from `run_context` — one
integration point, all jobs covered. Facets: rowcounts (from audit), schema (from
contract), DQ summary (from Phase 8 stretch). Sink: **Marquez** locally
(docker-compose) — explore the graph UI; also write edges to your `lineage_edge`
table (the Streamlit catalog reads this — no hard dependency on Marquez).

Impact analysis CLI (the §14 use case):

```bash
pipeforge lineage downstream --dataset fdp.dim_customers
# -> cdp.fct_order_lines, cdp.agg_daily_revenue, cdp.customer_features, <dashboard: revenue_daily>
```

Run it *before* the Phase-2 rename scenario and you've closed the loop: contract
change → blast radius known → owners notified → then deploy (§14 verbatim).

### 2.4 Archival & purge framework

- **GCS lifecycle (Terraform, per bucket):** RAW: Standard → Nearline @30d →
  Coldline @90d → delete @365d (per `archival_policy`); quarantine: delete @30d;
  landing: delete @7d (staging is disposable — §15).
- **BigQuery:** `partition_expiration_days` on ODP externals' underlying data and
  big CDP facts per policy; `fdp_staging` tables expire in 3 days (already done —
  now driven from metadata).
- Nightly `pipeforge archival enforce` reconciles metadata policies ↔ actual
  Terraform/table settings and reports drift (governance = declared vs actual,
  continuously compared — same philosophy as recon).

### 2.5 Catalog ⑪ — Dataplex + your registry

- Terraform: Dataplex lake/zones mapping RAW/ODP (GCS) and FDP/CDP (BQ);
  aspect/tag templates for `owner`, `layer`, `pii`, `sla`.
- Sync job: registry → Dataplex labels, so console search shows your governance
  metadata. (Collibra in the reference architecture ≈ Dataplex/DataHub here —
  same role: the enterprise face of metadata. Say that mapping in interviews.)
- Column-level access: BigQuery **policy tags** on any FDP column that holds
  tokens; analysts' group lacks the fine-grained reader role → they see the column
  exists but can't read it. One authorized view in `cdp` proving the
  "govern at the semantic layer" pattern.

### 2.6 Ship it

Tests: tokenizer determinism + case-folding, purge leaves aggregates queryable
but identity unrecoverable, lifecycle policy renderer, lineage emitter payloads.
Tag `v0.9.0`.

## 3. Prove it

- [ ] `fdp.dim_customers.email` contains only `tok_*` values; joining orders↔customers on tokenized email still works (determinism)
- [ ] Detokenization works for the authorized SA and **fails with 403** for your analyst test account
- [ ] `pipeforge purge` on a demo customer: vault row gone, RAW rows gone, purge_log row written, dashboards unchanged
- [ ] Marquez shows the full graph raw→odp→fdp→cdp for orders; `lineage downstream` lists correct blast radius
- [ ] `gsutil lifecycle get` on RAW matches the registered policy; drift job reports clean
- [ ] DLP job finds the undeclared IP column; you register it as PII and the next run tokenizes it

## 4. Break it

Rotate the tokenization key **without** a migration plan (new key = different
tokens = every join between old FDP partitions and new ones silently breaks —
COUNT DISTINCT customers doubles). Catch it via the Phase-8 distribution check,
then design proper rotation (dual-write window / re-tokenization backfill) in
`docs/incidents/010-token-key-rotation.md`. Key rotation breaking determinism is
a genuinely advanced war story — few candidates have it.

## 5. Interview corner

- *"How do you handle PII?"* — the full staff answer, from experience: declare at
  registration → tokenize at the trust boundary (ODP→FDP) → policy tags +
  authorized views for defense in depth → DLP for discovery of the undeclared →
  crypto-shredding for right-to-delete → immutable purge audit.
- *"A team wants to rename a column. Walk me through it."* — contract compat check
  (P02) + lineage blast radius (P09) + change protocol (§16). Three phases of your
  own platform, one coherent answer.
- Data Mesh (§25/Q19): your catalog + ownership + SLAs per data product = the
  "data as a product" pillar; your platform = the "self-serve platform" pillar.
  Argue honestly when mesh is org-overkill.

## 6. Stretch goals

- CMEK on the RAW bucket + BQ datasets (M10) — customer-managed keys end to end.
- Deploy **DataHub** instead of/alongside Marquez; ingest BigQuery + your registry; compare with Dataplex.
- VPC Service Controls perimeter around the project (read M10 first; this one bites).
