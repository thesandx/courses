# Phase 02 — The Metadata Core: Registration Framework ①⑧ (`v0.2.0`)

> **Mission:** build the brain. A Cloud SQL Postgres registry holds every source,
> dataset, schema contract, and (soon) DQ rule and run record. A `pipeforge`
> CLI registers the four NovaMart sources. From this phase on, **no component is
> allowed to know anything that isn't in this database.**

## 1. Concepts

- Notes **§16 (Data contracts & schema validation)** — you implement versioned
  contracts with compatibility checking today.
- Notes **Q7 (ETL framework for 100 sources)** — reread the breakdown; the registry
  you're building is its core answer.
- GCP course **M05 (choosing a database)** — *why Postgres here?* The registry is a
  low-volume, relational, transactional workload with joins and constraints:
  classic Cloud SQL. Not BigQuery (OLAP, no OLTP semantics), not Firestore (you
  want FK integrity + SQL reporting on audit data). Being able to defend this
  choice **is** the M05 exam skill.
- The **audit model ⑧** starts here: `pipeline_run` is an append-only table every
  future component writes to. Operational metadata capture is what turns "a bunch
  of jobs" into "a platform" — it feeds the recon framework (P08), observability
  (P10), and the ops console (P11).

**Registration = a data contract ceremony.** Onboarding isn't "give me creds";
it's: declare schema, keys, business date, PII columns, freshness SLA, retention.
Forcing this at registration time is what makes every downstream framework
(quality, tokenization, archival, SLA monitoring) automatic.

## 2. Build

### 2.1 Terraform: Cloud SQL (smallest possible)

`terraform/modules/cloudsql_metadata/main.tf`:

```hcl
variable "project_id" { type = string }
variable "region"     { type = string }
variable "env"        { type = string }

resource "google_sql_database_instance" "metadata" {
  name             = "pf-${var.env}-metadata"
  database_version = "POSTGRES_15"
  region           = var.region
  settings {
    tier    = "db-f1-micro"          # ~$9/mo — and you'll stop it when idle
    edition = "ENTERPRISE"
    ip_configuration {
      ipv4_enabled = true            # dev convenience; Phase 12 moves this private
      authorized_networks {
        name  = "dev-machine"
        value = var.dev_ip_cidr      # your IP/32 — never 0.0.0.0/0
      }
    }
    backup_configuration { enabled = true }
  }
  deletion_protection = false        # this is a course; prod would be true
}

variable "dev_ip_cidr" { type = string }

resource "google_sql_database" "pipeforge" {
  name     = "pipeforge"
  instance = google_sql_database_instance.metadata.name
}

resource "google_sql_user" "app" {
  name     = "pipeforge_app"
  instance = google_sql_database_instance.metadata.name
  password = var.db_password         # dev only; Phase 12 swaps to Secret Manager + IAM auth
}

variable "db_password" { type = string, sensitive = true }

output "connection_ip" { value = google_sql_database_instance.metadata.public_ip_address }
output "instance_name" { value = google_sql_database_instance.metadata.name }
```

Wire it into `envs/dev/main.tf`, apply, then:

```bash
echo "PF_METADATA_DB_URL=postgresql+psycopg://pipeforge_app:<pw>@<ip>/pipeforge" >> .env
# Idle cost control (memorize these two):
gcloud sql instances patch pf-dev-metadata --activation-policy=NEVER    # stop
gcloud sql instances patch pf-dev-metadata --activation-policy=ALWAYS   # start
```

### 2.2 SQLAlchemy models — `src/pipeforge/metadata/models.py`

