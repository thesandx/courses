# Module 13 — Migration & Hybrid Connectivity

Real deployments — and the current exam — assume your data starts *outside*
Google Cloud: on-prem databases with no public IPs, Hadoop clusters, Kafka
estates, other clouds. This module covers how data gets in **at scale**, **on a
deadline**, and **without touching the public internet**.

## Learning Objectives
- Pick the right bulk-transfer mechanism from volume, bandwidth, and deadline.
- Design private connectivity: Interconnect, VPN, Private Google Access, and
  Datastream private connectivity.
- Run continuous database replication (CDC) into BigQuery with Datastream, and
  know when Database Migration Service is the tool instead.
- Operate pipelines on a Shared VPC without permission surprises.
- Migrate Hadoop/Kafka estates incrementally instead of big-bang.

## 1. Bulk Transfer: Do the Math First

Transfer time ≈ data volume ÷ effective bandwidth. **Compute it before choosing.**
- 1 TB over 1 Gbps ≈ 2.5 hours; over 100 Mbps ≈ 1 day.
- 400 TB over 100 Mbps ≈ **a year** → no software tool fixes physics.

| Scenario | Tool |
|---|---|
| < a few TB, one-off, adequate bandwidth | `gcloud storage cp` (parallel composite uploads) |
| Large, recurring, scheduled; S3/HTTP/on-prem NAS | **Storage Transfer Service** (on-prem agent pools, incremental sync) |
| Deadline the math can't meet, or weak/saturated links | **Transfer Appliance** — physical device, load locally, ship back |
| SaaS (Ads, GA4, YouTube), S3/Redshift/Teradata → BigQuery, or scheduled GCS→BQ loads | **BigQuery Data Transfer Service** |
| Continuous change replication from databases | **Datastream** (§3) |

## 2. Private Connectivity Building Blocks

When the requirement reads "must not traverse the public internet" (regulated
industries, no-public-IP databases), assemble from four pieces:

1. **Cloud Interconnect** (Dedicated or Partner) — private, high-bandwidth
   physical link from the data center into your VPC. **Cloud VPN** is the
   lower-bandwidth, encrypted-over-internet alternative (IPsec) — private
   addressing, but the packets do ride the internet; Interconnect when the
   mandate is strict.
2. **Private Google Access (PGA)** — lets VPC (and, via on-prem routing,
   data-center) hosts call Google APIs — BigQuery, GCS, Pub/Sub — on **private
   IPs** (`private.googleapis.com`, or `restricted.googleapis.com` inside a
   VPC-SC perimeter). Without PGA, "no public IPs" breaks API access.
3. **Shared VPC** — networking team owns the network in a *host project*;
   pipelines run in *service projects*. Grant **`compute.networkUser`** on the
   shared subnetwork to the workload's service accounts **and the service
   agents** (Dataflow's, Datastream's) — the classic missing grant when jobs
   fail to start.
4. **VPC Service Controls** — the exfiltration perimeter around data APIs
   (Module 10); hybrid paths enter via access levels / private connectivity.

TLS ≠ residency: encryption in transit does **not** satisfy "no public
internet". Only the network path does.

## 3. Datastream: Serverless CDC

**Datastream** tails a database's change log (MySQL, PostgreSQL, Oracle, SQL
Server) and streams inserts/updates/deletes to **BigQuery** (directly) or GCS —
minimal source impact, no infrastructure to run.

Connectivity methods, in order of exam preference for locked-down sources:
- **Private connectivity** — Datastream peers into your VPC and reaches the
  source over your Interconnect/VPN. The answer whenever the source has no
  public IP or traffic must stay private.
- Forward-SSH tunnel / IP allowlisting — both traverse public networks; only
  for sources where that's acceptable.

**Datastream vs Database Migration Service (DMS):** DMS migrates/replicates a
database *into Cloud SQL or AlloyDB as a database* (lift-and-shift, minimal
downtime cutover). Datastream feeds *analytics* (BigQuery/GCS). "Replicate 50
Oracle tables into BigQuery continuously, minimal infra" → Datastream with
private connectivity — not self-managed Kafka + Debezium.

