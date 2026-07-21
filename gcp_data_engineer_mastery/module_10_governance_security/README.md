# Module 10: Governance, Security & Quality

## Learning Objectives
- Encrypt data with **CMEK/Cloud KMS** and understand default vs customer-managed keys.
- Protect sensitive data with **Cloud DLP** (Sensitive Data Protection): inspection,
  de-identification, masking.
- Apply **column-level** and **row-level** security in BigQuery via **policy tags**.
- Govern the lake with **Dataplex** (zones, data quality, lineage, catalog).
- Isolate data exfiltration risk with **VPC Service Controls**.

---

## 1. Encryption & Cloud KMS

Everything on GCP is encrypted at rest by default (Google-managed keys). Upgrade to
**CMEK** when you must control the key lifecycle/rotation, or **CSEK/EKM** for
externally-held keys.

| Option | Who holds the key | Use |
|--------|-------------------|-----|
| Google-managed (default) | Google | Baseline; no action needed |
| **CMEK** (Cloud KMS) | You, in KMS | Compliance, controlled rotation/revocation |
| **EKM** (External Key Manager) | You, off-cloud | Regulatory "key never on Google" needs |

```hcl
resource "google_bigquery_dataset" "secure" {
  dataset_id = "secure"
  default_encryption_configuration { kms_key_name = google_kms_crypto_key.bq.id }
}
```

> **Gotcha:** each service's **service agent** needs
> `roles/cloudkms.cryptoKeyEncrypterDecrypter` on the key, or encrypted resource creation
> fails. And the **key must be in the same region** as the data.

## 2. Cloud DLP / Sensitive Data Protection

Discover and protect PII (emails, credit cards, national IDs) with **infoType detectors**.

| Action | Result |
|--------|--------|
| **Inspection** | Find & classify sensitive data (scan GCS/BigQuery) |
| **De-identification** | Redact, mask, or replace with a token |
| **Format-preserving / tokenization** | Reversible pseudonymization (KMS-wrapped key) |
| **Re-identification risk** | k-anonymity / l-diversity analysis |

> **Exam tip:** "mask credit-card numbers but keep the last 4" → DLP
> **de-identification** with a masking/crypto transformation.

## 3. BigQuery Column- & Row-Level Security

- **Column-level:** attach **policy tags** (from a Data Catalog taxonomy) to sensitive
  columns; only principals with the tag's Fine-Grained Reader role see them.
- **Row-level:** `CREATE ROW ACCESS POLICY` filters rows per principal (e.g. region reps
  see only their region).
- **Dynamic data masking:** policy-tag-based masking (hash/nullify) instead of full block.

```sql
CREATE ROW ACCESS POLICY emea_only ON sales.orders
GRANT TO ('group:emea-team@example.com')
FILTER USING (region = 'EMEA');
```

## 4. Dataplex — Govern the Lakehouse

Dataplex unifies distributed data (GCS + BigQuery) into logical **lakes → zones →
assets**, adding:
- **Data quality** scans (rules → pass/fail metrics).
- **Data profiling** and **auto-discovery** (creates BigLake/external tables).
- **Lineage** and a **catalog** (searchable metadata, policy tags).

| Zone type | Meaning |
|-----------|---------|
| **Raw zone** | As-ingested, any format |
| **Curated zone** | Structured, quality-enforced (Parquet/BQ) |

## 5. VPC Service Controls & Network

- **VPC Service Controls (VPC-SC):** draw a **service perimeter** around BigQuery/GCS/etc.
  so data can't be copied to projects outside it — mitigates **exfiltration** even by
  credentialed insiders.
- **Private Google Access / Private Service Connect:** reach GCP APIs without public IPs.
- **IAM Conditions:** time-bound / resource-scoped grants.

> **Exam tip:** "prevent data from being exfiltrated to another project even with valid
> credentials" → **VPC Service Controls perimeter** (not IAM alone).

---

