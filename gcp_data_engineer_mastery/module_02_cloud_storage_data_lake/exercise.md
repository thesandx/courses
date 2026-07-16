# Module 2 Exercise: Build a Tiered Data Lake

## Goal
Provision the storage foundation for the lake: a **raw** bucket (immutable, versioned,
tiered to Coldline over time) and a **compliance** bucket with a **retention policy** so
objects cannot be deleted before their retention period — the pattern auditors demand.

## Tasks
Create `main.tf`. Reference `solution.tf` — attempt it first.

### TODO 1 — Provider, variables, unique suffix
Standard `google` provider; `project_id` + `region` vars; a `random_id` for name
uniqueness.

### TODO 2 — Raw bucket
- Regional, `STANDARD`, **UBLA enabled**, **versioning enabled**.
- Lifecycle: at age 90 days → `SetStorageClass COLDLINE`; at age 400 days → `Delete`.

### TODO 3 — Compliance bucket with retention lock
- Add a `retention_policy` with `retention_period = 2592000` (30 days).
- (Stretch) set `is_locked = true` — **irreversible**, so leave it commented for the lab.

### TODO 4 — Deny public access
Ensure neither bucket is public. Add `public_access_prevention = "enforced"`.

### TODO 5 — Outputs
Output both bucket URLs.

## Self-Verification
```bash
terraform init && terraform apply -var project_id="$PROJECT_ID"

# Versioning is on for raw:
gcloud storage buckets describe gs://$PROJECT_ID-lake-raw-* --format="value(versioning.enabled)"
#   → True

# Retention policy is set on compliance:
gcloud storage buckets describe gs://$PROJECT_ID-compliance-* \
  --format="value(retentionPolicy.retentionPeriod)"
#   → 2592000

# Public access is prevented:
gcloud storage buckets describe gs://$PROJECT_ID-lake-raw-* \
  --format="value(iamConfiguration.publicAccessPrevention)"
#   → enforced

# Try to delete a freshly-written object in the compliance bucket → should FAIL:
echo hi | gcloud storage cp - gs://$PROJECT_ID-compliance-*/probe.txt
gcloud storage rm gs://$PROJECT_ID-compliance-*/probe.txt
#   → error: object is subject to a retention policy (expected!)
```

## Stretch Goals
1. Add a lifecycle rule that aborts incomplete multipart uploads after 7 days.
2. Enable **Autoclass** on a third "curated" bucket and explain why you can't also keep
   class-transition lifecycle rules on it.
3. Turn on a **CMEK** key (peek ahead to Module 10) for the compliance bucket.

## Cleanup
```bash
# Retention-locked objects can't be deleted until expiry; unlocked policies + force_destroy are fine.
terraform destroy -var project_id="$PROJECT_ID"
```