```python
import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class SourceKind(str, enum.Enum):
    db = "db"; file = "file"; api = "api"; stream = "stream"


class LoadPattern(str, enum.Enum):
    full = "full"; incremental = "incremental"; cdc = "cdc"; stream = "stream"; api = "api"


class SourceSystem(Base):
    __tablename__ = "source_system"
    source_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[SourceKind]
    connection_ref: Mapped[str] = mapped_column(
        String(200), doc="Secret Manager key or docker alias — NEVER credentials")
    owner_email: Mapped[str] = mapped_column(String(200))
    tenant: Mapped[str] = mapped_column(String(50), default="novamart")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Dataset(Base):
    __tablename__ = "dataset"
    __table_args__ = (UniqueConstraint("source_id", "name"),)
    dataset_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_system.source_id"))
    name: Mapped[str] = mapped_column(String(100))
    load_pattern: Mapped[LoadPattern]
    schedule_cron: Mapped[str | None] = mapped_column(String(50))
    watermark_column: Mapped[str | None] = mapped_column(String(100))
    primary_keys: Mapped[list] = mapped_column(JSON, default=list)
    business_date_column: Mapped[str | None] = mapped_column(String(100))
    scd_type: Mapped[int] = mapped_column(default=1)
    pii_columns: Mapped[list] = mapped_column(JSON, default=list)
    sla_freshness_minutes: Mapped[int] = mapped_column(default=1440)
    retention_days: Mapped[int] = mapped_column(default=365)
    active: Mapped[bool] = mapped_column(default=True)


class SchemaContract(Base):
    __tablename__ = "schema_contract"
    __table_args__ = (UniqueConstraint("dataset_id", "version"),)
    contract_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.dataset_id"))
    version: Mapped[int]
    format: Mapped[str] = mapped_column(String(20), default="jsonschema")
    definition: Mapped[dict] = mapped_column(JSON)
    compatibility: Mapped[str] = mapped_column(String(20), default="backward")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PipelineRun(Base):
    """⑧ Audit model — APPEND ONLY. No UPDATEs except closing the row you opened."""
    __tablename__ = "pipeline_run"
    run_id: Mapped[str] = mapped_column(primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.dataset_id"))
    execution_date: Mapped[str] = mapped_column(String(10))     # YYYY-MM-DD, the idempotency key
    layer: Mapped[str] = mapped_column(String(10))              # raw|odp|fdp|cdp
    status: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None]
    rows_read: Mapped[int | None]
    rows_written: Mapped[int | None]
    rows_quarantined: Mapped[int | None]
    bytes_written: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)
    airflow_dag_id: Mapped[str | None] = mapped_column(String(200))
    airflow_run_id: Mapped[str | None] = mapped_column(String(200))
```

Set up **Alembic** (`alembic init src/pipeforge/metadata/alembic`, point it at
`Base.metadata`, autogenerate the first migration, `alembic upgrade head`).
Migrations-from-day-one is the professional habit: your schema will change 8 more
times this course, and `alembic upgrade head` is how every env keeps up.

### 2.3 Repository layer + run-context — `src/pipeforge/metadata/repo.py`

```python
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from pipeforge.core.settings import settings
from pipeforge.metadata.models import Dataset, PipelineRun, SchemaContract, SourceSystem

_engine = None

def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.metadata_db_url, pool_pre_ping=True)
    return _engine


@contextmanager
def session():
    with Session(engine()) as s, s.begin():
        yield s


def get_dataset(name: str) -> Dataset:
    with session() as s:
        ds = s.execute(select(Dataset).where(Dataset.name == name)).scalar_one()
        s.expunge(ds)
        return ds


@contextmanager
def run_context(dataset_id: str, execution_date: str, layer: str):
    """Audit wrapper: every unit of work in PipeForge runs inside one of these."""
    with session() as s:
        run = PipelineRun(dataset_id=dataset_id, execution_date=execution_date, layer=layer)
        s.add(run); s.flush()
        run_id = run.run_id
    metrics: dict = {}
    try:
        yield run_id, metrics
        status, error = "success", None
    except Exception as exc:
        status, error = "failed", str(exc)[:2000]
        raise
    finally:
        with session() as s:
            run = s.get(PipelineRun, run_id)
            run.status, run.error = status, error
            run.finished_at = datetime.now(timezone.utc)
            for k in ("rows_read", "rows_written", "rows_quarantined", "bytes_written"):
                setattr(run, k, metrics.get(k))
```

### 2.4 Contract compatibility — `src/pipeforge/contracts/compat.py`

Implement the §16 rules as code (this is a fantastic unit-test target):

