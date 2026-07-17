# Phase 01 — Empty Repo → Engineering Foundation (`v0.1.0`)

> **Mission:** turn the empty repo into a professional project: Python package,
> tests, lint, CI, and a Terraform foundation (remote state, APIs, budget, core
> service accounts, the lake buckets). Nothing "data" happens yet — this phase is
> what separates a portfolio project from a script dump.

## 1. Concepts

- GCP course **M01** (IAM, service accounts, least privilege) and **M02** (bucket design) are the backbone here.
- Notes **§15 (cost)**: infra-as-code is a cost tool — `terraform destroy` is the ultimate auto-suspend.
- Interview relevance: platform questions (Q7/Q15/Q19) always include "how do teams get environments?" Answer: *composable Terraform modules + per-env compositions* — which you're about to build.

**Terraform structure decision (memorize the reasoning):**

- `terraform/bootstrap/` — the chicken-and-egg resources (the state bucket itself,
  project APIs, budget). Applied once with **local** state, then never touched.
- `terraform/modules/` — reusable building blocks (`gcs_lake`, `bigquery`, …).
- `terraform/envs/dev/` — a *composition* that wires modules together with dev-sized
  knobs. Adding `envs/prod` later = new folder + bigger knobs, zero module changes.
  That sentence is a staff-level answer to "how do you promote infra between envs?"

## 2. Build

### 2.1 Repository skeleton + Python packaging

```bash
git clone git@github.com:<you>/pipeforge.git && cd pipeforge
mkdir -p src/pipeforge/core tests terraform/{bootstrap,modules,envs/dev} .github/workflows
```

`pyproject.toml`:

```toml
[project]
name = "pipeforge"
version = "0.1.0"
description = "Open-source, metadata-driven data platform on GCP"
requires-python = ">=3.11"
license = {text = "Apache-2.0"}
dependencies = [
  "typer>=0.12", "pydantic>=2.7", "pydantic-settings>=2.2",
  "google-cloud-storage>=2.16", "google-cloud-bigquery>=3.21",
  "sqlalchemy>=2.0", "structlog>=24.1",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-cov", "ruff>=0.4", "mypy", "pre-commit", "types-requests"]

[project.scripts]
pipeforge = "pipeforge.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
lint.select = ["E", "F", "I", "B", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`src/pipeforge/core/settings.py` — one config object, env-driven (12-factor):

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime config. Values come from env vars prefixed PF_ (never hardcode)."""
    model_config = SettingsConfigDict(env_prefix="PF_", env_file=".env", extra="ignore")

    project_id: str
    region: str = "us-central1"
    env: str = "dev"
    raw_bucket: str = ""          # filled by terraform output
    quarantine_bucket: str = ""
    metadata_db_url: str = ""     # set in Phase 2

    @property
    def resource_prefix(self) -> str:
        return f"pf-{self.env}"


settings = Settings()  # import-time singleton; tests override via env
```

`src/pipeforge/core/logging.py`:

```python
import structlog

def configure_logging() -> None:
    structlog.configure(processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),      # JSON logs → Cloud Logging-friendly
    ])

log = structlog.get_logger("pipeforge")
```

`src/pipeforge/cli.py` (grows every phase):

```python
import typer
from pipeforge.core.logging import configure_logging

app = typer.Typer(help="PipeForge — metadata-driven data platform on GCP")

@app.callback()
def _init() -> None:
    configure_logging()

@app.command()
def version() -> None:
    """Print version."""
    from importlib.metadata import version as v
    typer.echo(v("pipeforge"))
```

First test, `tests/test_cli.py`:

```python
from typer.testing import CliRunner
from pipeforge.cli import app

def test_version_runs():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
```

```bash
pip install -e ".[dev]"   # or: uv pip install -e ".[dev]"
pytest && ruff check .
```

Add `LICENSE` (Apache-2.0), `.gitignore` (Python + Terraform: `.terraform/`,
`*.tfstate*`, `.env`), and a minimal `README.md` with the elevator pitch from the
charter — you'll rewrite it properly in Phase 14.

### 2.2 CI — GitHub Actions

`.github/workflows/ci.yml`:

```yaml
name: ci
on:
  push: {branches: [main]}
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest --cov=pipeforge
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform fmt -check -recursive
        working-directory: terraform
      - run: |
          terraform init -backend=false
          terraform validate
        working-directory: terraform/envs/dev
```

(Real `terraform plan` in CI needs cloud auth — Workload Identity Federation is a
Phase 12 stretch goal; `validate` keeps CI honest until then.)

### 2.3 Terraform bootstrap (local state, applied once)

`terraform/bootstrap/main.tf`:

