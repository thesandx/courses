# Module 10 Exercise: Secure a Customer Dataset

## Goal
Protect a `customers` table end-to-end: encrypt the dataset with a **CMEK** key, and lock
down the `ssn` and `email` columns with **column-level security** (policy tags) so only a
compliance group can read them. Then verify an unauthorized query is blocked.

## Tasks
Create `main.tf` and `policy.sql`. Reference the `solution.*` files after attempting.

### TODO 1 — KMS key
Create a key ring + crypto key (90-day rotation) and grant the **BigQuery service agent**
`cryptoKeyEncrypterDecrypter` on it.

### TODO 2 — CMEK dataset + table
Create dataset `pii` with `default_encryption_configuration` using your key. Add a
`customers` table: `id STRING, email STRING, ssn STRING, country STRING`.

### TODO 3 — Policy tag taxonomy
Create a taxonomy with `FINE_GRAINED_ACCESS_CONTROL` and a `pii` policy tag.

### TODO 4 — Tag the sensitive columns
Attach the policy tag to `email` and `ssn` in the table schema (`policyTags`).

### TODO 5 — Grant fine-grained reader
Grant `roles/datacatalog.categoryFineGrainedReader` on the tag to a compliance group
(use your own email as a stand-in).

## Self-Verification
```bash
terraform init && terraform apply -var project_id="$PROJECT_ID"

# Dataset is CMEK-encrypted:
bq show --format=prettyjson $PROJECT_ID:pii | grep -A2 defaultEncryptionConfiguration
#   → shows your kmsKeyName

# A query selecting ssn WITHOUT the reader role is DENIED:
bq query --use_legacy_sql=false 'SELECT ssn FROM pii.customers LIMIT 1'
#   → Access Denied on the policy tag (expected, unless you granted yourself)

# Selecting a non-tagged column still works:
bq query --use_legacy_sql=false 'SELECT country FROM pii.customers LIMIT 1'
#   → succeeds
```

## Stretch Goals
1. Add a **row access policy** so each analyst sees only their `country`.
2. Configure a **DLP inspection job** that scans the table for `US_SOCIAL_SECURITY_NUMBER`
   and reports findings.
3. Add **dynamic data masking** (hash) on `email` instead of full column block.

## Cleanup
```bash
terraform destroy -var project_id="$PROJECT_ID"
```