```python
def check_backward_compatible(old: dict, new: dict) -> list[str]:
    """JSON-Schema flavored: new readers must read old data.
    Violations: removing a field that was required, changing a type,
    adding a NEW required field without default. A RENAME = remove + add = breaking.
    Returns list of violations (empty = compatible)."""
    violations = []
    old_props, new_props = old.get("properties", {}), new.get("properties", {})
    for field, spec in old_props.items():
        if field not in new_props:
            if field in old.get("required", []):
                violations.append(f"removed required field '{field}'")
        elif new_props[field].get("type") != spec.get("type"):
            violations.append(f"type change on '{field}': {spec.get('type')} -> {new_props[field].get('type')}")
    for field in new.get("required", []):
        if field not in old.get("required", []) and "default" not in new_props.get(field, {}):
            violations.append(f"new required field '{field}' without default")
    return violations
```

Registration of contract v2 **refuses** to save if violations exist (unless
`--force-breaking`, which requires a deprecation note — the §16 change protocol).

### 2.5 CLI — registration commands

Add to `cli.py` a `register` sub-app:

```python
# pipeforge register source --name novamart_oltp --kind db --connection-ref sm://novamart-mysql --owner you@x.com
# pipeforge register dataset --source novamart_oltp --name customers --pattern incremental \
#     --watermark-column updated_at --pk customer_id --scd-type 2 \
#     --pii email,phone --business-date-column updated_at --schedule "0 2 * * *"
# pipeforge register contract --dataset customers --file contracts/customers.v1.json
# pipeforge registry show --dataset customers        # pretty-print everything known
```

### 2.6 Register the four NovaMart sources

Create `contracts/` JSON-Schema files for `orders`, `customers`, `products`,
`clickstream`, `fx_rates` (write them yourself — deciding required fields, types,
and PII flags *is* the exercise), then register all sources/datasets. Example
`contracts/orders.v1.json`:

```json
{
  "$id": "novamart.orders.v1",
  "type": "object",
  "required": ["order_id", "order_line_id", "customer_id", "product_id",
               "order_ts", "quantity", "unit_price_usd", "status"],
  "properties": {
    "order_id":        {"type": "string"},
    "order_line_id":   {"type": "string"},
    "customer_id":     {"type": "string"},
    "product_id":      {"type": "string"},
    "order_ts":        {"type": "string", "format": "date-time"},
    "quantity":        {"type": "integer", "minimum": 1},
    "unit_price_usd":  {"type": "number", "minimum": 0},
    "currency":        {"type": "string", "default": "USD"},
    "status":          {"type": "string", "enum": ["placed","paid","shipped","cancelled","returned"]}
  }
}
```

### 2.7 Ship it

Tests to write before tagging: models round-trip, `run_context` writes
success/failed rows correctly, compatibility checker (≥6 cases: add optional ✅,
remove optional ✅, remove required ❌, type change ❌, rename ❌, new required
without default ❌). Tag `v0.2.0`.

## 3. Prove it

- [ ] `alembic upgrade head` from scratch creates all tables
- [ ] `pipeforge registry show --dataset customers` prints source, pattern, keys, PII, SLA, contract v1
- [ ] Registering an incompatible contract v2 is rejected with the exact violation listed
- [ ] `pytest` ≥ 12 tests green in CI
- [ ] Cloud SQL stopped when you walk away (`activation-policy=NEVER`)

## 4. Break it

Simulate the classic Friday-4pm incident (§16): change `customers.v2` to rename
`email → email_address` and register with `--force-breaking`. Note what *will*
break downstream (nothing exists yet — but write the prediction in
`docs/incidents/002-contract-rename.md`). Revisit this file in Phase 8 when the DQ
gate actually catches it. Predict-then-verify is how you build systems intuition.

## 5. Interview corner

- *"How would you onboard 100 sources?"* — you now answer with a schema diagram you
  designed: "registration writes to a registry; every engine is parameter-driven
  off it; onboarding = INSERT, not code." (Q7)
- *"What's in a data contract?"* — schema **+ semantics + quality guarantees +
  change protocol + ownership** (§16). You built the enforcement, so mention the
  compatibility matrix (backward/forward/full) and that **a rename is a breaking change**.
- *"Why Postgres and not BigQuery for metadata?"* — transactional integrity, FKs,
  point lookups, tiny volume. Match the store to the access pattern (M05).

## 6. Stretch goals

- `pipeforge registry export --format json` → the seed of the Phase 11 catalog page.
- Add a `tags` JSONB column (domain, criticality) — Data-Mesh-ish product metadata (§25).
- Property-based tests (hypothesis) for the compatibility checker.