```hcl
terraform {
  required_version = ">= 1.7"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.30" }
  }
}

variable "project_id" { type = string }
variable "region"     { type = string, default = "us-central1" }
variable "billing_account" { type = string }

provider "google" {
  project = var.project_id
  region  = var.region
}

# APIs the whole course needs (enabling is free; using them isn't)
resource "google_project_service" "apis" {
  for_each = toset([
    "storage.googleapis.com", "bigquery.googleapis.com", "sqladmin.googleapis.com",
    "dataproc.googleapis.com", "pubsub.googleapis.com", "run.googleapis.com",
    "secretmanager.googleapis.com", "cloudkms.googleapis.com", "dlp.googleapis.com",
    "dataplex.googleapis.com", "datacatalog.googleapis.com",
    "monitoring.googleapis.com", "logging.googleapis.com",
    "cloudbilling.googleapis.com", "billingbudgets.googleapis.com",
    "artifactregistry.googleapis.com", "compute.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# Remote state bucket — versioned, so a bad state push is recoverable
resource "google_storage_bucket" "tf_state" {
  name                        = "${var.project_id}-tf-state"
  location                    = var.region
  uniform_bucket_level_access = true
  versioning { enabled = true }
  public_access_prevention = "enforced"
}

# The budget from Phase 0, now as code
resource "google_billing_budget" "guardrail" {
  billing_account = var.billing_account
  display_name    = "pipeforge-guardrail-tf"
  budget_filter { projects = ["projects/${var.project_id}"] }
  amount { specified_amount { currency_code = "USD", units = "25" } }
  dynamic "threshold_rules" {
    for_each = [0.5, 0.9, 1.0]
    content { threshold_percent = threshold_rules.value }
  }
}

output "state_bucket" { value = google_storage_bucket.tf_state.name }
```

```bash
cd terraform/bootstrap
terraform init
terraform apply -var project_id=$PROJECT_ID -var billing_account=<ACCOUNT_ID>
```

### 2.4 First reusable module + dev environment

`terraform/modules/gcs_lake/main.tf`:

```hcl
variable "project_id" { type = string }
variable "region"     { type = string }
variable "env"        { type = string }

locals { prefix = "${var.project_id}-pf-${var.env}" }

resource "google_storage_bucket" "zones" {
  for_each                    = toset(["raw", "quarantine", "artifacts"])
  name                        = "${local.prefix}-${each.key}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  # Lifecycle rules arrive in Phase 9 (archival framework) — resist adding them now.
}

output "buckets" { value = { for k, b in google_storage_bucket.zones : k => b.name } }
```

`terraform/envs/dev/main.tf`:

```hcl
terraform {
  required_version = ">= 1.7"
  backend "gcs" {
    bucket = "REPLACE_WITH_STATE_BUCKET"   # from bootstrap output
    prefix = "envs/dev"
  }
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.30" }
  }
}

variable "project_id" { type = string }
variable "region"     { type = string, default = "us-central1" }

provider "google" {
  project = var.project_id
  region  = var.region
}

module "lake" {
  source     = "../../modules/gcs_lake"
  project_id = var.project_id
  region     = var.region
  env        = "dev"
}

# Runtime SA for pipelines — least privilege grows with the course, never Editor
resource "google_service_account" "pipeline" {
  account_id   = "pf-dev-pipeline"
  display_name = "PipeForge dev pipeline runtime"
}

resource "google_storage_bucket_iam_member" "pipeline_rw" {
  for_each = module.lake.buckets
  bucket   = each.value
  role     = "roles/storage.objectAdmin"
  member   = "serviceAccount:${google_service_account.pipeline.email}"
}

output "buckets"        { value = module.lake.buckets }
output "pipeline_sa"    { value = google_service_account.pipeline.email }
```

```bash
cd terraform/envs/dev
terraform init && terraform apply -var project_id=$PROJECT_ID
# Wire outputs into your .env:
echo "PF_PROJECT_ID=$PROJECT_ID" >> ../../../.env
echo "PF_RAW_BUCKET=$(terraform output -json buckets | jq -r .raw)" >> ../../../.env
echo "PF_QUARANTINE_BUCKET=$(terraform output -json buckets | jq -r .quarantine)" >> ../../../.env
```

### 2.5 Ship it

```bash
git add -A && git commit -m "Engineering foundation: package, CI, terraform bootstrap + dev env"
git push -u origin main
git tag v0.1.0 && git push origin v0.1.0
```

Open a GitHub Release for `v0.1.0` with 3 bullet points. Every phase ends like this.

## 3. Prove it

- [ ] CI green on GitHub (lint + tests + terraform fmt/validate)
- [ ] `pipeforge version` prints `0.1.0`
- [ ] `gsutil ls` shows raw/quarantine/artifacts buckets; state bucket has versioning
- [ ] Budget exists **in Terraform state** (`terraform state list | grep budget`)
- [ ] The pipeline SA has objectAdmin on the lake buckets and *nothing project-wide*

## 4. Break it

Corrupt your local Terraform state (rename `.terraform/` and change backend prefix
to a typo), run `plan`, observe the blast radius, then recover using the **GCS
state bucket versioning**. Write a 5-line postmortem in `docs/incidents/001-tf-state.md`.
The habit of writing postmortems starts now — they become your interview war stories (§8).

## 5. Interview corner

- *"How do you manage environments?"* → module/composition split, remote state per
  env, same modules dev→prod with different knobs.
- *"How do you keep cloud costs sane on a platform team?"* → budget-as-code before
  the first resource, serverless-first, destroy-able envs.
- Rehearse: 60 seconds on why the runtime SA has **no** project-level role (least
  privilege, M01) and why the state bucket is versioned (recoverability).

## 6. Stretch goals

- `pre-commit` with ruff + terraform fmt hooks.
- Add `terraform/envs/dev/README.md` documenting inputs/outputs — module docs are open-source hygiene.
- Protect `main` (require PR + green CI) and work via PRs from now on.
