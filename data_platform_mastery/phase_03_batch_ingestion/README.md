# Phase 03 — Batch Ingestion Framework ② (`v0.3.0`)

> **Mission:** one parameter-driven ingestion engine, three connector types
> (files, JDBC, REST API), all landing in the RAW zone with manifests, contract
> validation, quarantine, and audit rows. Plus the NovaMart data generators that
> feed the rest of the course.

## 1. Concepts

Read notes **§12 (ingestion patterns)** and **§4 (source categories)** first —
this phase implements the left half of both tables. Also GCP **M02** (lake zoning)
and **M03** (loading BigQuery, external tables).

**RAW zone rules (§5, §22 Bronze):**
- **As-is.** No cleaning, no typing, no renames. RAW is your replay/audit insurance.
  "Making bronze a little clean" is the classic mistake — you lose the original.
- **Partition by *ingestion* date, not event date** — late data makes event-date
  partitioning of raw unpredictable (§1's practical-knowledge example, §11).
- Append-only, with **batch manifests**: each landed batch writes
  `_MANIFEST.json` (rows, bytes, source watermark, contract version, checksum).
  Downstream promotion reads *the manifest*, not "whatever files are there" —
  that's how you make append-only RAW + idempotent ODP coexist.

**Layout convention (memorize — you'll say it in interviews):**

```
gs://<raw>/source=<source>/dataset=<name>/ingest_date=YYYY-MM-DD/batch_id=<uuid>/
    part-000.csv            # or .jsonl / .parquet — source-native
    _MANIFEST.json
```

**The idempotency contract of this phase:** re-running ingestion for the same
`execution_date` creates a *new* batch under the same `ingest_date=` prefix and
marks it latest in the manifest index; promotion (Phase 5) always takes the latest
**complete** batch per execution_date. Result: retries never corrupt, and RAW keeps
full history. Compare this with the naive "overwrite raw on retry" and be able to
argue both (§7).

**Watermarks:** incremental JDBC pulls `WHERE updated_at > :last_watermark`. The
watermark lives in the **metadata DB** (never in code, never in a local file). And
say it with me (§12): **incremental extraction misses hard deletes** — we'll prove
it in Phase 8 recon and fix the discussion with CDC in Phase 5.

## 2. Build

### 2.1 NovaMart generators — `generators/`

1. `gen_orders.py` — writes a daily CSV of ~100k order lines to a *landing* bucket
   (simulate a partner drop): 1–3% deliberately malformed rows (bad dates, negative
   qty, null PKs — the DQ fodder), plus ~0.5% duplicate order_line_ids (dedup fodder),
   and a `--late-fraction` flag that stamps some rows with yesterday's `order_ts`
   (late-data fodder for Phase 5).
2. `docker/docker-compose.sources.yml` — a local **MySQL 8** container seeded with
   `customers` (50k) and `products` (5k) tables, plus `gen_oltp_churn.py` that
   updates ~2% of customers/day (tier changes, address moves — SCD2 fodder) and
   **hard-deletes** a handful (the recon lesson).
3. `fx_rates` needs no generator — you'll pull https://api.frankfurter.dev (free, keyless).

Add a `landing` bucket to the `gcs_lake` module (partner drops arrive here, outside RAW).

### 2.2 The connector interface — `src/pipeforge/ingestion/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class BatchResult:
    batch_id: str
    rows_read: int
    rows_landed: int
    rows_quarantined: int
    bytes_written: int
    new_watermark: str | None = None

class Connector(ABC):
    """Every connector is constructed from a Dataset row — parameters, not code."""
    def __init__(self, dataset, contract, execution_date: str):
        self.ds, self.contract, self.execution_date = dataset, contract, execution_date

    @abstractmethod
    def extract(self) -> "Iterator[dict]": ...

    def land(self) -> BatchResult:
        """Template method: extract → validate against contract → write RAW + quarantine
        + _MANIFEST.json. Subclasses only implement extract()."""
```

`land()` is where the framework earns its name: contract validation
(`jsonschema.validate` per record, invalid → quarantine bucket with the violation
attached), Hive-style pathing, manifest writing, and metrics into the
`run_context` from Phase 2. Write it once; every connector inherits it.

### 2.3 Three connectors

`file.py` (GCS landing → RAW):

```python
class FileConnector(Connector):
    """Moves partner file drops from landing/ to RAW with validation.
    Config used: dataset.name, contract, expected filename pattern in params."""
    def extract(self):
        client = storage.Client()
        prefix = f"drops/{self.ds.name}/{self.execution_date}/"
        blobs = list(client.list_blobs(settings.landing_bucket, prefix=prefix))
        if not blobs:
            raise SourceDataMissing(prefix)     # fail LOUD — silent skip = silent staleness (§1)
        for blob in blobs:
            yield from csv.DictReader(io.TextIOWrapper(blob.open("rb")))
```

`jdbc.py` (MySQL incremental) — key logic:

```python
def extract(self):
    wm = repo.get_watermark(self.ds.dataset_id)            # from ingestion_state table
    q = text(f"SELECT * FROM {self.ds.name} WHERE {self.ds.watermark_column} > :wm "
             f"AND {self.ds.watermark_column} <= :ceiling ORDER BY {self.ds.watermark_column}")
    # ceiling = execution_date 23:59:59 — a CLOSED window makes the run reproducible/backfillable.
    # An open-ended query ("> wm") re-run tomorrow returns different rows = not idempotent.
    ...
    self._new_watermark = str(max_seen)
```

After a successful land, `repo.advance_watermark(...)` — inside the same audit
transaction. (Interview nugget: advance the watermark only after durable landing,
or a crash between the two loses data.)

`rest_api.py` (fx_rates) — pagination loop, `tenacity` retries with exponential
backoff + jitter, explicit timeout, and a politeness rate limit. Small data, but
the *shape* (retry/backoff/pagination/closed date window) is what interviews ask about (§4 APIs).

Add an `ingestion_state` table via a new Alembic migration (dataset_id PK,
watermark_value, updated_at) — your first schema evolution, done properly.

### 2.4 CLI + wiring

```bash
pipeforge ingest --dataset orders     --execution-date 2026-07-15   # file
pipeforge ingest --dataset customers  --execution-date 2026-07-15   # jdbc incremental
pipeforge ingest --dataset fx_rates   --execution-date 2026-07-15   # api
```

The `ingest` command: look up dataset → pick connector class from
`load_pattern` (a registry dict, not if/else chains) → run inside `run_context`.

### 2.5 See it in BigQuery (teaser for M03)

Create dataset `raw_ext` in Terraform and one **external table** over
`gs://…/source=partner_files/dataset=orders/*` with hive partitioning. Query your
raw CSVs with SQL — and note the bytes scanned (external tables don't prune well;
that's a *feature* here: it motivates ODP columnar in Phase 5).

### 2.6 Ship it

Unit tests: contract-validation split (valid→raw, invalid→quarantine with reason),
manifest correctness, watermark closed-window logic (freeze time, run twice, second
run lands zero rows). Tag `v0.3.0`.

## 3. Prove it

- [ ] Three datasets land for today's date; `gsutil ls` shows the exact layout convention
- [ ] `_MANIFEST.json` rows == audit `pipeline_run.rows_written`
- [ ] Malformed rows are in quarantine **with violation reasons**, and
      `rows_read = rows_landed + rows_quarantined` (conservation law — check it in SQL)
- [ ] Re-run same execution_date: new batch_id, watermark unmoved for jdbc (closed window), no duplication downstream risk
- [ ] `SELECT COUNT(*)` on the external table matches the manifest

## 4. Break it

1. Delete the day's partner drop and run ingestion → confirm it fails loudly with
   `SourceDataMissing`, audit row `failed`, not a silent success. (Silent failure is THE
   DE failure mode — §1.)
2. Kill the JDBC run mid-extract (Ctrl-C). Confirm: watermark did NOT advance,
   re-run lands a complete batch, no gap. Write `docs/incidents/003-midrun-crash.md`.

## 5. Interview corner

- 60-second answer to *"How do you ingest files reliably?"*: landing→validate against
  contract→quarantine bad→manifest→RAW ingestion-date partitions→audit row→loud
  failure on missing drop. That's a complete, senior answer.
- *"Full vs incremental vs CDC?"* — you now have the 3-question decision tree (§12)
  **plus** a personal example: "customers is incremental on `updated_at`; I know it
  misses hard deletes — my recon framework catches that drift, and CDC is the fix."
- Say "closed watermark window" out loud in your answer. Interviewers notice.

## 6. Stretch goals

- Content checksum (SHA256) in manifests; verify on promotion (bit-rot paranoia).
- A `--dry-run` flag printing the plan (rows sampled, target paths) — ops love this.
- Handle `.csv.gz` transparently; add a JSONL file source.
