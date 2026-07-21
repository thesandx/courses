# Exercise 13 — Design and Provision a Private Ingestion Path

You are the data engineer for a retailer whose order database (MySQL) runs in an
on-prem data center connected to Google Cloud by a 10 Gbps Partner Interconnect.
Compliance requires that **no replication traffic touches the public internet**,
and analytics must see order changes in BigQuery within ~15 minutes.

Separately, a one-time archive of **250 TB** of historical clickstream logs sits
on a NAS behind a **200 Mbps** office link and must reach Cloud Storage within
**one month**.

## Part A — Decide (no cloud resources needed)

1. **A1.** Compute the transfer time for 250 TB at 200 Mbps (assume ~80%
   efficiency). Does it meet the one-month deadline? Which transfer mechanism do
   you choose, and why not Storage Transfer Service?
2. **A2.** For the MySQL CDC feed: which service do you pick, and which of its
   connectivity methods satisfies "no public internet"? Why are IP allowlisting
   and forward-SSH disqualified?
3. **A3.** The VPC is a Shared VPC owned by the networking team. List the exact
   IAM role (and the two identities) that must be granted on the subnetwork for
   a Dataflow enrichment job to launch there.
4. **A4.** The analytics team also wants ad-hoc SQL over clickstream Parquet
   files that will stay in AWS S3 (owned by a sister company). Which BigQuery
   features avoid copying the data?

## Part B — Build (Terraform)

Work from `concepts.tf` as your reference. Create `main.tf` that provisions:

5. **B1.** A custom-mode VPC `retail-hybrid-vpc` with subnet `ingest-subnet`
   (10.50.0.0/20, region of your choice) with **Private Google Access enabled**.
6. **B2.** Cloud Router + Cloud NAT so private-IP workers can reach non-Google
   endpoints outbound-only.
7. **B3.** A worker service account plus `roles/compute.networkUser` bindings on
   the subnetwork for (a) that SA and (b) the Dataflow service agent.
8. **B4.** A Datastream **private connection** into the VPC (pick an unused /29),
   a MySQL **connection profile** that uses it, a BigQuery destination profile,
   and a **stream** replicating database `orders` with `backfill_all`, 15-minute
   data freshness, and `desired_state = "NOT_STARTED"`.

### Self-verification
- `terraform validate` passes and `terraform plan` shows only your resources.
- `gcloud compute networks subnets describe ingest-subnet --region=<r> \
  --format="value(privateIpGoogleAccess)"` → `True`.
- `gcloud datastream private-connections list --location=<r>` shows the peering.
- The subnet IAM policy lists **both** networkUser members.

## Part C — Think Like the Exam

9. **C1.** The stream works in the lab project but fails in production with a
   subnet permissions error. What did the platform team forget?
10. **C2.** Mid-migration, leadership asks to *move the database itself* to
    Cloud SQL with minimal downtime instead of feeding analytics. Which service
    replaces Datastream in that sentence, and what stays the same about the
    networking?
11. **C3.** The sister company's Kafka team refuses to migrate. Name two ways
    their topics still land in your GCP analytics without rewriting their
    producers.
