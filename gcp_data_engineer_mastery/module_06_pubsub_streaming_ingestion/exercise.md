# Module 6 Exercise: Ordered, Dead-Lettered Ingestion

## Goal
Build a robust ingestion path for **payment events** that (a) preserves per-account
order, (b) never silently drops poison messages, and (c) enforces a schema. Then publish
test messages and watch a bad one land in the dead-letter queue.

## Tasks
Create `main.tf`. Reference `solution.tf` after attempting.

### TODO 1 — Schema + topic
Define an Avro `payment` schema (`payment_id`, `account_id`, `amount_cents:long`,
`ts:long`) and bind it to a `payments` topic.

### TODO 2 — Dead-letter path
Create a `payments-dlq` topic and a subscription on it.

### TODO 3 — Main subscription
A pull subscription `payments-worker` with:
- **message ordering enabled**,
- **exactly-once enabled**,
- a **dead-letter policy** → `payments-dlq`, `max_delivery_attempts = 5`,
- `ack_deadline_seconds = 30`.

### TODO 4 — Grant the Pub/Sub service agent
Grant the Pub/Sub service account `roles/pubsub.publisher` on the DLQ topic (required for
dead-lettering to work).

## Self-Verification
```bash
terraform init && terraform apply -var project_id="$PROJECT_ID"

# Publish an ORDERED valid message (note the ordering key):
gcloud pubsub topics publish payments \
  --message='{"payment_id":"p1","account_id":"a1","amount_cents":500,"ts":1}' \
  --ordering-key=a1

# Pull it (ordered subs must be pulled per key):
gcloud pubsub subscriptions pull payments-worker --auto-ack --limit=1
#   → shows the message

# Confirm the DLQ subscription exists:
gcloud pubsub subscriptions describe payments-dlq-sub --format="value(name)"

# Confirm exactly-once + ordering are set:
gcloud pubsub subscriptions describe payments-worker \
  --format="value(enableExactlyOnceDelivery, enableMessageOrdering)"
#   → True   True
```

## Stretch Goals
1. Add a **BigQuery subscription** that writes valid payments straight to a table.
2. Publish a message that violates the schema and confirm it is **rejected at publish**.
3. Simulate repeated nack (don't ack) and observe delivery to the DLQ after 5 attempts.

## Cleanup
```bash
terraform destroy -var project_id="$PROJECT_ID"
```
