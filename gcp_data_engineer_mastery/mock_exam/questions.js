// GCP Professional Data Engineer — Mock Exam question bank.
// Original practice questions written for this course (not copied from any exam
// or question-dump site). Each item: d = domain, q = question, o = options,
// a = index of correct option, e = explanation.
const QUESTIONS = [

// ---------------------------------------------------------------- BigQuery
{
d: "BigQuery",
q: "Your analysts run daily dashboards that always filter a 90 TB events table on event_date and customer_id. Queries scan far more data than expected and costs are climbing. What should you do first?",
o: [
"Create an index on event_date and customer_id.",
"Partition the table on event_date and cluster it on customer_id.",
"Export the table to Cloud Storage and query it as an external table.",
"Switch the project to flat-rate slot pricing."
],
a: 1,
e: "BigQuery has no user-managed indexes. Partitioning on the date column lets the engine prune whole partitions from the scan, and clustering on customer_id co-locates rows so blocks that don't match the filter are skipped. External tables are slower, and flat-rate pricing changes billing but does not reduce wasted scanning."
},
{
d: "BigQuery",
q: "A scheduled query writes daily aggregates to a reporting table. The finance team wants to be able to see the table exactly as it was up to 5 days ago after an accidental bad load. What is the simplest built-in mechanism?",
o: [
"Enable table snapshots every hour with a cron job.",
"Use time travel with SELECT ... FOR SYSTEM_TIME AS OF and configure the dataset's time travel window to 5 days.",
"Export the table daily to Cloud Storage with object versioning.",
"Recreate the table from the raw source data each time."
],
a: 1,
e: "BigQuery time travel lets you query or restore a table's state at any point within the configurable window (2–7 days, default 7). FOR SYSTEM_TIME AS OF reads historical data with no extra pipelines. Snapshots and exports work but add cost and operational overhead for something time travel gives you natively."
},
{
d: "BigQuery",
q: "You must load 10 TB of Parquet files from Cloud Storage into BigQuery once, at the lowest possible cost. Which approach should you use?",
o: [
"A Dataflow pipeline that reads the files and streams rows into BigQuery.",
"The BigQuery Storage Write API in committed mode.",
"A native batch load job (bq load / LOAD DATA) from Cloud Storage.",
"An external table plus a scheduled CTAS query."
],
a: 2,
e: "Batch load jobs from Cloud Storage are free (they use a shared pool of slots) and Parquet is a natively supported format. Streaming inserts and the Storage Write API incur ingestion costs and are meant for continuous ingestion; the CTAS over an external table would bill you for scanning all 10 TB."
},
{
d: "BigQuery",
q: "A query joins a 6 TB fact table with a 40 MB dimension table and runs slowly with high shuffle. What is the most likely automatic optimization, and how can you help it?",
o: [
"Broadcast join — keep the small table under the broadcast threshold and put the largest table first in the JOIN clause.",
"Hash join — force it with a query hint.",
"Nested loop join — add an index to the dimension table.",
"Sort-merge join — pre-sort both tables by the join key."
],
a: 0,
e: "When one side of a join is small, BigQuery broadcasts it to every slot processing the large table, avoiding a shuffle of the big side. Writing the largest table first is the documented best practice. BigQuery has no user-supplied join hints or indexes."
},
{
d: "BigQuery",
q: "Your team wants dashboards to reflect data that arrives continuously, with results visible within a few seconds of ingestion, using SQL only. Which ingestion method fits best?",
o: [
"Batch load jobs every 15 minutes.",
"Storage Write API (or a Pub/Sub BigQuery subscription) so rows are queryable within seconds.",
"bq cp from a staging table hourly.",
"Federated queries against Cloud SQL."
],
a: 1,
e: "The Storage Write API (and the Pub/Sub BigQuery subscription built on it) makes rows available to queries within seconds and offers exactly-once semantics — that's the streaming path. Batch loads are cheaper but introduce minutes of latency."
},
{
d: "BigQuery",
q: "An on-demand query is estimated to scan 2 TB. Which two-part change reduces the bytes billed the most?",
o: [
"SELECT * but add a LIMIT 1000 clause.",
"Select only needed columns and filter on the partitioning column.",
"Wrap the query in a view.",
"Run the query with higher priority."
],
a: 1,
e: "BigQuery bills columnar scans: selecting fewer columns cuts bytes read, and a filter on the partition column prunes partitions. LIMIT does not reduce bytes scanned on a native table, views don't change scanning, and priority affects scheduling, not cost."
},
{
d: "BigQuery",
q: "You need to share a curated slice of a dataset with an external partner organization without copying data or granting access to your project's other tables. What is the recommended approach?",
o: [
"Export the data nightly to their SFTP server.",
"Create an authorized view (or authorized dataset) that exposes only the slice, and share it — or publish it via Analytics Hub.",
"Grant the partner the BigQuery Data Viewer role at the project level.",
"Email them a CSV extract weekly."
],
a: 1,
e: "Authorized views let consumers query the view without having read access to the underlying tables; Analytics Hub packages datasets for cross-org sharing with no data copies. Project-level Data Viewer over-grants, and file transfers create stale copies and governance headaches."
},
{
d: "BigQuery",
q: "A materialized view over a large events table is not being used by your queries, and you notice the base table receives streaming inserts constantly. What is TRUE about BigQuery materialized views here?",
o: [
"Materialized views cannot be created over tables that receive streaming data.",
"Queries can still be automatically rewritten to use the materialized view, and the engine combines the view with the delta of new base-table rows.",
"You must refresh the materialized view manually after every insert.",
"Materialized views always return stale data until the next scheduled refresh."
],
a: 1,
e: "BigQuery materialized views support smart tuning: eligible queries are rewritten to read the precomputed view plus the delta of base-table changes since the last refresh, so results are always fresh and correct even with streaming inserts."
},
{
d: "BigQuery",
q: "Your organization runs steady, heavy BigQuery workloads 24/7, currently on on-demand pricing, and finance wants predictable costs. What should you evaluate?",
o: [
"BigQuery editions capacity commitments (slot reservations) sized to the workload.",
"Splitting the workload across 10 projects to multiply free tiers.",
"Moving all queries to external tables over Cloud Storage.",
"Scheduling all queries at night."
],
a: 0,
e: "Capacity-based pricing (editions with slot reservations and optional commitments) gives a fixed spend for steady workloads and lets you share slots across projects via reservations. Splitting projects to game free tiers is an anti-pattern; external tables typically cost more in performance."
},
{
d: "BigQuery",
q: "You need row-level security so regional sales managers see only rows for their own region in a shared table. What is the native mechanism?",
o: [
"Create one table per region and grant access separately.",
"CREATE ROW ACCESS POLICY ... GRANT TO ... FILTER USING (region = ...) on the table.",
"A wrapper view with SESSION_USER() logic is the only option.",
"Use column-level encryption per region."
],
a: 1,
e: "Row access policies are BigQuery's native row-level security: they filter rows at query time based on the caller's identity. Views with SESSION_USER() work but are a legacy workaround; per-region tables multiply maintenance."
},
{
d: "BigQuery",
q: "A table is partitioned by ingestion time, but analysts actually filter on a business timestamp column inside the payload, so partition pruning never happens. What should you do?",
o: [
"Tell analysts to add _PARTITIONTIME filters even though they don't match the business logic.",
"Re-create the table partitioned on the business timestamp column (column-based time partitioning).",
"Add clustering on _PARTITIONTIME.",
"Increase the partition expiration."
],
a: 1,
e: "Partition on the column users actually filter by. Column-based time partitioning uses the business timestamp so natural WHERE clauses prune partitions. Filtering on _PARTITIONTIME only helps if ingestion time correlates with the business time, which is not guaranteed (late data)."
},
{
d: "BigQuery",
q: "Which statement about BigQuery slots is correct?",
o: [
"A slot is a unit of storage equal to 1 GB.",
"A slot is a unit of compute (virtual CPU + memory) used to execute query stages; queries are queued when slots are exhausted.",
"Slots are only used in on-demand pricing.",
"Each user gets exactly one slot."
],
a: 1,
e: "Slots are BigQuery's unit of compute capacity. On-demand projects get a default pool (about 2,000 slots); capacity pricing reserves a specific number. When demand exceeds available slots, work units queue — throughput degrades gracefully rather than failing."
},
{
d: "BigQuery",
q: "You want to query data that lives in Parquet files on Cloud Storage with BigQuery, while enforcing fine-grained (row/column-level) security on it and caching metadata for performance. What should you use?",
o: [
"A permanent external table with the legacy connector.",
"BigLake tables.",
"Load everything into native tables first — security on external data is impossible.",
"A federated Cloud SQL query."
],
a: 1,
e: "BigLake extends BigQuery governance (row-level security, column-level security, data masking) and metadata caching to data in object storage — external tables without BigLake can't enforce fine-grained security."
},
{
d: "BigQuery",
q: "A dashboard runs the same expensive aggregation every 5 minutes over a table that changes once per hour. Users pay on-demand. What's the cheapest low-effort fix?",
o: [
"Nothing — BigQuery caches all query results automatically for 24 hours, and cache hits are free; just make sure the query text stays identical and the table isn't changing between runs.",
"Create a materialized view for the aggregation so repeated dashboard hits read precomputed results.",
"Add LIMIT to the dashboard query.",
"Increase the dashboard refresh interval to 6 minutes."
],
a: 1,
e: "The result cache is invalidated whenever the table changes, and here the table changes hourly — so the cache helps but the 5-minute refreshes between changes already hit it; the wasteful runs are the ones after each change. A materialized view precomputes the aggregation incrementally so every dashboard hit reads a tiny precomputed result regardless of table changes. (If the table truly never changed, A would suffice.)"
},
{
d: "BigQuery",
q: "You need to delete every row for a specific user across a huge partitioned table to satisfy a GDPR erasure request, efficiently. Which is the recommended pattern?",
o: [
"Query with a WHERE clause excluding the user — deletion is impossible in BigQuery.",
"Run a DML DELETE WHERE user_id = X; BigQuery DML is fully supported and can use partition pruning if you also filter partitions.",
"Export, filter with grep, and re-import the table.",
"Drop and recreate the whole table."
],
a: 1,
e: "BigQuery supports DML DELETE/UPDATE/MERGE. For large partitioned tables, adding a partition filter limits the work. Search indexes or clustering on user_id can further reduce cost. Export/reimport and full recreation are far more expensive and error-prone."
},
{
d: "BigQuery",
q: "Analysts complain a query fails with 'Resources exceeded' during a large GROUP BY with millions of groups and an ARRAY_AGG. What's the most effective first change?",
o: [
"Retry the query at night.",
"Reduce per-group memory pressure: drop unneeded columns from ARRAY_AGG, filter earlier, or split the aggregation into stages (e.g., aggregate per day, then merge).",
"Switch to legacy SQL.",
"Increase the table's partition count."
],
a: 1,
e: "'Resources exceeded' usually means a stage (often a big aggregation or sort on a single worker) ran out of memory. Reducing the data carried per group, filtering earlier, and staging the aggregation reduces per-slot memory. Legacy SQL and retrying don't address the cause."
},
{
d: "BigQuery",
q: "Your company wants analysts to experiment freely but cap the daily on-demand spend of each analyst. What should you configure?",
o: [
"A Cloud Billing budget alert only.",
"Custom query quotas: per-user and per-project daily bytes-billed limits.",
"Ask analysts to check the query validator before running.",
"Remove BigQuery access outside business hours."
],
a: 1,
e: "BigQuery custom quotas hard-cap the bytes billed per user or per project per day — queries beyond the cap fail rather than spend. Budget alerts only notify after the fact; the validator is advisory."
},
{
d: "BigQuery",
q: "You have IoT data arriving with occasional very late events (up to 3 days). The table is partitioned by event_date. What should your MERGE-based daily job do to remain correct and cheap?",
o: [
"MERGE against the full table every run.",
"MERGE with a WHERE clause on the target that restricts partitions to the late-arrival window (e.g., last 4 days).",
"Ignore late events — they are statistically insignificant.",
"Reload the entire table daily."
],
a: 1,
e: "Constraining the MERGE's target scan to the partitions that can actually change (the late-data window) preserves correctness for late events while pruning everything older, keeping cost proportional to the window instead of the table."
},
{
d: "BigQuery",
q: "Which BigQuery feature lets you mask a column (e.g., show only the last 4 digits of a card number) for most users while privileged users see the raw value, without maintaining two tables?",
o: [
"Authorized UDFs.",
"Dynamic data masking with policy tags (column-level security).",
"Client-side encryption.",
"Table snapshots."
],
a: 1,
e: "Attach a policy tag from a Data Catalog/Dataplex taxonomy to the column and configure a data policy with a masking rule; users without the Fine-Grained Reader role see the masked value. One table, policy-driven access."
},
{
d: "BigQuery",
q: "A batch pipeline overwrite-loads a snapshot table daily, but consumers occasionally query mid-load and see partial data. What's the cleanest fix?",
o: [
"Load into a staging table, then atomically swap using a single statement (e.g., CREATE OR REPLACE TABLE ... AS SELECT, or MERGE), since individual BigQuery jobs are atomic.",
"Tell consumers not to query between 2 and 3 AM.",
"Use two datasets and update a wiki page pointing to the current one.",
"Lock the table with an exclusive lock during load."
],
a: 0,
e: "Each BigQuery job/statement is atomic — readers see the table before or after, never mid-write. Loading to staging and then replacing the target in one statement guarantees consumers never observe partial data. BigQuery has no user-managed table locks."
},

// ------------------------------------------------- Storage & Data Lakes
{
d: "Storage & Data Lakes",
q: "Compliance requires you to keep audit logs for 7 years; they are read perhaps once a year during audits. Which storage class minimizes cost?",
o: [
"Standard",
"Nearline",
"Coldline",
"Archive"
],
a: 3,
e: "Archive has the lowest at-rest price and is designed for access less than once a year, with a 365-day minimum storage duration. Retrieval costs are higher, but with annual-or-less access the storage savings dominate."
},
{
d: "Storage & Data Lakes",
q: "Access patterns for a bucket are unpredictable — some objects are hot for months, others go cold immediately. You want cost optimization without writing lifecycle rules. What should you enable?",
o: [
"Object versioning",
"Autoclass",
"Requester Pays",
"Turbo replication"
],
a: 1,
e: "Autoclass automatically transitions each object between storage classes based on its individual access pattern, with no retrieval fees or early-deletion charges — ideal when you can't predict access patterns well enough to write lifecycle rules."
},
{
d: "Storage & Data Lakes",
q: "A regulator requires that objects in a bucket cannot be deleted or overwritten for 5 years, even by project owners. What do you configure?",
o: [
"A lifecycle rule with age = 5 years.",
"A bucket retention policy set to 5 years, and lock it.",
"IAM deny on storage.objects.delete for all users.",
"Object versioning with 5-year noncurrent expiry."
],
a: 1,
e: "A locked retention policy makes WORM guarantees: no one — including owners — can delete or replace objects before they age past the retention period, and the policy itself can't be reduced or removed once locked. IAM can be changed by admins, so it doesn't satisfy the regulator."
},
{
d: "Storage & Data Lakes",
q: "Your Dataflow jobs in region us-central1 read terabytes daily from a bucket. Where should the bucket live to minimize cost and latency?",
o: [
"A multi-region US bucket, always.",
"A regional bucket in us-central1, co-located with the compute.",
"A dual-region bucket spanning US and EU.",
"Anywhere — network egress within Google is free."
],
a: 1,
e: "Co-locating storage and compute in the same region avoids inter-region egress charges and gives the best throughput/latency. Multi-region buckets are for serving/HA reads across geographies, and cross-continent replication (US+EU dual-region doesn't even exist; dual-regions are within a continent) adds cost."
},
{
d: "Storage & Data Lakes",
q: "In a lakehouse layout, raw ingested files land in one zone, cleansed/conformed data in another, and business-ready aggregates in a third. Why keep the raw zone immutable?",
o: [
"Immutability is required by all GCP services.",
"So you can always reprocess from source truth when transformation logic changes or bugs are found, and support audit/lineage.",
"Raw files compress better when immutable.",
"To reduce storage cost."
],
a: 1,
e: "The raw zone is your replayable source of truth: if a transformation bug corrupts curated data, you rebuild from raw. Mutating raw data destroys that guarantee and breaks auditability."
},
{
d: "Storage & Data Lakes",
q: "A team accidentally deleted objects from a bucket last week. You want cheap protection against accidental deletion going forward, with the ability to restore prior versions of overwritten files. What do you enable?",
o: [
"Object versioning, with lifecycle rules to expire noncurrent versions after N days.",
"A locked retention policy.",
"Turbo replication.",
"Bucket Lock plus Requester Pays."
],
a: 0,
e: "Versioning keeps noncurrent versions on delete/overwrite so you can restore them; lifecycle rules cap the cost by expiring old versions. A locked retention policy is WORM compliance — overkill and irreversible. (Soft delete also provides a short safety window by default.)"
},
{
d: "Storage & Data Lakes",
q: "You must transfer 300 TB from an on-prem NAS to Cloud Storage over a 10 Gbps link within a month, with scheduled incremental syncs afterward. What should you use?",
o: [
"gsutil cp in a for loop.",
"Storage Transfer Service with an on-prem agent pool.",
"Transfer Appliance.",
"BigQuery Data Transfer Service."
],
a: 1,
e: "Storage Transfer Service for on-premises data handles large-scale, parallelized, resumable transfers with scheduling and incremental sync. 300 TB over 10 Gbps is ~3 days of transfer time, so no appliance is needed; gsutil/gcloud storage doesn't manage scheduled incremental jobs at this scale. Transfer Appliance is for poor connectivity."
},
{
d: "Storage & Data Lakes",
q: "Which statement about Cloud Storage consistency is correct?",
o: [
"Listings are eventually consistent, so newly written objects may be missing from lists for minutes.",
"Cloud Storage is strongly consistent: after a successful write, reads and listings immediately reflect the object.",
"Only multi-region buckets are strongly consistent.",
"Consistency must be enabled per bucket."
],
a: 1,
e: "Cloud Storage provides strong global consistency for read-after-write, read-after-update/delete, and object listing — a pipeline can safely list a bucket immediately after writing to discover the new objects."
},

// ------------------------------------------------- Databases
{
d: "Databases",
q: "A global retail app needs a relational database with SQL, ACID transactions, 99.999% availability, and horizontal write scaling across continents. Which service fits?",
o: [
"Cloud SQL for PostgreSQL with read replicas",
"Cloud Spanner",
"Bigtable",
"Firestore"
],
a: 1,
e: "Spanner is the only option offering relational semantics with strongly consistent, horizontally scalable writes and multi-region 99.999% SLA. Cloud SQL scales reads with replicas but writes are limited to one primary; Bigtable and Firestore are NoSQL."
},
{
d: "Databases",
q: "You're storing time-series sensor data: billions of rows/day, single-row reads and writes by key, sub-10 ms latency, no SQL joins needed. Which database is designed for this?",
o: [
"Cloud SQL",
"BigQuery",
"Bigtable",
"Firestore"
],
a: 2,
e: "Bigtable is a wide-column NoSQL store built for massive write throughput and low-latency key-based access — the canonical choice for time-series/IoT at scale. BigQuery is analytics (high-latency scans), Cloud SQL can't take this write volume, Firestore targets app documents, not this throughput profile."
},
{
d: "Databases",
q: "Your Bigtable cluster shows one node handling most traffic while others idle. Rows are keyed by timestamp. What's the root cause and fix?",
o: [
"Too few nodes — add more.",
"Sequential row keys hotspot a single tablet; redesign the key to distribute writes, e.g., prefix with sensor/device ID (field promotion) instead of leading with the timestamp.",
"HDD storage — switch to SSD.",
"The cluster needs a second app profile."
],
a: 1,
e: "Monotonically increasing keys (timestamps) send all writes to the tail tablet on one node. Designing keys as device_id#reversed_or_bucketed_timestamp spreads load. Adding nodes doesn't help when the key design forces all writes to one range."
},
{
d: "Databases",
q: "In Spanner, which primary key design risks hotspotting, and what's a recommended alternative?",
o: [
"UUIDv4 keys risk hotspots; use sequential integers instead.",
"Monotonically increasing keys (timestamps, auto-increment IDs) hotspot the last split; use UUIDs, bit-reversed sequences, or hash-prefixed keys.",
"Composite keys always hotspot; use single-column keys.",
"String keys hotspot; use integers."
],
a: 1,
e: "Like Bigtable, Spanner splits data by key ranges — sequential keys concentrate inserts on the final split. UUIDv4, bit-reversed sequence, or a shard/hash prefix distributes inserts across splits."
},
{
d: "Databases",
q: "An existing app uses MySQL on-prem and must move to GCP with minimal code change; workload fits on one machine with read scaling. What's the right target?",
o: [
"Cloud SQL for MySQL (with read replicas as needed)",
"Spanner",
"Bigtable",
"AlloyDB for PostgreSQL"
],
a: 0,
e: "Cloud SQL for MySQL is the managed drop-in: same engine, minimal code change, vertical scaling plus read replicas. Spanner would require schema/app rework; AlloyDB is PostgreSQL-compatible, not MySQL."
},
{
d: "Databases",
q: "A gaming leaderboard needs sub-millisecond reads of session state and counters, with data that can be rebuilt if lost. Which service?",
o: [
"Firestore",
"Memorystore (Redis)",
"Spanner",
"Cloud SQL"
],
a: 1,
e: "Sub-millisecond latency and tolerable data loss is the classic in-memory cache profile — Memorystore for Redis. The persistent databases are all slower and more expensive per operation for this use."
},
{
d: "Databases",
q: "A mobile/web app needs a document database with real-time listeners, offline sync on devices, and automatic scaling. Which service?",
o: [
"Bigtable",
"Firestore",
"Cloud SQL",
"Memorystore"
],
a: 1,
e: "Firestore is the serverless document DB with real-time synchronization and offline support in mobile/web SDKs. None of the others offer client-side sync or realtime listeners natively."
},
{
d: "Databases",
q: "Which is TRUE about Bigtable schema design?",
o: [
"Design for many small tables, one per query pattern.",
"Store related entities in tall narrow tables, design the row key around your most common query, and avoid storing more than ~100 MB per row.",
"Secondary indexes make row-key design unimportant.",
"Joins across tables are executed server-side."
],
a: 1,
e: "In Bigtable everything hinges on the row key: reads are efficient by key or key range only. Keep rows reasonably sized, prefer tall/narrow layouts for time series. There are no joins or (classically) secondary indexes, so the key must serve the dominant access pattern."
},
{
d: "Databases",
q: "You need to run occasional analytical SQL over data that lives in Cloud SQL without building a pipeline. What's the lightest-weight approach?",
o: [
"Nightly Dataflow export to BigQuery.",
"BigQuery federated queries via EXTERNAL_QUERY against the Cloud SQL instance (or Cloud SQL federation connection).",
"Datastream CDC into BigQuery.",
"Manual CSV exports."
],
a: 1,
e: "Federated queries let BigQuery push a query to Cloud SQL and use the result — no pipeline, always-current data. For heavy/continuous analytics you'd graduate to Datastream CDC, but for occasional queries federation is the minimal solution."
},
{
d: "Databases",
q: "Spanner CPU utilization is sustained at 90% and latencies are rising. The instance uses manual configuration. What's the immediate correct action?",
o: [
"Reduce the session pool size in clients.",
"Add compute capacity (nodes/processing units) — or enable autoscaling; Google recommends keeping regional instances below ~65% CPU (multi-region below ~45%).",
"Switch to HDD storage.",
"Shard the database manually across two instances."
],
a: 1,
e: "Sustained high-priority CPU above the recommended threshold degrades latency; adding processing units (or the managed autoscaler) is the designed remedy. Spanner already shards automatically — manual sharding across instances defeats its purpose."
},
{
d: "Databases",
q: "Which consistency guarantee does Spanner provide for reads by default, thanks to TrueTime?",
o: [
"Eventual consistency",
"External consistency (strict serializability) — transactions appear to execute in a globally consistent order; strong reads see all previously committed data.",
"Read-your-writes only within a session",
"Causal consistency only"
],
a: 1,
e: "Spanner's TrueTime-based commit timestamps give external consistency, the strongest practical guarantee. It also offers cheaper bounded-staleness/exact-timestamp reads when you can tolerate stale data."
},
{
d: "Databases",
q: "A reporting workload on Bigtable is interfering with the latency-sensitive serving workload on the same instance. What is the recommended isolation mechanism?",
o: [
"Run reports only at night.",
"Add a second cluster (replication) and use app profiles to route the analytics traffic to it — e.g., single-cluster routing per workload.",
"Move reports to a bigger VM.",
"Enable request priorities in the client library."
],
a: 1,
e: "Bigtable replication plus app profiles is the documented pattern for workload isolation: serving traffic routes to one cluster, batch/analytics to another, so heavy scans don't affect serving latency."
},
{
d: "Databases",
q: "You need strongly consistent secondary lookups on a Bigtable-scale time-series dataset — e.g., query by customer AND by device. Bigtable's single row key can't serve both. What's a standard pattern?",
o: [
"Enable Bigtable secondary indexes.",
"Maintain a second table (or key-prefix pattern) keyed by the other access path, written by the pipeline — i.e., application-managed index tables.",
"Use SQL JOINs in Bigtable.",
"Switch all data to Cloud SQL."
],
a: 1,
e: "The classic Bigtable pattern is to write the data twice under different keys (or maintain an index table) so each dominant query has a key-served path. The pipeline keeps them in sync. (If you need rich secondary indexing with SQL, that's a signal to consider Spanner.)"
},
{
d: "Databases",
q: "Cloud SQL: you need high availability with automatic failover for a production instance. What does enabling HA actually provision?",
o: [
"A read replica promoted manually on failure.",
"A standby instance in a different zone of the same region, kept in sync via regional persistent disk (synchronous replication), with automatic failover.",
"A second primary in another region with bidirectional replication.",
"Hourly snapshots restored on failure."
],
a: 1,
e: "Cloud SQL HA uses a regional (synchronously replicated) disk with a standby in another zone; failover is automatic and the instance IP is preserved. Read replicas are asynchronous and for scaling reads or cross-region DR (manual promotion)."
},

// ------------------------------------------------- Pub/Sub & Streaming
{
d: "Pub/Sub & Streaming",
q: "Two independent services must each receive every message published to a topic. How do you configure Pub/Sub?",
o: [
"Both services pull from one shared subscription.",
"Create one subscription per service — each subscription gets its own copy of every message.",
"Publish every message twice.",
"Use two topics with duplicated publishers."
],
a: 1,
e: "Fan-out is per subscription: every subscription on a topic independently receives all messages. Multiple consumers sharing ONE subscription instead split (load-balance) the messages between them."
},
{
d: "Pub/Sub & Streaming",
q: "A subscriber processes a message successfully but crashes before acknowledging it. What happens?",
o: [
"The message is lost.",
"Pub/Sub redelivers the message after the ack deadline expires — consumers must therefore be idempotent (at-least-once delivery).",
"Pub/Sub detects the crash and marks it acknowledged.",
"The message moves to the dead-letter topic immediately."
],
a: 1,
e: "Unacked messages are redelivered after the ack deadline — that's at-least-once delivery, and why processing should be idempotent (or use exactly-once delivery subscriptions / Dataflow deduplication). Dead-lettering only kicks in after the configured number of delivery attempts."
},
{
d: "Pub/Sub & Streaming",
q: "Messages for the same order ID must be processed in the order they were published. What must you configure?",
o: [
"Nothing — Pub/Sub always preserves order.",
"Publish with an ordering key (the order ID) to a topic and enable message ordering on the subscription; messages with the same key in the same region are delivered in order.",
"Use a single-threaded subscriber.",
"Set message priority fields."
],
a: 1,
e: "Ordering keys give per-key ordered delivery (same region). Without them Pub/Sub makes no ordering guarantee. A single-threaded subscriber alone can't fix order because redelivery and multiple publishers can still interleave."
},
{
d: "Pub/Sub & Streaming",
q: "A malformed message keeps failing in your subscriber and is being redelivered forever, blocking alert noise. What's the standard remedy?",
o: [
"Increase the ack deadline to 10 minutes.",
"Configure a dead-letter topic with a maximum number of delivery attempts, and alert/inspect from the DLQ.",
"Restart the subscriber daily.",
"Delete and recreate the subscription."
],
a: 1,
e: "Dead-letter topics catch poison messages after N failed deliveries, unblocking the main flow while preserving the message for inspection and replay. Remember to grant the Pub/Sub service account publish rights on the DLQ topic."
},
{
d: "Pub/Sub & Streaming",
q: "You want to land Pub/Sub messages in BigQuery with no transformation and minimal ops. What's the simplest supported path?",
o: [
"A custom subscriber on GKE writing rows.",
"A BigQuery subscription on the topic (Pub/Sub writes directly via the Storage Write API).",
"A Dataflow job — it is mandatory for BigQuery delivery.",
"Cloud Functions triggered per message."
],
a: 1,
e: "BigQuery subscriptions write messages straight into a table (optionally mapping the topic schema to columns) with no pipeline to run. Dataflow becomes the right answer only when you need transformation, enrichment, windowing, or exactly-once processing logic."
},
{
d: "Pub/Sub & Streaming",
q: "Your subscriber fleet was down for 3 hours during an incident. Standard subscription, default retention. What is true?",
o: [
"All messages from the outage are gone.",
"Unacknowledged messages are retained (default 7 days), so subscribers resume and drain the backlog when they recover.",
"Messages older than 10 minutes are dropped.",
"You must replay from the publisher."
],
a: 1,
e: "Pub/Sub retains unacked messages for the retention window (default 7 days). Backlogged messages are delivered when subscribers return. Additionally, with topic retention or subscription retain-acked plus seek, you can even replay already-acked messages."
},
{
d: "Pub/Sub & Streaming",
q: "After a bad code deploy, you need to reprocess the last 24 hours of already-acknowledged messages on a subscription. What makes this possible?",
o: [
"Ack'd messages can never be re-read.",
"Enable retain_acked_messages (or topic retention) and use seek to a timestamp 24 hours ago (or to a snapshot taken before the deploy).",
"Ask publishers to republish.",
"Export Pub/Sub logs and parse them."
],
a: 1,
e: "Seek rewinds a subscription to a past timestamp or snapshot. It requires the messages to still be retained — via retain-acked on the subscription or message retention on the topic. Snapshots taken before risky deploys are the safest pattern."
},
{
d: "Pub/Sub & Streaming",
q: "Publishers occasionally send messages that don't match the expected Avro structure, breaking downstream consumers. How do you enforce the contract at the topic?",
o: [
"Validate in every consumer.",
"Attach a schema (Avro or Protocol Buffers) to the topic — Pub/Sub rejects non-conforming publishes; evolve with compatible revisions.",
"Use message attributes to flag versions.",
"Switch to JSON."
],
a: 1,
e: "Topic schemas validate at publish time, moving the contract to the boundary. Schema revisions allow compatible evolution. Consumer-side validation catches bad data too late — after it's already in the stream."
},
{
d: "Pub/Sub & Streaming",
q: "In streaming, what is a watermark?",
o: [
"A cryptographic signature on each message.",
"The system's notion of event-time progress — an estimate that all events with timestamps earlier than the watermark have (probably) arrived, used to decide when windows can close.",
"The maximum throughput of a topic.",
"A marker written to storage after each checkpoint."
],
a: 1,
e: "Watermarks track event-time completeness. When the watermark passes a window's end, the window can fire/close; events arriving after that are 'late data' handled by allowed lateness and triggers."
},
{
d: "Pub/Sub & Streaming",
q: "You must guarantee a message is published to Pub/Sub if-and-only-if a database transaction commits (no dual-write inconsistency). Which pattern addresses this?",
o: [
"Publish first, then commit the transaction.",
"Transactional outbox: write the event to an outbox table in the same transaction, and a separate process (e.g., CDC via Datastream or a poller) publishes from the outbox.",
"Publish and commit in parallel threads for speed.",
"Two-phase commit between Pub/Sub and the database."
],
a: 1,
e: "Pub/Sub doesn't participate in database transactions. The outbox pattern makes the event part of the DB transaction and asynchronously relays it, achieving effectively exactly-once handoff. Publish-then-commit or commit-then-publish each risks one side succeeding alone."
},
{
d: "Pub/Sub & Streaming",
q: "What does enabling 'exactly-once delivery' on a Pub/Sub subscription actually guarantee?",
o: [
"Each message is processed exactly once end-to-end, including your side effects.",
"While a message's ack deadline is respected, Pub/Sub will not redeliver a successfully-acknowledged message, and no redelivery occurs while the deadline hasn't expired — removing Pub/Sub-side duplicates within the subscription.",
"Publishers cannot publish the same payload twice.",
"Ordering is also guaranteed automatically."
],
a: 1,
e: "Exactly-once delivery eliminates Pub/Sub-originated redeliveries of acknowledged messages for a subscription. It cannot make your downstream side effects idempotent, dedupe publisher-side duplicates, or order messages — those remain application concerns (or Dataflow's)."
},
{
d: "Pub/Sub & Streaming",
q: "An IoT fleet must stream telemetry into GCP for real-time processing with per-device backpressure-tolerant ingestion, then analytics in BigQuery. Which canonical GCP architecture applies?",
o: [
"Devices → Cloud SQL → BigQuery replication",
"Devices → Pub/Sub → Dataflow (transform/window/dedupe) → BigQuery (and GCS for raw archive)",
"Devices → Bigtable → manual exports",
"Devices → Cloud Functions → Sheets"
],
a: 1,
e: "Pub/Sub absorbs bursty global ingestion and decouples producers from consumers; Dataflow does streaming transformation/enrichment/exactly-once processing; BigQuery serves analytics; GCS keeps replayable raw archives. This is the standard GCP streaming reference architecture."
},

// ------------------------------------------------- Dataflow & Beam
{
d: "Dataflow & Beam",
q: "You need per-user session analytics where a session ends after 30 minutes of inactivity. Which Beam windowing strategy applies?",
o: [
"Fixed windows of 30 minutes",
"Sliding windows of 30 minutes every 5 minutes",
"Session windows with a 30-minute gap duration, keyed by user",
"Global window with a repeating trigger"
],
a: 2,
e: "Session windows group elements per key into activity bursts separated by a minimum gap — exactly the 'session ends after 30 idle minutes' semantics. Fixed/sliding windows cut on wall-clock boundaries regardless of activity."
},
{
d: "Dataflow & Beam",
q: "A streaming pipeline must compute a 10-minute moving average, updated every minute. Which window type?",
o: [
"Fixed 10-minute windows",
"Sliding windows: 10-minute duration, 1-minute period",
"Session windows with 1-minute gap",
"Two pipelines with different fixed windows"
],
a: 1,
e: "Sliding (hopping) windows of duration 10 min and period 1 min produce overlapping windows so each minute you emit an average over the trailing 10 minutes. Fixed windows would only update every 10 minutes."
},
{
d: "Dataflow & Beam",
q: "Events can arrive up to 2 hours late, but you want early results too. How do you configure the window?",
o: [
"Increase the watermark manually.",
"Set allowed lateness to 2 hours with an early/late firing trigger (e.g., early firings every minute, late firings on each late element) and an accumulation mode.",
"Drop late data — Beam cannot handle it.",
"Buffer events in Redis before the pipeline."
],
a: 1,
e: "Allowed lateness keeps window state alive past the watermark so late data can update results; triggers control speculative (early) and corrective (late) firings; accumulating vs discarding mode decides whether firings include prior data. This is Beam's core lateness model."
},
{
d: "Dataflow & Beam",
q: "Your Dataflow streaming job's system lag keeps growing and the watermark stalls. Autoscaling is on but stuck at max workers. A single transform shows a massive fan-in on one key. What's the likely cause?",
o: [
"Pub/Sub is throttling the subscription.",
"A hot key — one key receives a disproportionate share of elements, serializing work on one worker; fix by salting/sharding the key or using combiner lifting.",
"Workers are in the wrong zone.",
"The job needs more disk."
],
a: 1,
e: "Grouping operations process each key on a single worker, so a hot key caps parallelism no matter how many workers exist. Salting keys (adding a shard suffix then re-combining), or using Combine with combiner lifting, spreads the load. (Dataflow can also flag hot keys in the UI.)"
},
{
d: "Dataflow & Beam",
q: "You must update a running streaming Dataflow job with new code without losing in-flight data or duplicating output. What are the supported options?",
o: [
"Kill and restart the job — state loss is unavoidable.",
"Use an in-place update (--update, with compatible transform mapping) or drain the job (finish in-flight work, stop reading) and launch the new version.",
"Pause the job and edit the code on the workers.",
"Snapshot the VMs with Compute Engine."
],
a: 1,
e: "Dataflow supports in-place updates that transfer state when the new graph is compatible, and 'drain' which stops ingestion while completing buffered work. Cancel drops in-flight data; there's no pausing/live-editing of workers."
},
{
d: "Dataflow & Beam",
q: "In Beam, what's the difference between event time and processing time?",
o: [
"They are synonyms.",
"Event time is when the event actually occurred (embedded timestamp); processing time is when the pipeline happens to process it. Correct windowed results require event time, since arrival can be delayed and out of order.",
"Event time only exists in batch pipelines.",
"Processing time is always earlier than event time."
],
a: 1,
e: "The gap between event time and processing time (skew) is why watermarks, allowed lateness, and triggers exist: data arrives late and out of order, but analytics usually need results organized by when events truly happened."
},
{
d: "Dataflow & Beam",
q: "A batch Dataflow job is cost-sensitive and not urgent. Which two features cut its cost most directly?",
o: [
"Streaming Engine and exactly-once mode",
"FlexRS (flexible resource scheduling with preemptible/spot resources and delayed scheduling) and rightsizing machine types; Dataflow Shuffle offloads shuffle for better efficiency",
"More max workers",
"Running it in two regions simultaneously"
],
a: 1,
e: "FlexRS trades start-time flexibility (jobs may be delayed up to ~6 hours) for heavily discounted preemptible-based compute — ideal for non-urgent batch. Service-based Dataflow Shuffle improves efficiency and autoscaling. More workers or dual regions increase cost."
},
{
d: "Dataflow & Beam",
q: "Your streaming pipeline writes to BigQuery and must not produce duplicate rows even when workers retry. Within the Dataflow → BigQuery path, what provides exactly-once results?",
o: [
"Nothing — duplicates are unavoidable in streaming.",
"Dataflow's exactly-once processing (checkpointed state, deduplicated Pub/Sub reads by message ID or record ID) combined with the Storage Write API sink's exactly-once semantics.",
"Setting a primary key on the BigQuery table.",
"Manually de-duplicating with a nightly query."
],
a: 1,
e: "Dataflow provides exactly-once processing internally, and the BigQuery Storage Write API supports exactly-once appends via stream offsets. End to end you still design idempotency at the edges, but the Dataflow+Storage Write API path is the supported exactly-once combination. BigQuery has no enforced primary keys."
},
{
d: "Dataflow & Beam",
q: "What is a side input in Beam, and when does it become a problem?",
o: [
"A secondary Pub/Sub topic; it fails if empty.",
"An additional (usually small) input available to every element of a ParDo — e.g., a lookup/config map; it becomes a problem when it's too large to fit in worker memory or updates too frequently in streaming.",
"The error output of a transform.",
"A debug log channel."
],
a: 1,
e: "Side inputs broadcast auxiliary data (dimension tables, config) to all workers. They must be reasonably small/broadcastable; for large or fast-changing lookups, prefer CoGroupByKey joins, state APIs, or external lookups with caching."
},
{
d: "Dataflow & Beam",
q: "The same Beam pipeline code must run both as a nightly batch over GCS files and as a real-time stream from Pub/Sub. What makes this possible?",
o: [
"It's not possible; batch and streaming need different frameworks.",
"Beam's unified model: PCollections are bounded or unbounded, so the same transforms work in both modes — just swap the source and pick the runner mode.",
"Only Spark Structured Streaming supports this.",
"Writing two pipelines that share a library."
],
a: 1,
e: "Beam's core abstraction — bounded vs unbounded PCollections with the same transform/windowing model — is exactly this batch/streaming unification. Swap ReadFromText for ReadFromPubSub and the business logic stays identical."
},
{
d: "Dataflow & Beam",
q: "A non-programmer team needs a standard stream: Pub/Sub topic → BigQuery table with a simple UDF tweak. Fastest supported route?",
o: [
"Write a custom Java pipeline from scratch.",
"Use the Google-provided Dataflow template (Pub/Sub to BigQuery), optionally with a JavaScript UDF, launched from the console.",
"Build a Spark job on Dataproc.",
"Use BigQuery scheduled queries."
],
a: 1,
e: "Google-provided (classic/flex) templates cover common paths like Pub/Sub→BigQuery and accept a JS UDF for light transformation — launchable from the console/CLI with no code. That's the low-effort path; custom pipelines are for real logic."
},
{
d: "Dataflow & Beam",
q: "Your streaming job needs to remember, per key, the last event's value to compute deltas, with timers to expire idle keys. Which Beam feature?",
o: [
"Global variables in the DoFn.",
"The State and Timers API in a stateful ParDo (per-key state cells, event/processing-time timers).",
"A side output.",
"Reshuffle."
],
a: 1,
e: "Stateful processing gives durable per-key, per-window state (ValueState, BagState, etc.) plus timers for expiry/callbacks — the supported way to keep last-seen values. DoFn instance variables aren't durable or key-scoped; workers restart and rebalance."
},
{
d: "Dataflow & Beam",
q: "Dataflow autoscaling for streaming jobs primarily reacts to which signals?",
o: [
"Time of day.",
"Backlog (e.g., Pub/Sub backlog / stage lag) and worker CPU utilization — scaling up when backlog grows and down when workers are underutilized.",
"Number of open user sessions.",
"BigQuery slot availability."
],
a: 1,
e: "Streaming autoscaling (with Streaming Engine) targets keeping backlog low: it adds workers when backlog/lag grows and removes them when CPU and backlog indicate over-provisioning. Understanding this helps diagnose stuck-at-max scenarios like hot keys."
},
{
d: "Dataflow & Beam",
q: "Security requires that Dataflow workers have no public IPs and all traffic stays on the VPC. What do you configure?",
o: [
"It isn't possible; Dataflow requires public IPs.",
"Launch jobs with --no_use_public_ips (usePublicIps=false) into a VPC/subnetwork with Private Google Access enabled (or via VPC-SC perimeter).",
"A firewall rule blocking egress.",
"An external HTTP proxy."
],
a: 1,
e: "Dataflow supports private-IP-only workers; Private Google Access lets them reach Google APIs (GCS, BigQuery, Pub/Sub) without public addresses. Blocking egress via firewall without PGA breaks the job."
},

// ------------------------------------------------- Dataproc & Hadoop
{
d: "Dataproc & Hadoop",
q: "You're migrating an on-prem Hadoop cluster to GCP. The recommended pattern for storage is:",
o: [
"Keep everything in HDFS on persistent disks.",
"Move data to Cloud Storage (using the GCS connector, gs:// paths) and treat Dataproc clusters as ephemeral, job-scoped compute.",
"Store data in BigQuery and access it via HDFS API.",
"Use local SSDs for durability."
],
a: 1,
e: "Decoupling storage (GCS) from compute (ephemeral Dataproc) is THE Hadoop-migration pattern: clusters become disposable, data survives cluster deletion, and you stop paying for idle nodes. HDFS remains only as scratch space."
},
{
d: "Dataproc & Hadoop",
q: "A nightly Spark job runs 2 hours on a long-lived 20-node Dataproc cluster that sits idle the other 22 hours. Best cost fix?",
o: [
"Resize to 10 nodes.",
"Create an ephemeral cluster per run (workflow template / Composer), use preemptible/spot secondary workers, and delete the cluster after the job — or move the job to Dataproc Serverless for Spark.",
"Switch the cluster to HDD boot disks.",
"Run the job weekly instead."
],
a: 1,
e: "Ephemeral clusters mean you pay only for the 2 hours; spot secondary workers cut that further (they do no HDFS storage, so they're safe to lose with GCS-based data). Dataproc Serverless removes cluster management entirely for Spark batch."
},
{
d: "Dataproc & Hadoop",
q: "Which workers can be preemptible/spot in Dataproc, and what's the caveat?",
o: [
"Primary workers; no caveat.",
"Secondary workers can be spot/preemptible; they don't store HDFS data, and too high a spot fraction can cause task churn if reclaimed — keep data on GCS and size primaries for stability.",
"Masters only.",
"All nodes must be the same type."
],
a: 1,
e: "Secondary workers are compute-only (no HDFS datanodes), so losing them costs retries, not data. Best practice: modest spot ratio, data on GCS, and enough primary workers for shuffle stability."
},
{
d: "Dataproc & Hadoop",
q: "Your Spark job on Dataproc reads gs:// data and shows executors idle while a few tasks run forever. Input is 4 huge gzip files. Why?",
o: [
"GCS is slow.",
"Gzip files are not splittable, so parallelism is capped at 4 tasks; use splittable formats/compression (e.g., Parquet with Snappy, or uncompressed/bzip2) or pre-split the data.",
"The cluster needs more RAM.",
"YARN queues are misconfigured."
],
a: 1,
e: "One gzip stream = one task. Four files means max four parallel readers regardless of cluster size. Columnar splittable formats (Parquet/ORC with snappy) restore parallelism and are the standard lake format anyway."
},
{
d: "Dataproc & Hadoop",
q: "You need to run an existing Hive metastore-dependent stack (Hive, Spark SQL, Presto/Trino) across multiple ephemeral clusters that must share table metadata. What's the managed answer?",
o: [
"Re-create metastore tables at cluster startup with init scripts.",
"Dataproc Metastore (managed Hive metastore) shared by all clusters (or BigLake Metastore for BigQuery interop).",
"Store metadata in a text file on GCS.",
"One giant permanent cluster."
],
a: 1,
e: "Dataproc Metastore is the managed, highly available Hive metastore that ephemeral clusters attach to, so tables persist across cluster lifecycles. Init-script rebuilds are fragile; a permanent cluster defeats the ephemeral model."
},
{
d: "Dataproc & Hadoop",
q: "A data science team wants interactive PySpark notebooks against Dataproc without managing SSH tunnels. Which integration is designed for this?",
o: [
"Screen-sharing a laptop running Jupyter.",
"Dataproc's Jupyter/JupyterLab optional component with Component Gateway (or Vertex AI Workbench / BigQuery Studio Spark connections).",
"Running Jupyter on the master via cron.",
"Cloud Shell only."
],
a: 1,
e: "The Jupyter optional component plus Component Gateway exposes secure, IAM-controlled notebook UIs on the cluster without tunnels. Vertex AI Workbench can also attach to Dataproc kernels."
},
{
d: "Dataproc & Hadoop",
q: "When should you choose Dataproc over Dataflow for a new pipeline?",
o: [
"Always — Dataproc is newer.",
"When you have existing Spark/Hadoop code, dependencies on that ecosystem (Hive, HBase, MLlib), or teams with deep Spark expertise; choose Dataflow for new pipelines wanting serverless, unified batch/streaming without cluster ops.",
"Whenever the data exceeds 1 TB.",
"Only for streaming workloads."
],
a: 1,
e: "The exam's rule of thumb: existing Hadoop/Spark investment → Dataproc (lift-and-shift friendly); greenfield GCP-native pipelines → Dataflow (serverless, autoscaling, unified model). Data size alone doesn't decide it."
},
{
d: "Dataproc & Hadoop",
q: "You want Spark jobs without provisioning or tuning any cluster at all — submit code, get results, pay per job. Which offering?",
o: [
"Dataproc on GKE",
"Dataproc Serverless for Spark (Google-managed execution; now also surfaced as BigQuery serverless Spark)",
"A 2-node standard cluster",
"Cloud Run jobs with PySpark installed"
],
a: 1,
e: "Dataproc Serverless accepts Spark batch workloads with no cluster lifecycle to manage — autoscaling and infrastructure are Google's problem. Dataproc on GKE still requires a GKE cluster."
},

// ------------------------------------------------- Orchestration & Integration
{
d: "Orchestration & Integration",
q: "You orchestrate 40 interdependent daily jobs (BigQuery loads, Dataflow jobs, quality checks) with retries, backfills, and SLA alerts. Which service is designed for this?",
o: [
"Cloud Scheduler with many cron entries",
"Cloud Composer (managed Apache Airflow) DAGs",
"A shell script on a VM",
"Pub/Sub with ordered delivery"
],
a: 1,
e: "Composer/Airflow models dependencies as DAGs with retries, backfill, SLAs, sensors, and rich GCP operators. Cloud Scheduler is fine for triggering a single job on cron, but it has no dependency management or backfill."
},
{
d: "Orchestration & Integration",
q: "An Airflow task that loads a daily partition sometimes reruns after transient failures. What property must the task have so reruns don't corrupt data?",
o: [
"Priority weight",
"Idempotency — running the task twice for the same logical date yields the same result (e.g., WRITE_TRUNCATE into the date partition or MERGE keyed on the date), never blind appends.",
"A longer timeout",
"Depends_on_past = True"
],
a: 1,
e: "Retries and backfills mean any task can run more than once for the same logical date. Partition-overwrite or MERGE semantics make repeats safe; plain INSERT/append duplicates data on every retry."
},
{
d: "Orchestration & Integration",
q: "A DAG must start processing only after a file arrives in a GCS bucket, without wasting a worker slot while waiting for hours. Which Airflow construct?",
o: [
"A PythonOperator polling in a while loop.",
"A sensor (e.g., GCSObjectExistenceSensor) in deferrable or reschedule mode.",
"A 12-hour sleep task.",
"Manually triggering the DAG."
],
a: 1,
e: "Sensors wait for external conditions; reschedule/deferrable modes free the worker slot between pokes so long waits don't consume capacity. Busy-wait loops and sleeps hold slots and starve the scheduler."
},
{
d: "Orchestration & Integration",
q: "Analysts (not engineers) need to build ETL pipelines visually, with prebuilt connectors to SaaS sources and on-prem databases, running on GCP. Which service targets this?",
o: [
"Dataflow SQL",
"Cloud Data Fusion (graphical, CDAP-based ETL with 150+ connectors; executes on Dataproc under the hood)",
"Cloud Build",
"BigQuery Data Transfer Service"
],
a: 1,
e: "Data Fusion is the code-free, drag-and-drop pipeline builder with a large connector library — the exam's answer for 'visual ETL tool for non-programmers'. BQ DTS only loads into BigQuery from specific sources on a schedule."
},
{
d: "Orchestration & Integration",
q: "You need continuous, low-latency replication of an on-prem Oracle/MySQL/PostgreSQL database into BigQuery for analytics, without touching application code. Which service?",
o: [
"Storage Transfer Service",
"Datastream (serverless CDC), typically Datastream → BigQuery directly or via Dataflow templates",
"Nightly mysqldump to GCS",
"Database Migration Service only"
],
a: 1,
e: "Datastream reads the database's change log (CDC) and streams inserts/updates/deletes into BigQuery (or GCS) with minimal source impact. DMS is for migrating/replicating into Cloud SQL/AlloyDB as a database, not analytics feeds."
},
{
d: "Orchestration & Integration",
q: "You need Google Ads, YouTube, and Google Analytics data landed in BigQuery on a schedule with zero pipeline code. What's the intended tool?",
o: [
"BigQuery Data Transfer Service",
"Custom Python + Composer",
"Dataflow flex templates",
"Fivetran only"
],
a: 0,
e: "BigQuery Data Transfer Service has native, scheduled, fully-managed connectors for Google SaaS sources (Ads, GA4, YouTube), plus S3/Redshift/Teradata migrations — no code, lands straight into BigQuery datasets."
},
{
d: "Orchestration & Integration",
q: "In Composer, where do you put DAG files so the environment picks them up?",
o: [
"SSH into the scheduler VM and copy files to /opt/airflow.",
"Upload them to the environment's GCS bucket dags/ folder (typically via CI/CD sync).",
"Paste code into the Airflow UI.",
"Attach them to a Pub/Sub message."
],
a: 1,
e: "Each Composer environment has a dedicated bucket; the dags/ prefix is synchronized to the Airflow workers/scheduler. Best practice is CI/CD (e.g., Cloud Build) that tests then syncs DAGs to the bucket — no SSH access exists."
},
{
d: "Orchestration & Integration",
q: "A workflow is simple: call three HTTP/Cloud Run services in sequence with a retry, triggered by an event, at minimal cost. Composer feels heavy. What's the lighter GCP-native option?",
o: [
"Cloud Workflows (serverless step orchestration, pay-per-step, YAML-defined) triggered via Eventarc",
"A bigger Composer environment",
"Cron on a GCE VM",
"Dataproc workflow templates"
],
a: 0,
e: "Cloud Workflows is the serverless, low-cost orchestrator for service-to-service call sequences with retries/conditionals — no environment to run 24/7. Composer earns its cost when you need Airflow's ecosystem: complex DAGs, sensors, backfills."
},

// ------------------------------------------------- Security & Governance
{
d: "Security & Governance",
q: "A data scientist needs to run queries in a dataset and create tables with results, but must not be able to grant access to others or delete the dataset. Which principle and role apply?",
o: [
"Grant Project Editor for convenience.",
"Least privilege: grant BigQuery Data Editor on that specific dataset (plus BigQuery Job User on the project to run jobs).",
"Grant BigQuery Admin on the project.",
"Add them to the Owners group."
],
a: 1,
e: "Dataset-scoped Data Editor allows reading and writing tables in just that dataset; Job User allows running query jobs. Admin/Editor/Owner all violate least privilege by including IAM-granting or destructive permissions."
},
{
d: "Security & Governance",
q: "Compliance mandates that you control and be able to revoke the encryption keys protecting BigQuery and GCS data, with rotation you manage. What do you use?",
o: [
"Default Google-managed encryption (no action needed).",
"Customer-managed encryption keys (CMEK) in Cloud KMS, referenced by the datasets/buckets; revoke/disable the key to cut access.",
"Client-side encryption in every application.",
"TLS."
],
a: 1,
e: "CMEK keeps data encrypted under keys you control in Cloud KMS: you set rotation policy, and disabling/destroying the key makes the data unreadable. Google-managed default encryption exists but gives you no control or revocation; TLS protects data in transit only."
},
{
d: "Security & Governance",
q: "You must prevent data exfiltration: even a credentialed insider should not be able to copy data from your BigQuery/GCS projects to an outside project or the public internet. Which control addresses this at the service level?",
o: [
"VPC Service Controls perimeters around the projects (restricting API access across the perimeter boundary), with access levels for legitimate paths.",
"Stronger passwords.",
"Bucket-level IAM only.",
"Cloud Armor."
],
a: 0,
e: "VPC-SC creates a service perimeter: Google API calls that would move data across the boundary (e.g., copy a table to an external project) are blocked regardless of the caller's IAM permissions — this is THE exfiltration control for data services. IAM alone can't stop an authorized user's outbound copies."
},
{
d: "Security & Governance",
q: "Before sharing a support-ticket dataset with an analytics vendor, you must find and mask emails, phone numbers, and credit card numbers in free-text fields. Which service?",
o: [
"Cloud KMS",
"Sensitive Data Protection (Cloud DLP) — inspect with infoType detectors and de-identify (mask, redact, or tokenize with format-preserving encryption)",
"IAM Conditions",
"reCAPTCHA"
],
a: 1,
e: "Cloud DLP is purpose-built for discovering and transforming PII in text/images/BigQuery/GCS: 150+ infoType detectors, plus de-identification transforms including reversible tokenization. KMS encrypts whole resources, not selective PII in content."
},
{
d: "Security & Governance",
q: "Your organization needs a central place to discover datasets across projects, tag them with business metadata (owner, sensitivity), manage data quality checks, and organize lakes/zones. Which service?",
o: [
"Cloud Asset Inventory",
"Dataplex (Universal Catalog) — data discovery, cataloging with tags/taxonomies, quality tasks, lineage, and lake/zone governance",
"A Sheets registry",
"Cloud Logging"
],
a: 1,
e: "Dataplex (which absorbed Data Catalog) is GCP's data-governance fabric: automatic discovery/harvesting of metadata, business tags and policy-tag taxonomies, data-quality scans, lineage, and logical lakes/zones over GCS + BigQuery."
},
{
d: "Security & Governance",
q: "Auditors ask: 'Who queried table X last month, and who changed IAM on the dataset?' Where is the authoritative answer?",
o: [
"Ask team leads.",
"Cloud Audit Logs — BigQuery Data Access logs (queries/reads) and Admin Activity logs (IAM/config changes), ideally exported to BigQuery for analysis.",
"The BigQuery UI history tab of each user.",
"Billing reports."
],
a: 1,
e: "Admin Activity audit logs are always on; Data Access logs record reads/queries (on by default for BigQuery). A log sink to BigQuery makes them queryable for audits. Per-user UI history isn't centralized or authoritative."
},
{
d: "Security & Governance",
q: "A Dataflow job needs to read a GCS bucket and write BigQuery. How should it authenticate in production?",
o: [
"A developer's downloaded JSON key baked into the container.",
"A dedicated service account with least-privilege roles attached as the job's worker/controller service account — no exported keys.",
"OAuth tokens typed at deploy time.",
"An API key in an environment variable."
],
a: 1,
e: "Workloads should use attached service accounts and Google-managed credentials — exported JSON keys are a leak risk and an anti-pattern. Grant the SA only the bucket/dataset roles it needs."
},
{
d: "Security & Governance",
q: "Column-level security in BigQuery is implemented by:",
o: [
"GRANT SELECT(column) SQL statements.",
"Policy tags from a Dataplex/Data Catalog taxonomy attached to columns, with access via the Fine-Grained Reader role (optionally with masking rules).",
"Separate tables per sensitivity level, always.",
"Encrypting sensitive columns with AEAD and sharing keys."
],
a: 1,
e: "You define a taxonomy (e.g., PII > SSN), attach policy tags to columns, and only principals with Fine-Grained Reader on that tag can read those columns; others get denied or masked values. AEAD encryption is possible but is application-managed, not the native access-control mechanism."
},
{
d: "Security & Governance",
q: "Your company must keep all data and processing for an EU workload physically within the EU. Which practices apply?",
o: [
"Nothing — GCP handles residency automatically.",
"Choose EU regions/multi-region for buckets, datasets, and compute; constrain with the Resource Location organization policy; keep processing (Dataflow/Dataproc) in EU regions too.",
"Use a US multi-region with EU CMEK keys.",
"Only VPN traffic matters for residency."
],
a: 1,
e: "Data residency is set by resource locations. The org policy constraint gcp.resourceLocations enforces that new resources can only be created in allowed regions, preventing accidental US-located datasets. Keys' location doesn't relocate the data."
},
{
d: "Security & Governance",
q: "What's the difference between Admin Activity and Data Access audit logs?",
o: [
"They are identical streams with different names.",
"Admin Activity logs record configuration/metadata changes (always enabled, free); Data Access logs record reads of user data and can be voluminous (mostly disabled by default outside BigQuery, enableable per service).",
"Data Access logs only exist for VMs.",
"Admin Activity logs must be purchased."
],
a: 1,
e: "This distinction is a favorite: Admin Activity (who changed IAM/created datasets) is always on; Data Access (who read/queried data) is default-on for BigQuery but must be enabled for most other services and can generate significant volume/cost."
},

// ------------------------------------------------- ML & Analytics
{
d: "ML & Analytics",
q: "Your analysts know SQL but not Python. They want a churn-prediction model trained on data already in BigQuery, fast. What's the pragmatic first step?",
o: [
"Hire ML engineers to build a TensorFlow model on Vertex AI.",
"BigQuery ML: CREATE MODEL ... (e.g., logistic regression or boosted trees) directly in SQL over the existing tables, then ML.PREDICT / ML.EVALUATE.",
"Export data to laptops and use scikit-learn.",
"Wait for AutoML to discover the data."
],
a: 1,
e: "BQML trains and serves models with SQL where the data already lives — the exam's answer whenever 'analysts + SQL + data in BigQuery' appears. Vertex AI custom training is the escalation path for complex models, not the first step."
},
{
d: "ML & Analytics",
q: "A model performs well on training data but poorly on new data. What is this called and what's a standard mitigation?",
o: [
"Underfitting; add more layers.",
"Overfitting; use regularization (L1/L2), early stopping, more/better training data, or simpler models — and validate on held-out data.",
"Data drift; retrain hourly.",
"Label leakage; nothing can be done."
],
a: 1,
e: "High train/low test performance is overfitting: the model memorized noise. Regularization, early stopping, dropout, and more diverse data are canonical mitigations; a proper train/validation/test split detects it."
},
{
d: "ML & Analytics",
q: "Prediction-time accuracy is mysteriously worse than offline evaluation. You discover the serving system computes the 'days_since_last_purchase' feature differently than the training pipeline did. What is this problem and a canonical fix?",
o: [
"Underfitting; larger model.",
"Training/serving skew; centralize feature computation — e.g., a feature store (Vertex AI Feature Store) or shared transformation code so training and serving use identical features.",
"Cold start; more users.",
"Exploding gradients; clip them."
],
a: 1,
e: "When training features and serving features are computed by different code paths, skew silently degrades production accuracy. Sharing the transformation (feature store, TFX Transform, or common library) is the standard cure."
},
{
d: "ML & Analytics",
q: "You need to extract text from scanned invoices, detect entities like dates and totals, without training anything. Which approach?",
o: [
"Train a custom CNN on Vertex AI.",
"Use pretrained APIs — Document AI (invoice/form parsers), or Vision API OCR for raw text.",
"BigQuery ML linear regression.",
"Manual data entry."
],
a: 1,
e: "The exam pattern: if a pretrained Google API (Vision, Document AI, Speech-to-Text, Translation, Natural Language) covers the task, use it before training anything. Document AI even has specialized invoice processors."
},
{
d: "ML & Analytics",
q: "Which BigQuery ML capability lets you use a large language or vision model on data in your tables (e.g., summarize a text column)?",
o: [
"ML.GENERATE_TEXT with a remote model over Vertex AI (foundation models), via a BigQuery connection.",
"CREATE MODEL type='llm' trained locally in the dataset.",
"Exporting to Sheets and using formulas.",
"It is not possible from SQL."
],
a: 0,
e: "BigQuery ML remote models call Vertex AI endpoints/foundation models from SQL — ML.GENERATE_TEXT, ML.GENERATE_EMBEDDING, etc. — so generative inference runs over table data without leaving BigQuery."
},
{
d: "ML & Analytics",
q: "Your dataset for fraud detection has 0.1% positive labels. Accuracy is 99.9% but the model catches nothing. What should you look at instead, and possibly do?",
o: [
"Accuracy is fine — ship it.",
"Use precision/recall, PR-AUC, F1; address imbalance via class weights, oversampling/undersampling (e.g., SMOTE), or adjusting the decision threshold.",
"Add more negative examples.",
"Reduce the feature count."
],
a: 1,
e: "With extreme class imbalance, accuracy is meaningless (predicting 'no fraud' always scores 99.9%). Precision/recall trade-offs and imbalance-aware training are the standard toolkit — a recurring exam scenario."
},
{
d: "ML & Analytics",
q: "The BI team needs governed, reusable business metrics (one definition of 'revenue') across dashboards, with modeling in code. Which tool is positioned for this?",
o: [
"Looker (LookML semantic model) on top of BigQuery",
"Ad-hoc SQL snippets shared in chat",
"Looker Studio only, with per-report formulas",
"CSV exports to Excel"
],
a: 0,
e: "Looker's LookML defines metrics/dimensions once, version-controlled, and every dashboard reuses the same definitions — the governed semantic-layer story. Looker Studio is the lightweight visualization tool without that central model."
},
{
d: "ML & Analytics",
q: "For repeatable ML on Vertex AI, which component orchestrates preprocessing → training → evaluation → deployment as a versioned, triggerable graph?",
o: [
"Vertex AI Pipelines (Kubeflow Pipelines / TFX based)",
"A README with numbered steps",
"BigQuery scheduled queries",
"Cloud CDN"
],
a: 0,
e: "Vertex AI Pipelines runs containerized ML workflow DAGs with caching, lineage, and scheduling — the MLOps backbone answer. Scheduled queries only cover SQL steps."
},

// ------------------------------------------------- Reliability & Cost
{
d: "Reliability & Cost",
q: "A streaming pipeline feeds an executive dashboard. Define an SLI/SLO pair that actually reflects user experience.",
o: [
"SLI: CPU utilization; SLO: below 80%.",
"SLI: end-to-end freshness (event time to queryable-in-BigQuery latency); SLO: e.g., 95% of data queryable within 5 minutes.",
"SLI: number of workers; SLO: exactly 10.",
"SLI: lines of logs; SLO: fewer than 1M/day."
],
a: 1,
e: "SLIs should measure what users experience — for a dashboard, data freshness/latency and availability — not internal resource metrics. CPU and worker counts are causes, not user-facing symptoms."
},
{
d: "Reliability & Cost",
q: "You want to be alerted before a monthly GCP bill explodes, and hard-stop a dev project's BigQuery spend. What combination works?",
o: [
"Billing budgets with alert thresholds (and Pub/Sub notifications) for awareness + BigQuery custom quotas (bytes billed per day) for hard caps; budgets alone don't stop spending.",
"Budgets alone — they cut off spending automatically.",
"Checking the console weekly.",
"Removing billing accounts from projects in production."
],
a: 0,
e: "A recurring exam trap: budgets NOTIFY, they don't stop usage (unless you wire a Pub/Sub-triggered function to disable billing). Hard limits come from quotas — e.g., BigQuery daily bytes-billed caps per project/user."
},
{
d: "Reliability & Cost",
q: "Dataflow job metrics you should alert on for a streaming pipeline's health include:",
o: [
"Worker hostname lengths.",
"System lag / data watermark age, backlog size, and job/worker error rates — via Cloud Monitoring alerting policies.",
"Number of code comments.",
"BigQuery dataset count."
],
a: 1,
e: "Watermark age and system lag tell you the pipeline is falling behind (the user-facing symptom); backlog growth and error rates catch failing workers. These are the standard Dataflow SLO signals in Cloud Monitoring."
},
{
d: "Reliability & Cost",
q: "An entire region hosting your analytics stack could fail. For BigQuery datasets, what's the recommended DR posture if you need cross-region survivability of critical data?",
o: [
"Nothing — BigQuery is global.",
"BigQuery datasets are regional (or multi-region); for DR, use cross-region dataset replication / scheduled copies (or multi-region locations) and document RTO/RPO for restore.",
"RAID on the underlying disks.",
"Store SQL queries in git — data will regenerate."
],
a: 1,
e: "Datasets live in a location; a regional outage makes a regional dataset unavailable. Cross-region replication (now a native feature), scheduled dataset copies, or multi-region locations are the DR levers, chosen against your RTO/RPO."
},
{
d: "Reliability & Cost",
q: "Which statement about committed use discounts (CUDs) and sustained use discounts is correct for cost planning?",
o: [
"They apply to BigQuery on-demand queries.",
"CUDs give discounts for committing to 1/3-year resource use (e.g., Compute/Dataflow/Dataproc VMs, Spanner, Bigtable nodes); sustained-use discounts apply automatically to eligible Compute Engine usage within a month.",
"Both require preemptible VMs.",
"Discounts apply only to storage."
],
a: 1,
e: "CUDs = planned commitment pricing on infrastructure (and services like Spanner/Bigtable capacity); SUDs = automatic for steady Compute Engine usage. BigQuery's analogous lever is capacity commitments/editions, not CUDs."
},
{
d: "Reliability & Cost",
q: "A nightly batch pipeline failed at 2 AM; the on-call engineer reran it manually. What practice prevents silent data gaps from partially-processed runs like this?",
o: [
"Hope the rerun covered everything.",
"Idempotent, parameterized-by-date tasks plus data-quality/completeness checks (e.g., row-count and freshness assertions) that gate downstream steps and alert on failure.",
"Longer timeouts.",
"Disabling retries so failures are visible."
],
a: 1,
e: "Reruns are safe only when tasks are idempotent per logical date, and gaps are caught only when pipelines assert expectations (row counts, freshness, nulls) before publishing — 'circuit breaker' data-quality gates are the pattern (Airflow checks, Dataform assertions, Dataplex data quality)."
},
{
d: "Reliability & Cost",
q: "Storage cost review: a BigQuery dataset's tables are append-only and many partitions haven't been edited in months. What automatic saving applies, and what should you add?",
o: [
"Nothing is automatic; delete old data.",
"Partitions/tables untouched for 90 consecutive days automatically drop to long-term storage pricing (~50% cheaper); add partition expiration for data past its retention need.",
"Long-term pricing requires exporting to Coldline.",
"Compressing tables manually halves cost."
],
a: 1,
e: "Long-term storage pricing kicks in per table/partition after 90 days without modification — automatically, with no performance difference. Partition expiration then deletes data you no longer need at all. (Also consider physical vs logical storage billing per dataset.)"
},
{
d: "Reliability & Cost",
q: "Your team wants pipeline changes (Dataflow code, Composer DAGs, Terraform) deployed safely. What's the recommended path to production?",
o: [
"Editing DAGs directly in the production bucket.",
"CI/CD: version control, automated tests (unit + pipeline integration on sample data), staged environments (dev → staging → prod), and infrastructure-as-code applied by pipelines like Cloud Build.",
"One shared notebook everyone edits.",
"Quarterly manual releases."
],
a: 1,
e: "The exam expects the modern answer: everything (code, DAGs, infra) in git, tested in CI, promoted through environments by automation — reducing manual production edits that cause outages."
}
,

// ============ Additions from real-exam topic gap analysis ============

// ---------------------------------------------------------------- BigQuery
{
d: "BigQuery",
q: "A legacy pipeline creates one table per day (events_20240101, events_20240102, ...). Queries over long ranges are slow and one hit the per-query table limit. What should you do?",
o: [
"Keep sharding but query fewer days at a time.",
"Convert the date-sharded tables into a single date-partitioned table; until then, query shards with a wildcard table filtered on _TABLE_SUFFIX.",
"Create a view per month.",
"Export everything to Cloud Storage."
],
a: 1,
e: "Partitioning is recommended over sharding: sharded tables carry per-table schema/metadata/permission overhead and per-query table limits, while one partitioned table supports thousands of partitions with pruning. Wildcard tables (`events_*` with _TABLE_SUFFIX filters) are the bridge while you migrate."
},
{
d: "BigQuery",
q: "You model orders with their line items in BigQuery. Analysts always fetch an order together with its items, and join costs are hurting. What's the idiomatic BigQuery design?",
o: [
"Strict third normal form across two tables.",
"Denormalize: store line items as an ARRAY<STRUCT<...>> (nested, repeated field) inside the order row, and UNNEST() when you need to flatten.",
"One giant flat table with items as JSON strings.",
"A separate dataset per order."
],
a: 1,
e: "BigQuery is columnar and join-averse at scale: nested/repeated STRUCT arrays keep the one-to-many relationship inside the parent row — no join, no duplication of parent columns, and UNNEST flattens on demand. Avro/Parquet loads preserve nested schemas (CSV cannot)."
},
{
d: "BigQuery",
q: "Looker Studio dashboards over BigQuery are slow; many users run varied interactive aggregations on the same tables. You don't want to rewrite queries. What's the designed fix?",
o: [
"Increase the Looker Studio refresh interval.",
"Create a BI Engine reservation so dashboard queries are served from in-memory acceleration.",
"Row-level security to reduce data processed.",
"Export the data to Sheets."
],
a: 1,
e: "BI Engine is BigQuery's in-memory analysis acceleration: reserve capacity in the project and eligible dashboard/interactive queries speed up transparently — no query rewrites. A materialized view is the alternative when ONE heavy aggregation dominates; for many varied interactive queries, BI Engine fits better."
},
{
d: "BigQuery",
q: "Compliance regularly needs to find all rows containing a specific user ID across wide log tables — a needle-in-haystack lookup that currently scans terabytes. What BigQuery feature targets this?",
o: [
"LIMIT clauses.",
"A search index on the table and the SEARCH() function for point lookups.",
"More clustering columns (beyond the 4 allowed).",
"Legacy SQL."
],
a: 1,
e: "CREATE SEARCH INDEX builds an inverted index over string columns; SEARCH() then serves point lookups (IDs, emails, tokens in logs) without full scans — the feature built for GDPR-style 'find this identifier anywhere' work."
},
{
d: "BigQuery",
q: "You must choose partition granularity for a table receiving ~2 GB/day, queried mostly by month, retained for 15 years. Daily partitioning would create ~5,475 partitions. What do you consider?",
o: [
"Nothing — partition count is unlimited.",
"Partition limits (up to 10,000 partitions per table) and pruning granularity: monthly partitioning (or daily with expiration) keeps counts safe and matches the query pattern.",
"Hourly partitioning for maximum pruning.",
"Avoid partitioning entirely on principle."
],
a: 1,
e: "Partitioned tables have a partition-count limit (10,000). Choose granularity to match query patterns and retention: monthly partitions (180 over 15 years) suit month-scoped queries; hourly would explode the count for no benefit. Partition expiration bounds retention automatically."
},
{
d: "BigQuery",
q: "Rows stream into a BigQuery table continuously, and you want a standing SQL transformation whose results flow onward (e.g., to another table or Pub/Sub) without managing a pipeline. Which capability is this?",
o: [
"Scheduled queries every minute.",
"BigQuery continuous queries — long-running SQL over arriving data with results written out as they're produced.",
"Table snapshots.",
"The BI Engine."
],
a: 1,
e: "Continuous queries are BigQuery's SQL-only streaming processing: the query runs perpetually over new arrivals and emits results onward. For complex event-time logic (windows, late data), Dataflow is still the tool — but for SQL-shaped streaming transforms this avoids a pipeline entirely."
},

// ---------------------------------------------------------------- Databases
{
d: "Databases",
q: "A PostgreSQL-based application needs to stay PostgreSQL, wants better performance than Cloud SQL, and must serve transactional traffic AND analytical queries on the same database without a separate warehouse. Which service?",
o: [
"Cloud SQL for PostgreSQL with more vCPUs.",
"AlloyDB for PostgreSQL — PostgreSQL-compatible with a columnar engine for analytics on transactional data (HTAP).",
"Spanner with the PostgreSQL interface.",
"Bigtable."
],
a: 1,
e: "AlloyDB is Google's optimized PostgreSQL: disaggregated storage for transactional performance plus an in-memory columnar engine that accelerates analytics over the same data — the 'one database for OLTP + analytics, stays Postgres' answer. Spanner's PG interface targets global write scaling, not HTAP."
},
{
d: "Databases",
q: "In Spanner, Customers and their Orders are always read together, and you want the child rows physically co-located with the parent for cheap joins. Which schema feature?",
o: [
"Foreign keys alone.",
"Interleaved tables: declare Orders INTERLEAVE IN PARENT Customers, with Orders' primary key prefixed by the Customers key.",
"A materialized join view.",
"Storing orders as a JSON column."
],
a: 1,
e: "Interleaving stores child rows physically within the parent's row range, so parent+children reads and joins along that hierarchy avoid cross-split work. It's the Spanner-specific locality tool — use when children are (almost) always accessed via their parent."
},
{
d: "Databases",
q: "You suspect a Bigtable performance problem is caused by hot ranges of row keys, and you need to see the access pattern across the keyspace over time to prove it. Which tool?",
o: [
"Cloud Trace.",
"Key Visualizer — a heatmap of Bigtable access patterns by key range over time.",
"BigQuery INFORMATION_SCHEMA.",
"The gcloud CLI's describe command."
],
a: 1,
e: "Key Visualizer generates hourly/daily heatmaps of reads/writes/latency per key range — hotspots show as bright bands, confirming row-key design issues (e.g., sequential keys). It's the diagnostic that pairs with fixing the key schema."
},
{
d: "Databases",
q: "When is an HDD (instead of SSD) Bigtable cluster the right choice?",
o: [
"Whenever you want to save money on a serving workload.",
"Only for large (≥10 TB), latency-tolerant, scan-heavy archival workloads that are not user-facing; SSD is the default for anything latency-sensitive.",
"For time-series data, always.",
"Never — HDD is deprecated."
],
a: 1,
e: "HDD costs less but delivers much slower random reads. Google's guidance: choose HDD only for big, batch/scan-oriented, latency-insensitive datasets; user-facing or mixed workloads take SSD. Storage type is fixed at instance creation, so this choice matters up front."
},
{
d: "Databases",
q: "Your on-prem analytics stack runs Apache HBase and the team wants to move to a managed GCP service with minimal application change. Which target and why?",
o: [
"Cloud SQL, because HBase is relational.",
"Bigtable — it exposes an HBase-compatible API, so existing HBase client code largely works unchanged.",
"Firestore, because both are NoSQL.",
"BigQuery, because it's the analytics service."
],
a: 1,
e: "Bigtable is the managed wide-column store with an HBase-compatible client API — the designed landing zone for HBase (and Cassandra-style) workloads. The data model (row key, column families) maps directly; the ops burden disappears."
},
{
d: "Databases",
q: "You need to analyze Firestore (Datastore mode) application data in BigQuery nightly. What's the supported low-effort path?",
o: [
"Query Firestore directly from BigQuery with a JDBC driver.",
"Use the managed export (gcloud firestore export) to a Cloud Storage bucket, then load the export into BigQuery.",
"Write a custom crawler over the REST API.",
"Screenshot the console."
],
a: 1,
e: "Firestore's managed export writes a consistent snapshot to GCS in a format BigQuery can load directly (per kind/collection). Schedule export + load and you have nightly analytics without touching the app. Know the vocabulary: entities ≈ rows, kinds ≈ tables."
},
{
d: "Databases",
q: "A team migrating from on-prem Cassandra asks which GCP service most closely matches Cassandra's wide-column, high-write-throughput, key-addressed model. Your answer?",
o: [
"Cloud SQL",
"Bigtable (same wide-column family lineage; design the row key around access patterns just like Cassandra partition keys)",
"Cloud Spanner",
"Memorystore"
],
a: 1,
e: "Cassandra and Bigtable share the wide-column model: massive write throughput, key-range access, denormalized query-first schema design. Cassandra partition-key thinking translates directly to Bigtable row-key design, making it the natural managed replacement."
},

// ------------------------------------------------- Migration & Networking
{
d: "Migration & Networking",
q: "You must move 400 TB from a data center with a saturated 100 Mbps internet link to Cloud Storage within 2 months. What should you use?",
o: [
"gsutil with parallel composite uploads.",
"Transfer Appliance — a shipped physical device you load locally and return to Google for ingestion.",
"Storage Transfer Service over the existing link.",
"Compress the data first and use the link."
],
a: 1,
e: "Do the math first: 400 TB over 100 Mbps is roughly a year of continuous transfer — no software tool fixes physics. Transfer Appliance exists exactly for 'lots of data, weak link, real deadline'. STS/gsutil are answers only when bandwidth × time covers the volume."
},
{
d: "Migration & Networking",
q: "Regulation says data ingested from your on-prem systems into BigQuery must never traverse the public internet. Which combination satisfies this?",
o: [
"HTTPS uploads — encryption is equivalent to privacy.",
"Cloud Interconnect (or Cloud VPN) into your VPC plus Private Google Access so on-prem/VPC hosts reach Google APIs on private IPs.",
"A firewall rule allowing only Google IPs.",
"VPC peering between on-prem and Google."
],
a: 1,
e: "Interconnect/VPN provides the private path into the VPC; Private Google Access (private.googleapis.com / restricted.googleapis.com with VPC-SC) lets that private path reach BigQuery/GCS APIs without public IPs. TLS encrypts but still rides the public internet — it doesn't meet a 'no public internet' mandate."
},
{
d: "Migration & Networking",
q: "You're setting up Datastream CDC from an on-prem MySQL (no public IPs) into BigQuery, and traffic must stay private end to end. Which Datastream connectivity method fits?",
o: [
"IP allowlisting of Datastream public addresses.",
"Private connectivity — peer Datastream into your VPC so it reaches the source over your Interconnect/VPN.",
"Forward-SSH over the internet.",
"Publishing the database to a public IP temporarily."
],
a: 1,
e: "Datastream's private connectivity configuration attaches it to your VPC via peering, so CDC traffic flows over the private Interconnect/VPN path — matching a 'no public internet' constraint. Allowlisting and SSH-forwarding both still traverse public networks."
},
{
d: "Migration & Networking",
q: "Your company runs a large on-prem Kafka estate feeding many consumers, and wants to start landing those streams in GCP with minimal disruption. Reasonable approaches include:",
o: [
"Rewrite all producers to use Pub/Sub immediately.",
"Bridge Kafka to Pub/Sub with the Pub/Sub Kafka connector (or read Kafka directly from Dataflow), or adopt Google Cloud Managed Service for Apache Kafka if keeping the Kafka protocol matters.",
"FTP the Kafka log segments nightly.",
"Kafka data cannot reach GCP."
],
a: 1,
e: "The migration-friendly patterns: connector-based mirroring Kafka→Pub/Sub, Dataflow's KafkaIO reading the existing cluster, or moving the cluster itself to the managed Kafka service. Big-bang producer rewrites are the wrong first move."
},

// ------------------------------------------------- Dataproc & Hadoop
{
d: "Dataproc & Hadoop",
q: "A Hadoop job that was fast on on-prem bare metal is slow on Dataproc; profiling shows it is disk-I/O bound during shuffle/spill (data itself is on GCS). What's the targeted fix?",
o: [
"More vCPUs per worker.",
"Attach local SSDs to the workers (or enlarge persistent disks) so shuffle and spill hit fast local storage.",
"Move input data into HDFS.",
"Switch the cluster to HDD boot disks."
],
a: 1,
e: "Shuffle/spill happens on worker-local disks even when the dataset lives on GCS. Local SSDs give the IOPS/throughput bare metal had; persistent-disk throughput also scales with disk size. More CPU doesn't help an I/O-bound stage."
},
{
d: "Dataproc & Hadoop",
q: "Autoscaling removes Dataproc workers mid-job and running Spark tasks lose shuffle data, causing recomputation. Which two features mitigate this?",
o: [
"Bigger master node.",
"Graceful decommissioning (let YARN drain work before removing nodes) and Enhanced Flexibility Mode (keep shuffle data off preemptible secondary workers).",
"Disabling autoscaling forever.",
"Switching to HDDs."
],
a: 1,
e: "Graceful decommission timeouts let nodes finish/hand off work before removal; EFM writes shuffle data to primary workers (or HCFS) so losing spot secondaries costs little. Together they make autoscaling + preemptibles safe for real jobs."
},

// ------------------------------------------------- Dataflow & Beam
{
d: "Dataflow & Beam",
q: "Your streaming pipeline must divert malformed records for later inspection instead of crashing or silently dropping them. What's the idiomatic Beam construct?",
o: [
"try/except that logs and swallows errors.",
"A ParDo with multiple tagged outputs (side outputs): main output for valid records, a dead-letter output written to BigQuery/GCS for the bad ones.",
"A side input containing the bad records.",
"Two separate pipelines reading the same source."
],
a: 1,
e: "Tagged (side) outputs let one ParDo route each element: parse successes to the main PCollection, failures — with error context — to a dead-letter sink. Don't confuse with side INPUTS, which broadcast small lookup data into a ParDo."
},
{
d: "Dataflow & Beam",
q: "You want an alert that fires when your Pub/Sub → Dataflow → GCS pipeline silently stops processing. Which signal combination is right?",
o: [
"Alert on Dataflow worker count dropping.",
"Alert on rising subscription/num_undelivered_messages (and oldest_unacked_message_age) at the source plus a falling output write rate at the sink.",
"Alert on CPU utilization above 80%.",
"Alert when the job status is not 'Running'."
],
a: 1,
e: "A stuck pipeline often still shows 'Running' with healthy CPU. The user-visible truth is backlog growing at the source (undelivered messages, unacked age) while sink output flat-lines — alert on those. Watermark/system lag are the equivalent Dataflow-side metrics."
},

// ------------------------------------------------- Orchestration & Integration
{
d: "Orchestration & Integration",
q: "Upstream files land in a GCS bucket at unpredictable times, and each arrival must kick off a Composer DAG (Dataproc transform → BigQuery load). Scheduling hourly wastes runs and adds latency. What's the recommended trigger design?",
o: [
"Schedule the DAG every 5 minutes.",
"A Cloud Storage object-finalize event triggers a Cloud Function (or Eventarc) that calls the Airflow REST API to trigger the parameterized DAG.",
"A while-loop sensor task holding a worker slot forever.",
"Ask the upstream team to also click 'Trigger DAG'."
],
a: 1,
e: "Event-driven beats polling when arrival times are unknown: the bucket's finalize event fires a function that triggers the DAG (passing the object name as a parameter). One parameterized DAG serves all files; no wasted scheduled runs, minimal latency."
},
{
d: "Orchestration & Integration",
q: "Analysts must clean inconsistent CSVs (mixed types in columns, unstandardized phone/address formats) with an interactive, visual tool before the data reaches BigQuery. Which GCP tool is built for this?",
o: [
"The BigQuery console's preview tab.",
"Cloud Data Fusion's Wrangler — interactive data preparation (profiling, type fixes, format standardization) that then runs as a pipeline at scale.",
"Vim on the CSV files.",
"Cloud Shell's csvtool."
],
a: 1,
e: "Wrangler (in Data Fusion) is the visual data-prep experience aimed at analysts: explore a sample, build cleansing directives interactively, then execute them as a managed pipeline over the full data. It's the modern exam answer where 'Dataprep' appeared historically."
},
{
d: "Orchestration & Integration",
q: "CSV files have columns whose types are inconsistent (some rows STRING, some INT64), so typed loads fail. Which robust SQL-first pattern gets this data into a typed production table?",
o: [
"Keep retrying the load until it works.",
"Load into a staging table with all-STRING columns, transform with SQL (SAFE_CAST, REGEXP_REPLACE, dedupe), then INSERT/MERGE into the typed final table.",
"Edit the CSVs by hand.",
"Use JSON instead of CSV — types become irrelevant."
],
a: 1,
e: "The ELT staging pattern: land raw data permissively (STRINGs never fail to parse), then apply typed, validated transformation in SQL where errors are inspectable (SAFE_CAST yields NULL instead of failing), and only clean rows reach production. This — or a Data Fusion/Dataflow transform — is the exam's cleansing answer."
},

// ---------------------------------------------------------------- ML
{
d: "ML & Analytics",
q: "A linear model predicting taxi fares can't capture that the pickup-neighborhood × hour-of-day interaction matters. Without switching to a deep model, which feature engineering technique lets a linear model learn such non-linear interactions?",
o: [
"Normalize the inputs.",
"A feature cross — a synthetic feature crossing neighborhood and hour (often after bucketizing), giving the linear model a weight per combination.",
"Remove one of the two features.",
"Increase the learning rate."
],
a: 1,
e: "Feature crosses (e.g., lat×long grid cells, neighborhood×hour) create combinatorial features so linear models memorize interaction effects. It's the classic pre-deep-learning answer — and the 'wide' half of wide-and-deep models."
},
{
d: "ML & Analytics",
q: "A recommender should both memorize specific historical combinations (users who bought A buy B) and generalize to unseen combinations via learned representations. Which architecture is designed for exactly this trade-off?",
o: [
"A decision stump.",
"Wide & Deep: a wide linear component (feature crosses, memorization) trained jointly with a deep component (embeddings, generalization).",
"k-means clustering.",
"A single linear regression."
],
a: 1,
e: "Wide & Deep pairs a linear model over crossed sparse features (memorization) with a DNN over embeddings (generalization) — the canonical recommender architecture this exam has long referenced."
},
{
d: "ML & Analytics",
q: "You have a categorical feature with 2 million distinct values (user ID). One-hot encoding is infeasible. What's the standard representation?",
o: [
"Drop the feature.",
"An embedding — a learned dense low-dimensional vector per category that places similar categories near each other.",
"Alphabetical integer encoding fed directly to the model.",
"A separate model per user."
],
a: 1,
e: "Embeddings compress huge sparse categorical spaces into small dense vectors learned with the task, capturing similarity structure. Raw integer codes impose a false ordering; one-hot at this cardinality explodes parameters."
},
{
d: "ML & Analytics",
q: "During training, the loss doesn't decrease — it oscillates wildly and sometimes increases. What's the most likely knob to turn first?",
o: [
"Increase the batch size to 1.",
"Lower the learning rate (or apply decay) — oscillating/diverging loss is the classic symptom of steps that are too large.",
"Add more layers.",
"Train for more epochs unchanged."
],
a: 1,
e: "Too-high learning rates overshoot minima, producing oscillation or divergence; lowering the rate (or using warmup/decay, or an adaptive optimizer) is the first fix. Too-low rates show the opposite symptom: painfully slow but steady descent."
},
{
d: "ML & Analytics",
q: "You want regularization that also performs feature selection by driving irrelevant feature weights to exactly zero. Which do you choose?",
o: [
"L2 (ridge).",
"L1 (lasso) — its penalty zeroes out weights, yielding sparse models; L2 only shrinks weights smoothly toward zero.",
"Dropout.",
"Batch normalization."
],
a: 1,
e: "L1's absolute-value penalty produces exact zeros → built-in feature selection and sparse models. L2 shrinks all weights but rarely to zero — the default anti-overfitting choice when sparsity isn't a goal. (Dropout regularizes deep nets, not feature selection.)"
},
{
d: "ML & Analytics",
q: "Your team hand-tunes learning rate, layer sizes, and regularization by trial and error on Vertex AI. What's the managed, smarter alternative?",
o: [
"Fix all hyperparameters at library defaults.",
"Vertex AI hyperparameter tuning (Vizier): define ranges and a metric, and Bayesian optimization searches the space across parallel trials.",
"Only ever use grid search on two values each.",
"Change one parameter per week."
],
a: 1,
e: "Vertex AI's tuning service (powered by Vizier) runs parallel trials and uses Bayesian optimization to converge on good hyperparameters far more efficiently than manual or exhaustive grid search."
},

// ------------------------------------------------- Security & Governance
{
d: "Security & Governance",
q: "Onboarding/offboarding keeps breaking access: engineers get roles granted to their personal accounts, and departures leave stale grants. What's the Google-recommended structure?",
o: [
"Grant roles to individual users but audit quarterly.",
"Grant IAM roles to Google Groups per function (e.g., data-analysts@), and manage membership in the group — identity changes never touch IAM policy.",
"Share one service account's key among the team.",
"Give everyone Viewer at the org level plus exceptions."
],
a: 1,
e: "Groups are the recommended grant target: IAM policy stays stable while membership handles joiners/leavers, and access reviews happen in one place. Shared keys and per-user grants are the anti-patterns this question type punishes."
}
,

// ============ Additions from the full-bank sweep (every ~5th question) ============

{
d: "BigQuery",
q: "An app performs streaming inserts into BigQuery and immediately runs an aggregation, but the results sometimes miss rows that were just written. The aggregates must be complete when they run. What's the recommended redesign?",
o: [
"Retry the aggregation until the numbers stop changing.",
"Accumulate messages and use periodic batch load jobs (each load is atomic), running the aggregation after each completed load.",
"Route the inserts through Cloud SQL first.",
"Wait exactly twice the average streaming latency before querying."
],
a: 1,
e: "Streamed rows become visible within seconds but there's no guarantee an immediate query sees every in-flight row. Batch load jobs are atomic — after the job completes, queries see all of the data — so accumulate-and-load (e.g., every couple of minutes) is the design when aggregate completeness matters more than second-level latency."
},
{
d: "BigQuery",
q: "Analysts consuming a dataset via ODBC report errors against an old view. You discover the view is written in legacy SQL. What do you do?",
o: [
"Tell them ODBC isn't supported by BigQuery.",
"Recreate the view in GoogleSQL (standard SQL) — drivers and modern tooling require it — and authenticate the connection with a service account.",
"Enable a legacy-SQL flag on the ODBC driver.",
"Export the view to CSV nightly."
],
a: 1,
e: "Legacy SQL views are a compatibility dead end: standard-SQL consumers (ODBC/JDBC, most modern tooling) can't use them. Migrate the view to GoogleSQL; connections from BI tools authenticate via a service account with dataset-scoped read access."
},
{
d: "BigQuery",
q: "A query produces a very large result set that analysts need to keep querying for further analysis, with low maintenance and cost. What's the built-in mechanism?",
o: [
"Copy-paste results into a new project.",
"Run the query with a destination table (allowing large results) so the output is materialized as a normal table for follow-on SQL.",
"Export to Sheets.",
"Increase the interactive result-size limit in settings."
],
a: 1,
e: "Query jobs can write results straight into a destination table — bypassing interactive result-size limits and turning the result into a first-class table for further queries. No export loops, no extra services."
},
{
d: "BigQuery",
q: "Your company stores analytical data in both Cloud Storage and AWS S3 (all US). Analysts must query all of it from BigQuery with up-to-date results, without being granted direct access to the buckets. What's the design?",
o: [
"Nightly copy jobs from S3 into BigQuery.",
"BigQuery Omni for the S3 side, with BigLake tables over both the GCS and S3 data — users query governed tables, never the storage.",
"Public bucket URLs referenced in views.",
"A federated Cloud SQL proxy in AWS."
],
a: 1,
e: "BigQuery Omni runs BigQuery's engine next to the data in AWS/Azure, and BigLake tables add governed, table-level access (users need no storage permissions) with fine-grained security. That combination answers 'query in place across clouds, no direct bucket access'."
},
{
d: "BigQuery",
q: "You expose user-level data as aggregates to other projects via an authorized view. Who pays for the queries the consuming teams run against the view?",
o: [
"Your project — the view lives there.",
"The consuming project that runs the query — compute/bytes-scanned bill to the query's billing project, which is exactly why authorized views suit 'costs assigned to each analyzing team'.",
"Google absorbs cross-project query costs.",
"Costs are split 50/50 automatically."
],
a: 1,
e: "Query cost follows the project that issues the job, not the project that owns the data. An authorized view therefore shares curated results while each consumer's analysis lands on their own bill — a detail scenario questions test explicitly."
},
{
d: "Orchestration & Integration",
q: "A data analyst needs a fully managed, no-code way to load 200 CSV files (~15 MB each) that land daily in a GCS bucket into BigQuery, with a SQL transformation afterward. What do you recommend?",
o: [
"A custom Cloud Run service triggered by Cloud Scheduler.",
"BigQuery Data Transfer Service configured with the bucket as a source on a daily schedule, plus a scheduled query for the SQL transform.",
"A Spark job on Dataproc.",
"Manual bq load commands each morning."
],
a: 1,
e: "BQ DTS isn't only for SaaS sources — it also runs scheduled Cloud Storage → BigQuery loads with zero code, and a scheduled query covers the transform. For an analyst-owned pipeline, that no-code pairing beats writing services or Spark; the key fact to remember is that DTS supports Cloud Storage as a scheduled source."
},
{
d: "Pub/Sub & Streaming",
q: "A push subscription feeds an event-driven consumer that occasionally goes down or gets overloaded. Requirements: tolerate downtime, retry failed messages gradually without hammering the recovering app, and park messages after 10 failed attempts. How do you configure it?",
o: [
"Raise the ack deadline to the maximum.",
"Set the subscription retry policy to exponential backoff and attach a dead-letter topic (a different topic) with max delivery attempts = 10.",
"Use immediate redelivery with a dead-letter to the same source topic.",
"Switch to daily batch delivery."
],
a: 1,
e: "Exponential backoff spaces out redeliveries so a recovering consumer isn't stampeded; the dead-letter topic (never the source topic — that would loop) captures poison messages after the attempt limit. Message retention covers the downtime itself."
},
{
d: "Orchestration & Integration",
q: "A SQL aggregation must run every 2 hours, append to a table, retry on failure, and email the team after repeated failures. The team already runs Cloud Composer. Which implementation fits?",
o: [
"A BigQuery scheduled query — it supports retries and escalation emails after N failures.",
"A Composer DAG using BigQueryInsertJobOperator with retries set and email_on_failure enabled.",
"A cron job on a GCE VM calling bq query.",
"A Cloud Function with no retry configuration."
],
a: 1,
e: "Airflow operators carry exactly the knobs the requirements name: retries/retry_delay per task and email_on_failure notifications. Scheduled queries can notify on failure but don't give the same retry-then-escalate semantics; since Composer is already running, the operator is the fit."
},
{
d: "Orchestration & Integration",
q: "A Cloud Workflows workflow calls an API returning a small JSON payload and must apply business logic too complex for the Workflows standard library, then continue to a BigQuery load step. Optimizing for simplicity and speed, what do you add?",
o: [
"A Cloud Composer environment for the logic step.",
"A Cloud Function (Python) invoked from the workflow to apply the logic and return the result.",
"A Dataproc cluster running PySpark on the 1 KB payload.",
"Rewrite everything as one giant BigQuery UDF."
],
a: 1,
e: "For a small payload needing real code inside a Workflows sequence, invoking a Cloud Function is the lightweight, serverless answer. Spinning up Composer or a Spark cluster for 1 KB of JSON is the over-engineering the wrong options represent."
},
{
d: "Security & Governance",
q: "Two datasets must be joined on the email column, but analysts may never see real emails. Which de-identification approach keeps the join working?",
o: [
"DLP masking (replace characters with *).",
"DLP deterministic tokenization / format-preserving encryption (FPE-FFX) — the same email always maps to the same token, so equality joins still match.",
"Delete the email column from both datasets.",
"Hash one dataset and mask the other."
],
a: 1,
e: "Masking destroys linkage; deterministic FPE tokenization replaces each value consistently in both datasets, so joins on the tokenized field behave exactly like joins on the original — and re-identification requires the key. This masking-vs-tokenization distinction is a recurring exam trap."
},
{
d: "Security & Governance",
q: "You must share part of a CMEK-encrypted BigQuery dataset with a partner org that has no access to your KMS key. What's the supported pattern?",
o: [
"Send them an exported copy of the key.",
"Copy the shareable tables into a dataset without CMEK and publish that via Analytics Hub (or an authorized view over the copy).",
"Grant them roles/cloudkms.cryptoKeyDecrypter on your key.",
"CMEK datasets simply cannot be shared with anyone."
],
a: 1,
e: "Consumers of CMEK data need the key — which you don't hand to outside orgs. The pattern is a curated copy in a non-CMEK (Google-default-encrypted) dataset, shared through Analytics Hub. Granting external orgs your key or exporting it defeats CMEK's purpose."
},
{
d: "Security & Governance",
q: "In a Dataplex-based data mesh, data engineering teams need full control of their domain's lake while analysts should only consume curated data products. Which grants implement this cleanly?",
o: [
"BigQuery dataOwner on all datasets for everyone, filtered by etiquette.",
"dataplex.dataOwner for the engineering teams on their lake, and dataplex.dataReader for analysts on the curated zone — Dataplex propagates access to the underlying assets.",
"storage.admin for engineers and bigquery.user for analysts at the org level.",
"Per-table IAM maintained by hand."
],
a: 1,
e: "Dataplex's own roles applied at lake/zone level are the point of using Dataplex for a mesh: producers own their domain, consumers read the curated zone, and the grants propagate to the BigQuery datasets and GCS buckets underneath instead of being managed asset by asset."
},
{
d: "Dataflow & Beam",
q: "A batch Dataflow job starts, processes a few elements, then fails; the monitoring UI shows repeated errors attributed to one DoFn. What's the most likely cause?",
o: [
"A zonal outage.",
"Unhandled exceptions in that DoFn's code — Dataflow retries the bundle (4 times in batch) and then fails the job; inspect worker logs and catch-and-dead-letter the offending records.",
"Insufficient IAM permissions on the output bucket.",
"The watermark advanced too quickly."
],
a: 1,
e: "Errors pinned to a specific transform with retry-then-fail behavior are the signature of worker-code exceptions on certain records. Permission or infrastructure problems fail differently (at startup / at the sink). The fix: defensive parsing with a dead-letter side output."
},
{
d: "Migration & Networking",
q: "An Oracle database runs on a VM inside your VPC. You must continuously replicate 50 tables to BigQuery while minimizing infrastructure you manage. Which approach?",
o: [
"Deploy Kafka + Debezium + a BigQuery sink connector in the VPC.",
"Datastream with a private connectivity configuration into the VPC and BigQuery as the destination.",
"Cron-driven full exports every 15 minutes.",
"A custom JDBC poller on GKE."
],
a: 1,
e: "Datastream is the serverless CDC service: log-based capture from Oracle, direct BigQuery destination, and private connectivity keeps traffic inside the VPC. The Kafka/Debezium stack achieves the same result but is exactly the self-managed infrastructure the requirement rules out."
},
{
d: "Reliability & Cost",
q: "You need an instant notification whenever an insert job appends data to one specific BigQuery table — and no noise from other tables. What's the design?",
o: [
"Poll the logs API every minute and filter client-side.",
"A Cloud Logging sink with an advanced filter scoped to that table's insert-job audit events, exporting to Pub/Sub, with your notifier subscribed to the topic.",
"A log sink exporting everything to BigQuery.",
"A Cloud Monitoring uptime check on the table."
],
a: 1,
e: "The advanced log filter narrows to exactly the audit-log entries you care about; the Pub/Sub sink turns each match into a push event your tooling consumes immediately. Sinking to BigQuery stores logs (good for audits) but notifies no one; polling adds latency and cost."
},
{
d: "Reliability & Cost",
q: "You run MariaDB on Compute Engine VMs and need database metrics (connections, replication status) plus dashboards and alerts in Cloud Monitoring with minimal development. What do you do?",
o: [
"Nothing — GCE VMs export database metrics automatically.",
"Install the Ops Agent on the VMs and enable its MySQL/MariaDB integration; add custom metrics via OpenTelemetry only for anything the integration doesn't cover.",
"Build a custom exporter fleet from scratch first.",
"Migrate to Cloud SQL tonight."
],
a: 1,
e: "Self-managed databases need the Ops Agent; its MySQL-family integration ships the standard database metrics into Cloud Monitoring where dashboards/alerting work natively. Writing custom collection first is the high-effort distractor — reserve custom metrics for true gaps."
},
{
d: "ML & Analytics",
q: "Your data processing and cleaning for a sales-conversion model is complete. Following the model development lifecycle, what comes next?",
o: [
"Run predictions on fresh customer data.",
"Split the data — decide what's used for training vs validation/testing — before any training or evaluation.",
"Deploy the model to an endpoint.",
"Monitor production performance."
],
a: 1,
e: "Lifecycle order is tested directly: prepare data → split train/validation/test → train → evaluate on held-out data → tune → then predict/deploy/monitor. Evaluating or predicting before a principled split invalidates your metrics (leakage)."
},
{
d: "ML & Analytics",
q: "Executives say a Looker Studio dashboard doesn't show orders from the past hour, though the BigQuery table has them. Queries themselves are fast. What's the first thing to adjust?",
o: [
"Add more slots to the project.",
"The report's data freshness (cache) setting — Looker Studio serves cached results; shorten the refresh interval or refresh manually.",
"Rebuild the dashboard from scratch.",
"Partition the underlying table."
],
a: 1,
e: "Stale-but-fast is the cache signature: Looker Studio refreshes data on an interval (default 12 hours for BigQuery). Shortening data freshness fixes staleness. (Slow dashboards are the different problem — that's BI Engine / materialized-view territory.)"
}
];