**Transactional outbox** (Module 6) remains the app-level pattern when an event
must be published iff a transaction commits; CDC on the outbox table is its
industrial-strength implementation.

## 4. Migrating Estates, Not Just Bytes

- **Hadoop/HDFS**: data → **GCS** (gs:// via the connector), metadata →
  **Dataproc Metastore**, jobs → ephemeral **Dataproc** / **Dataproc
  Serverless**, orchestration stays **Airflow → Cloud Composer** (hundreds of
  existing DAGs port with minimal change). HBase workloads → **Bigtable**
  (HBase API). ORC/Parquet + "just SQL" → straight to **BigQuery**.
- **Kafka**: don't big-bang rewrite producers. Bridge with the **Pub/Sub Kafka
  connector**, read in place with Dataflow `KafkaIO`, or move the cluster to
  **Managed Service for Apache Kafka** when the Kafka protocol must survive.
- **Other clouds**: query S3/Azure data in place with **BigQuery Omni +
  BigLake** (Module 3); copy with Storage Transfer Service when it must land
  in GCS.

## 🎯 Exam Focus

| Scenario | Answer |
|----------|--------|
| "400 TB, 100 Mbps link, 2-month deadline" | **Transfer Appliance** (the math fails everything else) |
| "Nightly sync of an on-prem NAS to GCS" | **Storage Transfer Service** with on-prem agents |
| "Replicate on-prem MySQL to BigQuery, no public internet" | **Datastream + private connectivity** over **Interconnect/VPN**, with **PGA** |
| "Oracle in a VPC → 50 tables continuously to BigQuery, minimal infra" | **Datastream** private connectivity (not Kafka+Debezium) |
| "Move the database itself to Cloud SQL/AlloyDB" | **Database Migration Service** |
| "Dataflow won't start on the Shared VPC subnet" | Grant **`compute.networkUser`** (service agent + worker SA) on the subnetwork |
| "Workers must have no public IPs" | Disable public IPs + **Private Google Access** on the subnet |
| "Keep Kafka protocol, stop operating brokers" | **Managed Service for Apache Kafka** (bridge with the Pub/Sub Kafka connector) |
| "Hadoop + hundreds of Airflow DAGs, minimal orchestration change" | **Dataproc + GCS + Cloud Composer** |

### Practice Questions
1. **A hospital must copy a 10 TB relational DB to BigQuery securely and fast;
   a 10 Gbps Interconnect exists.** → Native export + `bq load` (or Dataflow/JDBC)
   over the Interconnect with PGA — ~2.5 hours of transfer; no appliance needed.
2. **Regulator: CDC traffic may never touch the public internet.** → Datastream
   **private connectivity** peered to the VPC, source reached via Interconnect/VPN.
3. **Sync 200 TB from S3 weekly into GCS.** → Storage Transfer Service (S3 source).
4. **Jobs on a Shared VPC fail with subnet permission errors.** → `compute.networkUser`
   for the Dataflow service agent + worker service account on the host-project subnet.
5. **Team wants to keep existing Kafka consumers during a 12-month migration.** →
   Mirror topics with the Pub/Sub Kafka connector; migrate consumers gradually.

## Key Takeaways
- **Bandwidth math before tools**; Transfer Appliance is the deadline-saver.
- Private path = **Interconnect/VPN + PGA** (+ VPC-SC); TLS alone ≠ private.
- **Datastream** feeds analytics; **DMS** moves databases.
- Shared VPC failures are almost always a missing **`compute.networkUser`**.
- Migrate estates incrementally: GCS for HDFS, Composer for Airflow, connectors
  for Kafka, Bigtable for HBase.

## Files in This Module
- `concepts.tf` — VPC with a PGA-enabled subnet, firewall for IAP/SSH, Shared-VPC
  style `compute.networkUser` grants, and a Datastream private connection + CDC
  stream skeleton
- `exercise.md` — design and provision a private ingestion path
- `solution.tf` — reference solution with commentary
