# Module 12 Exercise: Instrument for Reliability & Cost

## Goal
Make a streaming pipeline observable and cost-safe: alert when it falls behind (freshness
SLO), alert on error log spikes, and put a budget on the project. This is the "maintain &
automate workloads" exam domain in miniature.

## Tasks
Create `main.tf`. Reference `solution.tf` after attempting.

### TODO 1 — Notification channel
An email `google_monitoring_notification_channel` for on-call.

### TODO 2 — Freshness SLO alert
An alert policy on **Dataflow data watermark age** (metric
`dataflow.googleapis.com/job/data_watermark_age`) firing when lag > 900s (15 min) for
5 minutes → this encodes a **15-minute freshness SLO**.

### TODO 3 — Error-rate alert
A **log-based metric** counting `severity>=ERROR` logs, plus an alert policy that fires
when the error count exceeds a threshold.

### TODO 4 — Budget
A `google_billing_budget` of $100 with alerts at 50%, 90%, 100% scoped to the project.

### TODO 5 — Note the cap caveat
In a comment, explain how you'd make spend actually **stop** at 100% (budget → Pub/Sub →
function disabling billing).

## Self-Verification
```bash
terraform init && terraform apply \
  -var project_id="$PROJECT_ID" \
  -var billing_account="$BILLING_ACCOUNT" \
  -var alert_email="you@example.com"

# Alert policies exist:
gcloud alpha monitoring policies list --format="value(displayName)"
#   → freshness + error-rate policies

# Log-based metric exists:
gcloud logging metrics list --filter="name:pipeline_errors" --format="value(name)"

# Budget exists:
gcloud billing budgets list --billing-account="$BILLING_ACCOUNT" \
  --format="value(displayName,amount.specifiedAmount.units)"
#   → your budget, 100
```

## Stretch Goals
1. Wire the 100% budget threshold to a **Pub/Sub topic** and sketch the billing-disable
   function.
2. Add a **Monitoring dashboard** tiling watermark lag, backlog, and error rate.
3. Define the SLO formally with a **service + SLO** resource and track the error budget.

## Cleanup
```bash
terraform destroy \
  -var project_id="$PROJECT_ID" \
  -var billing_account="$BILLING_ACCOUNT" \
  -var alert_email="you@example.com"
```
