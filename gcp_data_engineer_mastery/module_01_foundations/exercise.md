# Module 1 Exercise: Project Baseline

## Goal
Stand up the least-privilege baseline every later module assumes: the required APIs are
enabled and a dedicated **analytics** service account exists with *scoped* read access —
no basic roles, no exported keys. You'll prove the access is correctly narrow.

## Tasks
Create `main.tf` in an empty directory. Reference `solution.tf` — try it yourself first.

### TODO 1 — Provider & variables
Configure the `google` provider and declare `project_id` and `region` (default
`us-central1`) variables.

### TODO 2 — Enable APIs
Enable at least `bigquery.googleapis.com` and `storage.googleapis.com` using
`google_project_service` with `disable_on_destroy = false`.

### TODO 3 — Create an `analytics-reader` service account
`account_id = "analytics-reader"`, with a clear `display_name`.

### TODO 4 — Grant least privilege
Bind the SA to **exactly** `roles/bigquery.dataViewer` and
`roles/bigquery.jobUser` — enough to run queries and read data, nothing else. Use the
**additive** `google_project_iam_member` resource.

### TODO 5 — Output the SA email.

## Self-Verification
```bash
terraform init && terraform apply -var project_id="$PROJECT_ID"

# The SA exists:
gcloud iam service-accounts list --filter="email:analytics-reader*"
#   → one row for analytics-reader@$PROJECT_ID.iam.gserviceaccount.com

# It has ONLY the two intended roles (no Editor/Owner):
gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --filter="bindings.members:analytics-reader" \
  --format="value(bindings.role)"
#   → roles/bigquery.dataViewer
#   → roles/bigquery.jobUser        (and NOTHING else)

# The APIs are enabled:
gcloud services list --enabled --filter="config.name:(bigquery OR storage)"
#   → both listed
```

## Stretch Goals
1. Add an **IAM Deny policy** that denies `storage.buckets.delete` to the SA even if a
   future broad grant would allow it.
2. Replace the two `google_project_iam_member` blocks with a single `for_each` over a
   `toset([...])` of roles (as in `concepts.tf`).
3. Enable **uniform bucket-level access** as an org policy constraint (preview only).

## Cleanup
```bash
terraform destroy -var project_id="$PROJECT_ID"
```