## 6. Data Mesh IAM, CMEK Sharing & Joinable De-identification

### Dataplex-powered data mesh (the current exam's pet architecture)
Multiple domain teams build data products; a central platform governs. Dataplex
organizes assets into **lakes and zones** (raw/curated), and access uses
**Dataplex's own roles** so permissions propagate to the underlying BigQuery/GCS
assets: producers (data engineers) get **`dataplex.dataOwner`** on their domain's
lake; consumers (analysts) get **`dataplex.dataReader`** on the **curated zone**
only. Granting raw BigQuery/GCS roles per asset is the anti-pattern the wrong
options describe.

### CMEK datasets can't be shared past the key
A partner without access to your Cloud KMS key cannot read a CMEK-protected
dataset — and you never hand out key copies. The pattern: **copy the shareable
slice into a non-CMEK dataset and publish it via Analytics Hub** (or an
authorized view over non-CMEK copies). Remember the reverse too: revoking the
key is your data kill-switch.

### De-identification that preserves joins
DLP masking destroys joinability (`j***@x.com` ≠ deterministic). When analysts
must **join on a de-identified field** (e.g., email across two datasets), use
**format-preserving encryption (FPE-FFX)** or deterministic tokenization — the
same input always yields the same token, so joins still work and the transform
is reversible only with the key. Masking/redaction is for display, tokenization
is for linkage.

### IAM hygiene the exam rewards
- Grant roles to **groups**, not individuals — membership handles joiners/leavers.
- **Predefined roles** over primitive Owner/Editor/Viewer; custom only when
  predefined over-grant.
- Workloads use **attached service accounts** (one per pipeline, least privilege,
  narrowest scope); never exported JSON keys.

## 🎯 Exam Focus

| Scenario | Answer |
|----------|--------|
| "Control the encryption key, rotate/revoke it" | **CMEK** (Cloud KMS) |
| "Key must never reside on Google" | **EKM** |
| "Find & mask PII across BigQuery/GCS" | **Cloud DLP** inspect + de-identify |
| "Hide salary column from most analysts" | **Policy tags** (column-level security) |
| "Reps see only their region's rows" | **Row access policy** |
| "Stop data copy to outside projects" | **VPC Service Controls** perimeter |
| "Enforce data-quality rules on the lake" | **Dataplex** data quality scan |

### Practice Questions
1. **Regulator requires you to control and rotate the encryption key for a dataset.** →
   **CMEK** with Cloud KMS; grant the BigQuery service agent encrypt/decrypt on the key.
2. **Analysts must query a table but never see the `ssn` column.** → Apply a **policy
   tag** to `ssn` and grant Fine-Grained Reader only to authorized users (column-level
   security).
3. **Even with valid credentials, no one should copy BigQuery data to a personal
   project.** → **VPC Service Controls** perimeter around BigQuery.
4. **Mask credit cards to last-4 in exports.** → **DLP de-identification** (masking
   transform).
5. **Sales reps should only see rows for their own region.** → **Row access policy**
   filtering on region.
6. **You need automated data-quality checks and a searchable catalog over the lake.** →
   **Dataplex** (quality scans + catalog/lineage).

---

## Key Takeaways
- **CMEK/EKM** give you key control; the service agent needs KMS encrypt/decrypt and
  region match.
- **DLP** discovers and de-identifies PII; **policy tags** and **row access policies**
  enforce fine-grained BigQuery security.
- **Dataplex** governs the lakehouse (zones, quality, lineage, catalog).
- **VPC Service Controls** stop exfiltration that IAM alone can't.

Next: [Module 11 — ML & Analytics Integration](../module_11_ml_analytics/README.md).

---

## Files in This Module
- `concepts.tf` — KMS key + CMEK dataset, a Data Catalog policy-tag taxonomy, and a
  Dataplex lake/zone
- `exercise.md` — secure a dataset with CMEK + column-level security
- `solution.tf` — reference solution
