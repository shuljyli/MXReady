# MXReady MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally deployable MXReady MVP that statically scans public GitHub/Gitee Python + PyTorch CUDA extension repositories, produces evidence-backed migration reports, and accepts manually generated MetaX verification results.

**Architecture:** A FastAPI service owns repository acquisition, static analysis, SQLite persistence, reporting, and verification-result validation. A React/Vite single-page frontend consumes the versioned API, while a separate Python runner executes only on a user-controlled MetaX host. Rule data lives in versioned YAML and all non-hardware behavior is covered by offline fixtures.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, PyYAML, SQLite, pytest, Ruff, React 19, TypeScript 5, Vite 7, Vitest, Testing Library. The downloadable runner uses only the Python 3.11 standard library.

## Global Constraints

- The Web service MUST NOT execute code from a scanned repository.
- The Web service accepts only public HTTPS repositories on `github.com` and `gitee.com`.
- Default clone timeout is exactly 60 seconds.
- Maximum downloaded repository size is exactly 50 MiB.
- Maximum indexed file count is exactly 10,000.
- Maximum indexed text-file size is exactly 1 MiB.
- Git submodules and Git LFS downloads remain disabled.
- MVP scans only Python + PyTorch CUDA extension projects and related build files.
- Static findings use only `blocker`, `warning`, and `info` severities.
- Reports MUST NOT expose a percentage compatibility score.
- A report can become `verified` only when a successful verification result references the exact scanned commit.
- The runner MUST NOT use `sudo`, install software, change drivers, or upload secrets.
- The downloadable runner MUST NOT require third-party Python packages.
- Offline automated tests MUST NOT require GitHub, Gitee, MXMACA, or a GPU.
- Public SaaS authentication, private repositories, automatic fixes, Docker orchestration, and cloud GPU scheduling are out of scope.

---

## Planned File Structure

```text
.
├── .github/workflows/ci.yml
├── .gitignore
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── pyproject.toml
├── backend/mxready/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── errors.py
│   ├── models.py
│   ├── storage.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── scans.py
│   │   └── rules.py
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── identity.py
│   │   └── git_client.py
│   ├── scanning/
│   │   ├── __init__.py
│   │   ├── indexer.py
│   │   ├── facts.py
│   │   ├── rule_loader.py
│   │   ├── rule_engine.py
│   │   └── analyzer.py
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── markdown.py
│   │   └── badge.py
│   ├── verification/
│   │   ├── __init__.py
│   │   ├── bundle.py
│   │   └── validation.py
│   └── services/
│       ├── __init__.py
│       └── scans.py
├── runner/mxready_runner/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── inspect.py
│   ├── execute.py
│   ├── redact.py
│   └── schema.py
├── rules/
│   └── v1/
│       ├── manifest.yml
│       └── core.yml
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── styles.css
│       ├── api/
│       │   ├── client.ts
│       │   └── types.ts
│       └── components/
│           ├── ScanForm.tsx
│           ├── ScanProgress.tsx
│           ├── ReportView.tsx
│           ├── FindingCard.tsx
│           └── VerificationPanel.tsx
├── schemas/
│   └── verification-result-v1.json
├── scripts/
│   └── scan_repository.py
├── tests/
│   ├── backend/
│   ├── runner/
│   └── fixtures/
│       ├── repositories/
│       ├── rules/
│       └── verification/
├── docs/
│   ├── rules.md
│   ├── runner.md
│   └── security.md
└── examples/
    ├── reports/
    └── verification/
```

Each module above owns one responsibility. In particular, repository acquisition never imports the analyzer, report rendering never reads Git repositories, and the Web API never imports the runner's command executor.

---

### Task 1: Python Project Foundation and Health API

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `backend/mxready/__init__.py`
- Create: `backend/mxready/config.py`
- Create: `backend/mxready/app.py`
- Create: `tests/backend/test_app.py`

**Interfaces:**
- Produces: `mxready.config.Settings`
- Produces: `mxready.app.create_app(settings: Settings | None = None) -> FastAPI`
- Produces: `GET /api/health -> {"status": "ok", "version": str}`

- [ ] **Step 1: Write the failing health test**

```python
# tests/backend/test_app.py
from fastapi.testclient import TestClient

from mxready.app import create_app
from mxready.config import Settings


def test_health_endpoint_uses_application_version(tmp_path):
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=tmp_path / "rules",
            temp_dir=tmp_path / "tmp",
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 2: Run the test and verify the foundation is missing**

Run: `python -m pytest tests/backend/test_app.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'mxready'`.

- [ ] **Step 3: Add package configuration and the minimal application**

Create `pyproject.toml` with these declared packages and commands:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "mxready"
version = "0.1.0"
description = "Static readiness checks for moving PyTorch CUDA extensions to MetaX MXMACA"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "Apache-2.0"}
dependencies = [
  "fastapi>=0.115,<1",
  "pydantic>=2.10,<3",
  "PyYAML>=6,<7",
  "uvicorn>=0.34,<1",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.28,<1",
  "pytest>=8,<9",
  "pytest-cov>=6,<8",
  "ruff>=0.11,<1",
]

[project.scripts]
mxready-scan = "scripts.scan_repository:main"
mxready-runner = "mxready_runner.cli:main"

[tool.setuptools.packages.find]
where = ["backend", "runner", "."]
include = ["mxready*", "mxready_runner*", "scripts*"]

[tool.pytest.ini_options]
addopts = "-ra --strict-markers"
testpaths = ["tests"]
pythonpath = ["backend", "runner", "."]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

Implement the exact settings and app factory:

```python
# backend/mxready/config.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path = Path("data")
    rules_dir: Path = Path("rules/v1")
    temp_dir: Path = Path("data/tmp")
```

```python
# backend/mxready/app.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from mxready import __version__
from mxready.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved.data_dir.mkdir(parents=True, exist_ok=True)
        resolved.temp_dir.mkdir(parents=True, exist_ok=True)
        app.state.settings = resolved
        yield

    app = FastAPI(title="MXReady", version=__version__, lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
```

Set `__version__ = "0.1.0"` in `backend/mxready/__init__.py`. Ignore Python caches, virtual environments, `data/*.db`, `data/tmp`, `frontend/node_modules`, `frontend/dist`, coverage output, and editor files in `.gitignore`.

- [ ] **Step 4: Install development dependencies and run the test**

Run: `python -m pip install -e ".[dev]"`

Run: `python -m pytest tests/backend/test_app.py -v`

Expected: PASS.

- [ ] **Step 5: Run lint and commit**

Run: `python -m ruff check backend tests/backend/test_app.py`

Expected: PASS.

```bash
git add .gitignore pyproject.toml backend/mxready tests/backend/test_app.py
git commit -m "chore: establish MXReady backend foundation"
```

---

### Task 2: Versioned Domain Models and Status Rules

**Files:**
- Create: `backend/mxready/models.py`
- Create: `backend/mxready/errors.py`
- Create: `tests/conftest.py`
- Create: `tests/backend/test_models.py`

**Interfaces:**
- Produces: `ScanStatus`, `Severity`, `StaticStatus`, `VerificationStatus`, `BadgeStatus`
- Produces: `ScanJob`, `SourceReference`, `RepositorySnapshot`, `Finding`, `ScanSummary`, `MigrationChecklistItem`, `AnalysisWarning`, `ScanReport`
- Produces: `VerificationCheck`, `VerificationCommand`, `VerificationRun`
- Produces: `summarize_findings(findings: list[Finding]) -> ScanSummary`
- Produces: `calculate_badge_status(report: ScanReport) -> BadgeStatus`
- Produces: `MxReadyError(code: str, message: str)`
- Produces test fixture: `report_factory(*, scan_id=None, commit="a"*40, repository_name="project", findings=None, summary=None, static_status=PASSED, verification_status=NOT_RUN) -> ScanReport`

- [ ] **Step 1: Write failing status and serialization tests**

```python
# tests/backend/test_models.py
from mxready.models import (
    BadgeStatus,
    Finding,
    ScanReport,
    Severity,
    StaticStatus,
    VerificationStatus,
    calculate_badge_status,
    summarize_findings,
)


def test_blocker_controls_static_and_badge_status(report_factory):
    finding = Finding(
        rule_id="MXR-CUDA-001",
        rule_version=1,
        severity=Severity.BLOCKER,
        category="toolchain",
        title="Hard-coded nvcc",
        relative_path="setup.py",
        line_start=12,
        line_end=12,
        evidence="compiler = 'nvcc'",
        message="The build invokes nvcc directly.",
        recommendation="Use a configurable compiler entry point.",
        references=[],
    )

    summary = summarize_findings([finding])
    report = report_factory(
        findings=[finding],
        summary=summary,
        static_status=StaticStatus.BLOCKED,
        verification_status=VerificationStatus.NOT_RUN,
    )

    assert summary.blocker_count == 1
    assert calculate_badge_status(report) is BadgeStatus.BLOCKED
    assert report.model_dump(mode="json")["schema_version"] == "1.0"


def test_verified_requires_static_pass_and_fresh_success(report_factory):
    report = report_factory(
        findings=[],
        summary=summarize_findings([]),
        static_status=StaticStatus.PASSED,
        verification_status=VerificationStatus.VERIFIED,
    )
    assert calculate_badge_status(report) is BadgeStatus.VERIFIED
```

Create the shared test factory with concrete defaults:

```python
# tests/conftest.py
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mxready.models import (
    RepositorySnapshot,
    ScanReport,
    StaticStatus,
    VerificationStatus,
    summarize_findings,
)


@pytest.fixture
def report_factory():
    def factory(
        *,
        scan_id=None,
        commit="a" * 40,
        repository_name="project",
        findings=None,
        summary=None,
        static_status=StaticStatus.PASSED,
        verification_status=VerificationStatus.NOT_RUN,
    ):
        resolved_findings = list(findings or [])
        return ScanReport(
            schema_version="1.0",
            scan_id=scan_id or uuid4(),
            repository=RepositorySnapshot(
                provider="github",
                owner="example",
                name=repository_name,
                url=f"https://github.com/example/{repository_name}",
                commit=commit,
            ),
            tool_version="0.1.0",
            ruleset_version="1",
            scanned_at=datetime(2026, 7, 29, tzinfo=UTC),
            summary=summary or summarize_findings(resolved_findings),
            findings=resolved_findings,
            migration_checklist=[],
            analysis_warnings=[],
            static_status=static_status,
            verification_status=verification_status,
        )

    return factory
```

- [ ] **Step 2: Run the tests and verify the models do not exist**

Run: `python -m pytest tests/backend/test_models.py -v`

Expected: FAIL importing `mxready.models`.

- [ ] **Step 3: Implement enums, immutable report models, and status calculation**

Use `str, Enum` enums with these exact values:

```python
class ScanStatus(str, Enum):
    QUEUED = "queued"
    CLONING = "cloning"
    INDEXING = "indexing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, Enum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class StaticStatus(str, Enum):
    PASSED = "passed"
    WARNINGS = "warnings"
    BLOCKED = "blocked"
    FAILED = "failed"


class VerificationStatus(str, Enum):
    NOT_RUN = "not-run"
    VERIFIED = "verified"
    FAILED = "failed"
    STALE = "stale"


class BadgeStatus(str, Enum):
    STATIC_PASSED = "static-passed"
    WARNINGS = "warnings"
    BLOCKED = "blocked"
    VERIFIED = "verified"
    VERIFICATION_STALE = "verification-stale"
    SCAN_FAILED = "scan-failed"
```

All external models inherit Pydantic `BaseModel`, set `extra="forbid"`, and use timezone-aware UTC datetimes. `VerificationRun` has the exact fields `schema_version: Literal["1.0"]`, `scan_id: UUID`, `repository_commit: str`, `runner_version: str`, `environment_fingerprint: str`, `checks: list[VerificationCheck]`, `commands: list[VerificationCommand]`, `started_at: datetime`, `finished_at: datetime`, and `overall_status: Literal["passed", "failed", "cancelled"]`.

Status calculation rules:

1. Any blocker yields `blocked`.
2. Otherwise any warning yields `warnings`.
3. Otherwise static status is `passed`.
4. `verified` takes badge precedence only for a successful, exact-commit verification.
5. `stale` takes precedence over static warning/passed badges but not over a static blocker.
6. A failed scan yields `scan-failed`.

Implement `MxReadyError` as a typed exception carrying `code`, `message`, and HTTP-safe `details: dict[str, str]`.

- [ ] **Step 4: Run focused tests and type-safe serialization checks**

Run: `python -m pytest tests/backend/test_models.py -v`

Expected: PASS.

Run: `python -m ruff check backend/mxready/models.py backend/mxready/errors.py tests/backend/test_models.py`

Expected: PASS.

- [ ] **Step 5: Commit the domain contract**

```bash
git add backend/mxready/models.py backend/mxready/errors.py tests/conftest.py tests/backend/test_models.py
git commit -m "feat: define versioned scan and verification models"
```

---

### Task 3: SQLite Scan Store

**Files:**
- Create: `backend/mxready/storage.py`
- Create: `tests/backend/test_storage.py`
- Modify: `backend/mxready/app.py`

**Interfaces:**
- Consumes: `ScanJob`, `ScanReport`, `VerificationRun`
- Produces: `SQLiteStore(path: Path)`
- Produces: `initialize() -> None`
- Produces: `create_job(repo_url: str, requested_ref: str | None) -> ScanJob`
- Produces: `get_job(scan_id: UUID) -> ScanJob | None`
- Produces: `update_job(scan_id: UUID, *, status, stage_message, resolved_commit=None, failure_code=None, failure_message=None) -> ScanJob`
- Produces: `save_report(report: ScanReport) -> None`
- Produces: `get_report(scan_id: UUID) -> ScanReport | None`
- Produces: `save_verification(scan_id: UUID, run: VerificationRun) -> None`

- [ ] **Step 1: Write failing persistence and restart tests**

```python
# tests/backend/test_storage.py
from mxready.models import ScanStatus
from mxready.storage import SQLiteStore


def test_scan_job_survives_store_reopen(tmp_path):
    database = tmp_path / "mxready.db"
    first = SQLiteStore(database)
    first.initialize()
    created = first.create_job("https://github.com/pytorch/extension-cpp", None)
    first.update_job(
        created.id,
        status=ScanStatus.CLONING,
        stage_message="Cloning repository",
    )

    reopened = SQLiteStore(database)
    reopened.initialize()
    loaded = reopened.get_job(created.id)

    assert loaded is not None
    assert loaded.status is ScanStatus.CLONING
    assert loaded.repo_url == "https://github.com/pytorch/extension-cpp"


def test_initialize_marks_interrupted_jobs_failed(tmp_path):
    store = SQLiteStore(tmp_path / "mxready.db")
    store.initialize()
    job = store.create_job("https://gitee.com/example/project", None)

    store.mark_interrupted_jobs_failed()

    loaded = store.get_job(job.id)
    assert loaded.failure_code == "SCAN_INTERRUPTED"
    assert loaded.status is ScanStatus.FAILED
```

- [ ] **Step 2: Run the test and confirm storage is absent**

Run: `python -m pytest tests/backend/test_storage.py -v`

Expected: FAIL importing `SQLiteStore`.

- [ ] **Step 3: Implement per-operation SQLite connections**

Use a `scan_jobs` table with scalar job columns and `report_json`, `verification_json` TEXT columns. Use `sqlite3.connect(self.path, timeout=5)`, enable WAL and foreign keys in `initialize`, and serialize Pydantic models with `model_dump_json()`.

The table must use the UUID string as primary key and store timestamps in ISO-8601 UTC. Every write runs inside `with connection:`. Do not retain a global SQLite connection across FastAPI threads.

Implement `mark_interrupted_jobs_failed()` to update `queued`, `cloning`, `indexing`, and `analyzing` jobs to:

```text
status = failed
failure_code = SCAN_INTERRUPTED
failure_message = The MXReady service restarted before this scan completed. Start a new scan.
```

- [ ] **Step 4: Wire the store into application lifespan and verify**

During lifespan:

```python
store = SQLiteStore(resolved.data_dir / "mxready.db")
store.initialize()
store.mark_interrupted_jobs_failed()
app.state.store = store
```

Run: `python -m pytest tests/backend/test_storage.py tests/backend/test_app.py -v`

Expected: PASS.

- [ ] **Step 5: Commit persistence**

```bash
git add backend/mxready/storage.py backend/mxready/app.py tests/backend/test_storage.py
git commit -m "feat: persist scan jobs and reports in sqlite"
```

---

### Task 4: Repository Identity and Bounded Git Acquisition

**Files:**
- Create: `backend/mxready/repository/__init__.py`
- Create: `backend/mxready/repository/identity.py`
- Create: `backend/mxready/repository/git_client.py`
- Create: `tests/backend/test_repository_identity.py`
- Create: `tests/backend/test_git_client.py`

**Interfaces:**
- Produces: `RepositoryIdentity(provider: str, owner: str, name: str, clone_url: str)`
- Produces: `parse_repository_url(value: str) -> RepositoryIdentity`
- Produces: `validate_git_ref(value: str | None) -> str | None`
- Produces: `RepositoryLimits(clone_timeout_seconds=60, max_bytes=52_428_800, max_files=10_000)`
- Produces: `GitClient.clone(identity, requested_ref, destination) -> str` returning a 40-character commit
- Consumes: injectable `CommandRunner(args, cwd, env, timeout) -> CompletedProcess[str]`

- [ ] **Step 1: Write failing allowlist and command-construction tests**

```python
# tests/backend/test_repository_identity.py
import pytest

from mxready.errors import MxReadyError
from mxready.repository.identity import parse_repository_url, validate_git_ref


@pytest.mark.parametrize(
    ("url", "provider", "clone_url"),
    [
        (
            "https://github.com/pytorch/extension-cpp.git",
            "github",
            "https://github.com/pytorch/extension-cpp.git",
        ),
        (
            "https://gitee.com/metax-maca/cu-bridge",
            "gitee",
            "https://gitee.com/metax-maca/cu-bridge.git",
        ),
    ],
)
def test_public_repository_urls_are_normalized(url, provider, clone_url):
    identity = parse_repository_url(url)
    assert identity.provider == provider
    assert identity.clone_url == clone_url


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/pytorch/extension-cpp",
        "https://user:token@github.com/pytorch/extension-cpp",
        "https://github.example.com/owner/repo",
        "file:///tmp/repo",
        "C:\\repo",
        "https://127.0.0.1/repo",
    ],
)
def test_non_public_or_credentialed_urls_are_rejected(url):
    with pytest.raises(MxReadyError) as error:
        parse_repository_url(url)
    assert error.value.code in {"INVALID_REPOSITORY_URL", "UNSUPPORTED_REPOSITORY_HOST"}


def test_git_ref_rejects_option_injection():
    with pytest.raises(MxReadyError):
        validate_git_ref("--upload-pack=malicious")
```

```python
# tests/backend/test_git_client.py
from pathlib import Path
from subprocess import CompletedProcess

from mxready.repository.git_client import GitClient
from mxready.repository.identity import parse_repository_url


class RecordingRunner:
    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, args, *, cwd, env, timeout):
        self.calls.append(args)
        if args[-2:] == ["rev-parse", "HEAD"]:
            return CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")
        Path(args[-1]).mkdir(parents=True, exist_ok=True)
        return CompletedProcess(args, 0, stdout="", stderr="")


def test_clone_uses_argument_array_and_disables_prompts(tmp_path):
    runner = RecordingRunner()
    client = GitClient(command_runner=runner)
    commit = client.clone(
        parse_repository_url("https://github.com/pytorch/extension-cpp"),
        None,
        tmp_path / "repo",
    )

    assert runner.calls[0][:4] == ["git", "clone", "--depth", "1"]
    assert commit == "a" * 40
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m pytest tests/backend/test_repository_identity.py tests/backend/test_git_client.py -v`

Expected: FAIL because repository modules do not exist.

- [ ] **Step 3: Implement strict URL/ref parsing and Git subprocess boundary**

URL parsing requirements:

- scheme exactly `https`;
- hostname exactly `github.com` or `gitee.com`;
- no username, password, query, fragment, port, or extra path segments;
- owner and repository each match `[A-Za-z0-9_.-]+`;
- `.git` suffix normalized to one suffix.

Reference requirements:

- `None` is accepted;
- 1–200 characters;
- matches `[A-Za-z0-9][A-Za-z0-9._/-]*`;
- contains neither `..`, `@{`, backslash, control characters, leading `-`, nor trailing `/`.

Default clone command:

```python
[
    "git", "clone", "--depth", "1", "--single-branch", "--no-tags",
    identity.clone_url, str(destination),
]
```

With a requested reference, insert `["--branch", requested_ref]` before the URL for branches/tags. For a 40-character hexadecimal commit, run `git init`, add the fixed origin URL, fetch exactly that commit with `--depth 1`, and check out `FETCH_HEAD` detached.

Set `GIT_TERMINAL_PROMPT=0`, `GIT_LFS_SKIP_SMUDGE=1`, and a blank credential helper. Map process timeout, authentication/not-found, and nonzero exit to the stable errors in the specification. After cloning, calculate directory bytes and regular-file count without following symlinks; raise `REPOSITORY_TOO_LARGE` or `TOO_MANY_FILES` when limits are exceeded.

- [ ] **Step 4: Run repository tests**

Run: `python -m pytest tests/backend/test_repository_identity.py tests/backend/test_git_client.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the repository boundary**

```bash
git add backend/mxready/repository tests/backend/test_repository_identity.py tests/backend/test_git_client.py
git commit -m "feat: add bounded public repository acquisition"
```

---

### Task 5: Safe File Index and Structured Project Facts

**Files:**
- Create: `backend/mxready/scanning/__init__.py`
- Create: `backend/mxready/scanning/indexer.py`
- Create: `backend/mxready/scanning/facts.py`
- Create: `tests/backend/test_indexer.py`
- Create: `tests/backend/test_facts.py`
- Create: `tests/fixtures/repositories/cuda_extension/requirements.txt`
- Create: `tests/fixtures/repositories/cuda_extension/pyproject.toml`
- Create: `tests/fixtures/repositories/cuda_extension/setup.py`
- Create: `tests/fixtures/repositories/cuda_extension/CMakeLists.txt`
- Create: `tests/fixtures/repositories/cuda_extension/csrc/kernel.cu`

**Interfaces:**
- Produces: `IndexedFile(relative_path: str, size: int, sha256: str, text: str)`
- Produces: `IndexWarning(code: str, relative_path: str, message: str)`
- Produces: `FileIndex(files: Sequence[IndexedFile], warnings: Sequence[IndexWarning])`
- Produces: `build_file_index(root: Path, *, max_files=10_000, max_file_bytes=1_048_576) -> FileIndex`
- Produces: `SourceLocation(relative_path: str, line: int, evidence: str)`
- Produces: `ProjectFacts(dependencies, build_systems, flags, locations)`
- Produces: `extract_project_facts(index: FileIndex) -> ProjectFacts`

- [ ] **Step 1: Write failing safety and fact tests**

```python
# tests/backend/test_indexer.py
from mxready.scanning.indexer import build_file_index


def test_indexer_skips_build_binary_and_symlink(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "extension.py").write_text("CUDA_HOME = '/usr/local/cuda'")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "generated.py").write_text("ignored = True")
    (tmp_path / "weights.bin").write_bytes(b"\x00\x01")

    index = build_file_index(tmp_path)

    assert [item.relative_path for item in index.files] == ["src/extension.py"]
```

```python
# tests/backend/test_facts.py
from pathlib import Path

from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import build_file_index


FIXTURE = Path("tests/fixtures/repositories/cuda_extension")


def test_extracts_dependencies_and_cuda_extension_facts():
    facts = extract_project_facts(build_file_index(FIXTURE))

    assert "torch" in facts.dependencies
    assert "flash-attn" in facts.dependencies
    assert "setuptools" in facts.build_systems
    assert facts.flags["uses_torch_cuda_extension"] is True
    assert facts.flags["uses_cmake_cuda_language"] is True
```

- [ ] **Step 2: Run tests and verify missing indexer/facts**

Run: `python -m pytest tests/backend/test_indexer.py tests/backend/test_facts.py -v`

Expected: FAIL importing the scanning modules.

- [ ] **Step 3: Implement deterministic indexing**

Allowed extensions:

```python
{
    ".py", ".toml", ".txt", ".cfg", ".cmake", ".cu", ".cuh",
    ".cc", ".cpp", ".c", ".h", ".hpp", ".sh", ".md", ".yml", ".yaml",
}
```

Also allow the exact filename `CMakeLists.txt`. Exclude `.git`, `node_modules`, `vendor`, `.venv`, `venv`, `dist`, `build`, `target`, `__pycache__`, and hidden cache directories. Never follow symlinks.

Decode in order with `utf-8-sig`, then `gb18030`. When neither works, append `UNSUPPORTED_TEXT_ENCODING` to warnings and skip the file. Normalize paths to POSIX separators and sort lexically before returning.

- [ ] **Step 4: Implement conservative structured facts**

Use:

- `tomllib` for `pyproject.toml`;
- line parsing for `requirements*.txt`;
- Python `ast` for imports, assignments, `CUDAExtension`, `CppExtension`, and `torch.utils.cpp_extension.load`;
- regex facts for CMake language/package declarations;
- regex facts for shell tools and environment variables.

Do not import or execute repository files. Record source locations for every boolean fact that becomes true.

Run: `python -m pytest tests/backend/test_indexer.py tests/backend/test_facts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit indexing and fact extraction**

```bash
git add backend/mxready/scanning tests/backend/test_indexer.py tests/backend/test_facts.py tests/fixtures/repositories/cuda_extension
git commit -m "feat: index source files and extract build facts"
```

---

### Task 6: Versioned YAML Rule Loader and Evaluation Engine

**Files:**
- Create: `backend/mxready/scanning/rule_loader.py`
- Create: `backend/mxready/scanning/rule_engine.py`
- Create: `rules/v1/manifest.yml`
- Create: `rules/v1/core.yml`
- Create: `tests/backend/test_rule_loader.py`
- Create: `tests/backend/test_rule_engine.py`
- Create: `tests/fixtures/rules/manifest.yml`
- Create: `tests/fixtures/rules/invalid.yml`

**Interfaces:**
- Produces: `RulePattern(type: Literal["regex", "dependency", "fact"], expression: str | None, flags: list[str], name: str | None, equals: bool | str | None)`
- Produces: `RuleDefinition(id, version, title, category, severity, file_globs, patterns, message, recommendation, references)`
- Produces: `RuleCatalog(version: str, rules: Sequence[RuleDefinition])`
- Produces: `load_rule_catalog(directory: Path) -> RuleCatalog`
- Produces: `evaluate_rules(catalog: RuleCatalog, index: FileIndex, facts: ProjectFacts) -> list[Finding]`

- [ ] **Step 1: Write failing validation and evidence tests**

```python
# tests/backend/test_rule_loader.py
import pytest

from mxready.errors import MxReadyError
from mxready.scanning.rule_loader import load_rule_catalog


def test_invalid_rule_set_fails_with_stable_error():
    with pytest.raises(MxReadyError) as error:
        load_rule_catalog("tests/fixtures/rules")
    assert error.value.code == "RULESET_INVALID"
```

Use this deliberately invalid fixture:

```yaml
# tests/fixtures/rules/manifest.yml
schema_version: "1.0"
ruleset_version: "invalid-fixture"
rule_files: [invalid.yml]
```

```yaml
# tests/fixtures/rules/invalid.yml
- id: not-a-valid-rule-id
  version: 1
  title: Missing required rule fields
  unexpected_field: true
```

```python
# tests/backend/test_rule_engine.py
from pathlib import Path

from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import build_file_index
from mxready.scanning.rule_engine import evaluate_rules
from mxready.scanning.rule_loader import load_rule_catalog


def test_regex_finding_has_line_evidence_and_migration_advice():
    index = build_file_index(Path("tests/fixtures/repositories/cuda_extension"))
    facts = extract_project_facts(index)
    findings = evaluate_rules(load_rule_catalog(Path("rules/v1")), index, facts)

    direct_nvcc = next(item for item in findings if item.rule_id == "MXR-TOOLCHAIN-001")
    assert direct_nvcc.relative_path == "setup.py"
    assert direct_nvcc.line_start > 0
    assert len(direct_nvcc.evidence) <= 240
    assert direct_nvcc.recommendation
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `python -m pytest tests/backend/test_rule_loader.py tests/backend/test_rule_engine.py -v`

Expected: FAIL because rule modules and rule data do not exist.

- [ ] **Step 3: Implement strict YAML loading**

`rules/v1/manifest.yml`:

```yaml
schema_version: "1.0"
ruleset_version: "1"
rule_files:
  - core.yml
```

`core.yml` is a YAML list. Reject unknown fields, duplicate IDs, invalid severity, missing HTTPS references, empty recommendations, invalid regexes, and IDs not matching `MXR-[A-Z]+-[0-9]{3}`.

Pattern contracts:

```yaml
- type: regex
  expression: "\\bnvcc\\b"
  flags: ["IGNORECASE"]
- type: dependency
  name: flash-attn
- type: fact
  name: uses_torch_cuda_extension
  equals: true
```

- [ ] **Step 4: Implement deterministic evaluation with four seed rules**

Seed exact rule IDs:

- `MXR-TOOLCHAIN-001`: direct `nvcc` invocation, severity `blocker`;
- `MXR-PATH-001`: `/usr/local/cuda` hard-coded path, severity `warning`;
- `MXR-PYTORCH-001`: `CUDAExtension` use, severity `info`;
- `MXR-DEPENDENCY-001`: `flash-attn` dependency, severity `warning`.

Deduplicate on `(rule_id, relative_path, line_start, evidence)`. Sort by severity order blocker/warning/info, then path, line, and rule ID. Truncate evidence to 240 characters and HTML is escaped only at render time.

Run: `python -m pytest tests/backend/test_rule_loader.py tests/backend/test_rule_engine.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the rule engine**

```bash
git add backend/mxready/scanning/rule_loader.py backend/mxready/scanning/rule_engine.py rules tests/backend/test_rule_loader.py tests/backend/test_rule_engine.py tests/fixtures/rules
git commit -m "feat: evaluate versioned MXMACA readiness rules"
```

---

### Task 7: Scan Analyzer, Service, and Task API

**Files:**
- Create: `backend/mxready/scanning/analyzer.py`
- Create: `backend/mxready/services/__init__.py`
- Create: `backend/mxready/services/scans.py`
- Create: `backend/mxready/api/__init__.py`
- Create: `backend/mxready/api/scans.py`
- Create: `backend/mxready/api/rules.py`
- Create: `tests/backend/test_analyzer.py`
- Create: `tests/backend/test_scan_api.py`
- Modify: `tests/conftest.py`
- Modify: `backend/mxready/app.py`

**Interfaces:**
- Produces: `ScanAnalyzer(catalog).analyze(repository_root, repository_url, commit, scan_id, stage_callback) -> ScanReport`
- Produces: `ScanService(store, git_client, analyzer, settings)`
- Produces: `create_scan(repo_url: str, requested_ref: str | None) -> ScanJob`
- Produces: `run_scan(scan_id: UUID) -> None`
- Produces: API request `CreateScanRequest(repo_url: HttpUrl, ref: str | None)`
- Produces: `POST /api/scans`, `GET /api/scans/{id}`, `GET /api/scans/{id}/report`, `GET /api/rules`

- [ ] **Step 1: Write failing analyzer and API lifecycle tests**

```python
# tests/backend/test_analyzer.py
from pathlib import Path
from uuid import uuid4

from mxready.models import ScanStatus, StaticStatus
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog


def test_analyzer_builds_report_and_migration_checklist():
    stages = []
    report = ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
        Path("tests/fixtures/repositories/cuda_extension"),
        repository_url="https://github.com/example/cuda-extension",
        commit="b" * 40,
        scan_id=uuid4(),
        stage_callback=stages.append,
    )

    assert stages == [ScanStatus.INDEXING, ScanStatus.ANALYZING]
    assert report.static_status in {StaticStatus.BLOCKED, StaticStatus.WARNINGS}
    assert report.summary.total_count == len(report.findings)
    assert report.migration_checklist
```

```python
# tests/backend/test_scan_api.py
def test_create_scan_returns_202_and_job(client):
    response = client.post(
        "/api/scans",
        json={"repo_url": "https://github.com/pytorch/extension-cpp", "ref": None},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert client.get(f"/api/scans/{body['id']}").status_code == 200
```

Extend `tests/conftest.py` with an API client that replaces `ScanService.run_scan` before the request schedules it:

```python
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from mxready.app import create_app
from mxready.config import Settings


@pytest.fixture
def client(tmp_path):
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("rules/v1"),
            temp_dir=tmp_path / "tmp",
        )
    )
    with TestClient(app) as http:
        app.state.scan_service.run_scan = Mock()
        yield http
```

- [ ] **Step 2: Run focused tests and verify missing orchestration**

Run: `python -m pytest tests/backend/test_analyzer.py tests/backend/test_scan_api.py -v`

Expected: FAIL because analyzer, service, and routes do not exist.

- [ ] **Step 3: Implement analyzer and migration checklist**

`ScanAnalyzer` must:

1. call `stage_callback(ScanStatus.INDEXING)` and build the file index;
2. call `stage_callback(ScanStatus.ANALYZING)` and extract project facts;
3. evaluate the rule catalog;
4. summarize findings;
5. calculate static status;
6. produce one checklist entry per unique blocker/warning rule;
7. include index warnings in report metadata without converting them to compatibility findings.

Checklist items contain `rule_id`, `title`, `action`, `affected_files`, and `completed=False`.

- [ ] **Step 4: Implement service state transitions and API**

`run_scan` transitions exactly:

```text
queued -> cloning -> indexing -> analyzing -> completed
```

The analyzer owns both indexing and analysis and invokes the supplied callback immediately before each stage. `ScanService` passes a callback that persists the corresponding status. Any `MxReadyError` becomes a failed job with its stable code/message; unexpected exceptions become `SCAN_INTERNAL_ERROR` and are logged with scan ID.

Use FastAPI `BackgroundTasks.add_task(service.run_scan, job.id)` for MVP. Return 404 with `SCAN_NOT_FOUND` for unknown IDs. Return 409 with `SCAN_NOT_COMPLETED` when a report is requested before completion.

Wire dependencies through `app.state.scan_service` and include routers under `/api`. Add one `MxReadyError` exception handler that always returns:

```json
{
  "error": {
    "code": "SCAN_NOT_FOUND",
    "message": "The requested scan does not exist.",
    "details": {}
  }
}
```

Map invalid input to 400, not found to 404, incomplete/commit mismatch to 409, upload size to 413, and schema errors to 422.

Run: `python -m pytest tests/backend/test_analyzer.py tests/backend/test_scan_api.py -v`

Expected: PASS.

- [ ] **Step 5: Commit scan orchestration**

```bash
git add backend/mxready/scanning/analyzer.py backend/mxready/services backend/mxready/api backend/mxready/app.py tests/conftest.py tests/backend/test_analyzer.py tests/backend/test_scan_api.py
git commit -m "feat: expose asynchronous static scan workflow"
```

---

### Task 8: Markdown, JSON, and SVG Report Outputs

**Files:**
- Create: `backend/mxready/reporting/__init__.py`
- Create: `backend/mxready/reporting/markdown.py`
- Create: `backend/mxready/reporting/badge.py`
- Create: `tests/backend/test_reporting.py`
- Modify: `backend/mxready/api/scans.py`

**Interfaces:**
- Produces: `render_markdown(report: ScanReport) -> str`
- Produces: `render_badge(report: ScanReport) -> str`
- Produces: `GET /api/scans/{id}/report.md`
- Produces: `GET /api/scans/{id}/report.json`
- Produces: `GET /api/scans/{id}/badge.svg`

- [ ] **Step 1: Write failing renderer escaping and metadata tests**

```python
# tests/backend/test_reporting.py
from mxready.models import Finding, Severity
from mxready.reporting.badge import render_badge
from mxready.reporting.markdown import render_markdown


def test_reports_include_commit_and_escape_untrusted_evidence(report_factory):
    report = report_factory(
        findings=[
            Finding(
                rule_id="MXR-PATH-001",
                rule_version=1,
                severity=Severity.WARNING,
                category="path",
                title="Unsafe <title>",
                relative_path="setup.py",
                line_start=2,
                line_end=2,
                evidence="<script>alert(1)</script>",
                message="Hard-coded path",
                recommendation="Make the path configurable.",
                references=[],
            )
        ]
    )

    markdown = render_markdown(report)
    badge = render_badge(report)

    assert report.repository.commit in markdown
    assert "<script>" not in badge
    assert "warnings" in badge
```

- [ ] **Step 2: Run test and verify renderer modules are missing**

Run: `python -m pytest tests/backend/test_reporting.py -v`

Expected: FAIL importing reporting modules.

- [ ] **Step 3: Implement deterministic renderers**

Markdown sections:

1. repository and commit;
2. tool/ruleset versions and timestamps;
3. static and verification statuses;
4. blocker/warning/info counts;
5. findings grouped by severity;
6. migration checklist;
7. analysis warnings;
8. disclaimer that static scanning is not complete compatibility proof.

Escape Markdown table delimiters and HTML-sensitive evidence. Badge output is a fixed two-segment SVG with escaped labels and these colors:

```python
COLORS = {
    "static-passed": "#2e7d32",
    "warnings": "#b26a00",
    "blocked": "#b3261e",
    "verified": "#1565c0",
    "verification-stale": "#6b5e00",
    "scan-failed": "#5f6368",
}
```

- [ ] **Step 4: Add content-disposition routes and verify**

JSON output uses `report.model_dump_json(indent=2)`. Markdown and JSON routes return attachment filenames containing the repository name and first 12 commit characters. SVG is inline with `image/svg+xml` and `Cache-Control: no-store`.

Run: `python -m pytest tests/backend/test_reporting.py tests/backend/test_scan_api.py -v`

Expected: PASS.

- [ ] **Step 5: Commit report outputs**

```bash
git add backend/mxready/reporting backend/mxready/api/scans.py tests/backend/test_reporting.py
git commit -m "feat: export readiness reports and status badges"
```

---

### Task 9: Verification Schema, Bundle, and Standalone Runner

**Files:**
- Create: `schemas/verification-result-v1.json`
- Create: `backend/mxready/verification/__init__.py`
- Create: `backend/mxready/verification/bundle.py`
- Create: `runner/mxready_runner/__init__.py`
- Create: `runner/mxready_runner/__main__.py`
- Create: `runner/mxready_runner/cli.py`
- Create: `runner/mxready_runner/inspect.py`
- Create: `runner/mxready_runner/execute.py`
- Create: `runner/mxready_runner/redact.py`
- Create: `runner/mxready_runner/schema.py`
- Create: `tests/runner/conftest.py`
- Create: `tests/runner/test_inspect.py`
- Create: `tests/runner/test_execute.py`
- Create: `tests/runner/test_redact.py`
- Create: `tests/backend/test_verification_bundle.py`
- Create: `tests/fixtures/verification/mxready.yml`
- Modify: `backend/mxready/api/scans.py`

**Interfaces:**
- Produces: `build_verification_bundle(report: ScanReport) -> bytes` as ZIP
- Produces: `mxready_runner.schema.CheckResult` and `mxready_runner.schema.RunResult` standard-library dataclasses whose JSON fields match the backend contract
- Produces: `collect_environment(command_runner) -> list[CheckResult]`
- Produces: `run_manifest(manifest_path: Path, *, approve: Callable[[list[str]], bool], command_runner) -> RunResult`
- Produces: `redact_text(value: str) -> str`
- Produces: CLI `python -m mxready_runner inspect --manifest mxready.yml --output result.json`
- Produces: CLI `python -m mxready_runner run --manifest mxready.yml --output result.json`

- [ ] **Step 1: Write failing runner safety tests**

```python
# tests/runner/test_execute.py
from mxready_runner.execute import run_manifest


def test_run_refuses_commands_without_explicit_approval(manifest_path, recording_runner):
    result = run_manifest(
        manifest_path,
        approve=lambda commands: False,
        command_runner=recording_runner,
    )

    assert result.overall_status == "cancelled"
    assert recording_runner.calls == []
```

```python
# tests/runner/test_redact.py
from mxready_runner.redact import redact_text


def test_redacts_tokens_home_paths_and_usernames():
    raw = "TOKEN=secret123 /home/alice/project Authorization: Bearer abc.def"
    redacted = redact_text(raw)
    assert "secret123" not in redacted
    assert "alice" not in redacted
    assert "abc.def" not in redacted
```

```python
# tests/backend/test_verification_bundle.py
import io
import zipfile

from mxready.verification.bundle import build_verification_bundle


def test_bundle_contains_pinned_scan_identity(report_factory):
    payload = build_verification_bundle(report_factory())
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        manifest = json.loads(archive.read("mxready.yml"))
        assert manifest["repository_commit"] == "a" * 40
        assert manifest["runner_version"] == "0.1.0"
        assert "SECURITY.md" in archive.namelist()
```

- Add `import json` to this test.
- Create concrete runner fixtures:

```python
# tests/runner/conftest.py
import json
from subprocess import CompletedProcess

import pytest


class RecordingRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, command, *, timeout):
        self.calls.append(list(command))
        return CompletedProcess(command, 0, stdout="ok\n", stderr="")


@pytest.fixture
def recording_runner():
    return RecordingRunner()


@pytest.fixture
def manifest_path(tmp_path):
    path = tmp_path / "mxready.yml"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "scan_id": "00000000-0000-0000-0000-000000000000",
                "repository_url": "https://github.com/example/project",
                "repository_commit": "a" * 40,
                "runner_version": "0.1.0",
                "checks": [],
                "project_commands": [
                    {"id": "tests", "command": ["python", "-m", "pytest"], "timeout_seconds": 60}
                ],
            }
        ),
        encoding="utf-8",
    )
    return path
```

- [ ] **Step 2: Run runner and bundle tests to verify failure**

Run: `python -m pytest tests/runner tests/backend/test_verification_bundle.py -v`

Expected: FAIL because runner and verification bundle do not exist.

- [ ] **Step 3: Define the exact manifest and result contracts**

The file remains named `mxready.yml`, but its content is JSON-compatible YAML so the downloadable runner can parse it with the standard-library `json` module:

```json
{
  "schema_version": "1.0",
  "scan_id": "00000000-0000-0000-0000-000000000000",
  "repository_url": "https://github.com/example/project",
  "repository_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "runner_version": "0.1.0",
  "checks": [
    {
      "id": "python-version",
      "command": ["python", "--version"],
      "timeout_seconds": 10
    },
    {
      "id": "pytorch-device",
      "command": [
        "python",
        "-c",
        "import torch; print(torch.cuda.is_available()); print(torch.cuda.device_count())"
      ],
      "timeout_seconds": 30
    }
  ],
  "project_commands": []
}
```

The runner uses dataclasses plus explicit validators rather than Pydantic or PyYAML. It accepts only command arrays, rejects empty commands, shell control characters as standalone executables, `sudo`, package managers, redirection, and timeouts outside 1–600 seconds. It calls `subprocess.run(command, shell=False, capture_output=True, text=True, timeout=timeout_seconds)`.

The result JSON Schema requires scan ID, exact commit, runner version, start/end UTC timestamps, environment fingerprint, redacted check results, command results, and overall status in `passed`, `failed`, or `cancelled`.

- [ ] **Step 4: Implement inspect/run CLI, redaction, and ZIP bundle**

Environment inspection tries fixed safe commands in order and records “unavailable” without failing the whole run:

- `uname -a`;
- `python --version`;
- `mx-smi --version`;
- `mx-smi`;
- a Python snippet importing `torch`, printing version, CUDA availability, and device count.

Redact case-insensitive assignments for `TOKEN`, `PASSWORD`, `SECRET`, `KEY`, `AUTHORIZATION`, and home-directory username components. Truncate stdout/stderr for each command to 16 KiB.

The bundle contains the manifest, runner source package, schema, and a `SECURITY.md` that states commands are run only on the user's host after review. Add `GET /api/scans/{scan_id}/verification-bundle`; it returns the ZIP as an attachment only for completed scans.

Run: `python -m pytest tests/runner tests/backend/test_verification_bundle.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the runner**

```bash
git add schemas backend/mxready/verification backend/mxready/api/scans.py runner/mxready_runner tests/runner tests/backend/test_verification_bundle.py tests/fixtures/verification
git commit -m "feat: generate and execute manual MetaX verification bundles"
```

---

### Task 10: Verification Upload Validation and Report Freshness

**Files:**
- Create: `backend/mxready/verification/validation.py`
- Create: `tests/backend/test_verification_validation.py`
- Modify: `backend/mxready/api/scans.py`
- Modify: `backend/mxready/storage.py`
- Modify: `backend/mxready/models.py`

**Interfaces:**
- Produces: `ValidatedVerification(run: VerificationRun, status: VerificationStatus)`
- Produces: `validate_verification_upload(report: ScanReport, payload: bytes, now: datetime) -> ValidatedVerification`
- Produces: `POST /api/scans/{id}/verification-runs`
- Consumes: maximum upload size 1 MiB

- [ ] **Step 1: Write failing commit mismatch, stale, and success tests**

```python
# tests/backend/test_verification_validation.py
from datetime import UTC, datetime, timedelta
import json

import pytest

from mxready.errors import MxReadyError
from mxready.verification.validation import validate_verification_upload


def make_payload(*, scan_id, repository_commit, finished_at, overall_status="passed"):
    started_at = finished_at - timedelta(minutes=1)
    return json.dumps(
        {
            "schema_version": "1.0",
            "scan_id": str(scan_id),
            "repository_commit": repository_commit,
            "runner_version": "0.1.0",
            "environment_fingerprint": "sha256:fixture",
            "checks": [],
            "commands": [],
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "overall_status": overall_status,
        }
    ).encode()


def test_rejects_result_for_a_different_commit(report_factory):
    report = report_factory(commit="a" * 40)
    payload = make_payload(
        scan_id=report.scan_id,
        repository_commit="b" * 40,
        finished_at=datetime.now(UTC),
    )

    with pytest.raises(MxReadyError) as error:
        validate_verification_upload(report, payload, now=datetime.now(UTC))

    assert error.value.code == "VERIFICATION_COMMIT_MISMATCH"


def test_marks_result_older_than_30_days_stale(report_factory):
    now = datetime.now(UTC)
    report = report_factory()
    payload = make_payload(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=now - timedelta(days=31),
    )
    validated = validate_verification_upload(report, payload, now=now)
    assert validated.status is VerificationStatus.STALE


def test_fresh_success_is_verified(report_factory):
    now = datetime.now(UTC)
    report = report_factory()
    payload = make_payload(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=now,
    )
    validated = validate_verification_upload(report, payload, now=now)
    assert validated.status is VerificationStatus.VERIFIED
```

Add `from mxready.models import VerificationStatus` to the test.

- [ ] **Step 2: Run validation tests and verify failure**

Run: `python -m pytest tests/backend/test_verification_validation.py -v`

Expected: FAIL because upload validation does not exist.

- [ ] **Step 3: Implement strict validation**

Validation order:

1. reject payloads over 1,048,576 bytes;
2. decode UTF-8 JSON;
3. validate with Pydantic `VerificationRun(extra="forbid")`;
4. require matching scan ID;
5. require matching 40-character repository commit;
6. require runner major schema version `1`;
7. reject finish time before start time or more than 10 minutes in the future;
8. mark results older than 30 days `stale`;
9. set report verification status to `verified` only when fresh and `overall_status == "passed"`;
10. set status to `failed` for a fresh failed/cancelled run.

- [ ] **Step 4: Add upload endpoint and report recalculation**

The endpoint accepts `application/json`, reads at most 1 MiB plus one byte, validates, stores the run, updates the report, and returns the updated report. It returns 409 for commit mismatch, 413 for size, and 422 for schema errors with stable error codes.

Run: `python -m pytest tests/backend/test_verification_validation.py tests/backend/test_scan_api.py tests/backend/test_storage.py -v`

Expected: PASS.

- [ ] **Step 5: Commit verification ingestion**

```bash
git add backend/mxready/verification/validation.py backend/mxready/api/scans.py backend/mxready/storage.py backend/mxready/models.py tests/backend/test_verification_validation.py
git commit -m "feat: validate and attach hardware verification results"
```

---

### Task 11: Complete the 20-Rule MXMACA Readiness Pack

**Files:**
- Modify: `rules/v1/core.yml`
- Create: `tests/backend/test_core_rules.py`
- Create: `tests/fixtures/repositories/rule_cases/positive.py`
- Create: `tests/fixtures/repositories/rule_cases/negative.py`
- Create: `tests/fixtures/repositories/rule_cases/CMakeLists.txt`
- Create: `tests/fixtures/repositories/rule_cases/requirements.txt`

**Interfaces:**
- Consumes: rule schema and `evaluate_rules`
- Produces: exactly 20 documented MVP rules

- [ ] **Step 1: Write a failing rule inventory test**

```python
# tests/backend/test_core_rules.py
from pathlib import Path

from mxready.scanning.rule_loader import load_rule_catalog


EXPECTED_RULES = {
    "MXR-TOOLCHAIN-001",
    "MXR-PATH-001",
    "MXR-PYTORCH-001",
    "MXR-DEPENDENCY-001",
    "MXR-CMAKE-001",
    "MXR-CMAKE-002",
    "MXR-ARCH-001",
    "MXR-ARCH-002",
    "MXR-TOOL-001",
    "MXR-COMM-001",
    "MXR-DEPENDENCY-002",
    "MXR-DEPENDENCY-003",
    "MXR-DEPENDENCY-004",
    "MXR-HEADER-001",
    "MXR-HEADER-002",
    "MXR-INTRINSIC-001",
    "MXR-KERNEL-001",
    "MXR-GRAPH-001",
    "MXR-BUILD-001",
    "MXR-PYTORCH-002",
}


def test_mvp_rule_pack_has_exact_documented_inventory():
    catalog = load_rule_catalog(Path("rules/v1"))
    assert {rule.id for rule in catalog.rules} == EXPECTED_RULES
    assert all(rule.references for rule in catalog.rules)
```

- [ ] **Step 2: Run the inventory test and verify only four rules exist**

Run: `python -m pytest tests/backend/test_core_rules.py -v`

Expected: FAIL showing the missing 16 IDs.

- [ ] **Step 3: Add these exact rules and severities**

| ID | Severity | Detection |
|---|---|---|
| MXR-TOOLCHAIN-001 | blocker | direct `nvcc` process/tool invocation |
| MXR-PATH-001 | warning | hard-coded `/usr/local/cuda` |
| MXR-PYTORCH-001 | info | PyTorch `CUDAExtension` |
| MXR-DEPENDENCY-001 | warning | dependency `flash-attn` |
| MXR-CMAKE-001 | info | `enable_language(CUDA)` or CUDA in `project(NAME LANGUAGES CUDA CXX)` |
| MXR-CMAKE-002 | warning | `find_package(CUDAToolkit)` |
| MXR-ARCH-001 | warning | `-gencode` or `--generate-code` |
| MXR-ARCH-002 | warning | hard-coded `sm_[0-9]+` or `compute_[0-9]+` |
| MXR-TOOL-001 | warning | direct `nvidia-smi` invocation |
| MXR-COMM-001 | warning | NVIDIA-only `NCCL_` environment configuration |
| MXR-DEPENDENCY-002 | warning | dependency `bitsandbytes` |
| MXR-DEPENDENCY-003 | warning | dependency `xformers` |
| MXR-DEPENDENCY-004 | blocker | dependency or import `tensorrt` |
| MXR-HEADER-001 | info | include `cuda_runtime.h` |
| MXR-HEADER-002 | info | include `cuda.h` |
| MXR-INTRINSIC-001 | warning | warp intrinsic `__shfl_sync`, `__ballot_sync`, or `__activemask` |
| MXR-KERNEL-001 | warning | `__launch_bounds__` tuning assumption |
| MXR-GRAPH-001 | warning | `cudaGraph*` API use |
| MXR-BUILD-001 | warning | `TORCH_CUDA_ARCH_LIST` override |
| MXR-PYTORCH-002 | info | `torch.utils.cpp_extension.load` JIT extension |

Every rule must reference at least one primary source from:

- `https://gitee.com/metax-maca/cu-bridge`;
- `https://gitee.com/metax-maca/mxmaca-performance-tuning-guide`;
- `https://docs.pytorch.org/docs/stable/cpp_extension.html`;
- `https://cmake.org/cmake/help/latest/module/FindCUDAToolkit.html`;
- `https://docs.nvidia.com/cuda/cuda-c-programming-guide/`.

Recommendations must say “review/validate” unless public MetaX documentation proves the item blocks adaptation. Do not claim an API is unsupported based only on a pattern match.

- [ ] **Step 4: Add positive and negative fixture assertions**

Parameterize the 20 IDs. Each positive fixture must trigger its expected rule, and `negative.py` must contain benign strings such as documentation prose and variable names that do not trigger code-oriented patterns.

Run: `python -m pytest tests/backend/test_core_rules.py tests/backend/test_rule_engine.py -v`

Expected: PASS with 20 positive and 20 negative cases.

- [ ] **Step 5: Commit the complete rule pack**

```bash
git add rules/v1/core.yml tests/backend/test_core_rules.py tests/fixtures/repositories/rule_cases
git commit -m "feat: add twenty documented MXMACA readiness checks"
```

---

### Task 12: React Scan Submission and Progress Experience

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/ScanForm.tsx`
- Create: `frontend/src/components/ScanProgress.tsx`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/components/ScanForm.test.tsx`
- Create: `frontend/src/App.test.tsx`

**Interfaces:**
- Produces: `createScan(input: {repo_url: string; ref: string | null}) -> Promise<ScanJob>`
- Produces: `getScan(id: string) -> Promise<ScanJob>`
- Produces: `getReport(id: string) -> Promise<ScanReport>`
- Produces: `ScanForm({onCreated})`
- Produces: `ScanProgress({job})`

- [ ] **Step 1: Create package manifest and write failing UI tests**

`frontend/package.json`:

```json
{
  "name": "mxready-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^5.0.0",
    "jsdom": "^27.0.0",
    "typescript": "^5.9.0",
    "vite": "^7.0.0",
    "vitest": "^3.0.0"
  }
}
```

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "vite.config.ts"]
}
```

`frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    clearMocks: true,
  },
});
```

`frontend/src/test/setup.ts` contains exactly:

```ts
import "@testing-library/jest-dom/vitest";
```

```tsx
// frontend/src/components/ScanForm.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { createScan } from "../api/client";
import { ScanForm } from "./ScanForm";

vi.mock("../api/client", () => ({ createScan: vi.fn() }));
const mockedCreateScan = vi.mocked(createScan);

beforeEach(() => {
  mockedCreateScan.mockResolvedValue({
    id: "00000000-0000-0000-0000-000000000001",
    repo_url: "https://github.com/pytorch/extension-cpp",
    requested_ref: null,
    resolved_commit: null,
    status: "queued",
    stage_message: "Waiting to start",
    created_at: "2026-07-29T00:00:00Z",
    updated_at: "2026-07-29T00:00:00Z",
    failure_code: null,
    failure_message: null,
  });
});

it("submits a normalized public repository request", async () => {
  const onCreated = vi.fn();
  render(<ScanForm onCreated={onCreated} />);
  await userEvent.type(
    screen.getByLabelText("公开仓库地址"),
    "https://github.com/pytorch/extension-cpp",
  );
  await userEvent.click(screen.getByRole("button", { name: "开始体检" }));
  expect(mockedCreateScan).toHaveBeenCalledWith({
    repo_url: "https://github.com/pytorch/extension-cpp",
    ref: null,
  });
});
```

- [ ] **Step 2: Install and run frontend tests to verify missing components**

Run on Windows: `cd frontend; npm.cmd install; npm.cmd test`

Run on macOS/Linux: `cd frontend && npm install && npm test`

Expected: FAIL because `ScanForm` and `App` do not exist.

- [ ] **Step 3: Implement versioned API types and client**

Mirror backend JSON field names exactly. `request<T>` parses structured errors shaped as:

```ts
export type ApiErrorBody = {
  error: { code: string; message: string; details: Record<string, string> };
};
```

Reject non-2xx responses with an `MxReadyApiError` containing code and message. Use relative `/api` URLs. Vite development proxy forwards `/api` to `http://127.0.0.1:8000`.

- [ ] **Step 4: Implement accessible form, progress polling, and five states**

`App` state machine:

```ts
type ViewState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "scanning"; job: ScanJob }
  | { kind: "report"; report: ScanReport }
  | { kind: "error"; code: string; message: string };
```

Poll every 1,500 ms only while the job status is queued/cloning/indexing/analyzing. Stop polling on unmount, completion, or failure. Provide a “重新开始” action that returns to idle without deleting server data.

Use semantic labels, keyboard focus, visible error text, and a responsive single-column layout. Do not add router, global state library, component framework, or authentication.

Run: `cd frontend && npm test && npm run build` or Windows equivalents with `npm.cmd`.

Expected: PASS.

- [ ] **Step 5: Commit the initial frontend**

```bash
git add frontend
git commit -m "feat: add repository scan submission experience"
```

---

### Task 13: React Report, Findings, Downloads, and Verification Upload

**Files:**
- Create: `frontend/src/components/ReportView.tsx`
- Create: `frontend/src/components/FindingCard.tsx`
- Create: `frontend/src/components/VerificationPanel.tsx`
- Create: `frontend/src/test/fixtures.ts`
- Create: `frontend/src/components/ReportView.test.tsx`
- Create: `frontend/src/components/VerificationPanel.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/api/client.ts`

**Interfaces:**
- Produces: `ReportView({report})`
- Produces: `FindingCard({finding})`
- Produces: `VerificationPanel({report, onUpdated})`
- Produces: `uploadVerification(scanId: string, file: File) -> Promise<ScanReport>`
- Produces: download links for report JSON, Markdown, badge, and verification bundle

- [ ] **Step 1: Write failing report and upload tests**

Create typed fixtures shared by both component tests:

```ts
// frontend/src/test/fixtures.ts
import type { ScanReport } from "../api/types";

const base: ScanReport = {
  schema_version: "1.0",
  scan_id: "00000000-0000-0000-0000-000000000001",
  repository: {
    provider: "github",
    owner: "example",
    name: "project",
    url: "https://github.com/example/project",
    commit: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  },
  tool_version: "0.1.0",
  ruleset_version: "1",
  scanned_at: "2026-07-29T00:00:00Z",
  summary: { total_count: 0, blocker_count: 0, warning_count: 0, info_count: 0 },
  findings: [],
  migration_checklist: [],
  analysis_warnings: [],
  static_status: "passed",
  verification_status: "not-run",
};

export const staticPassedFixture: ScanReport = base;

export const blockedReportFixture: ScanReport = {
  ...base,
  summary: { total_count: 1, blocker_count: 1, warning_count: 0, info_count: 0 },
  static_status: "blocked",
  findings: [
    {
      rule_id: "MXR-TOOLCHAIN-001",
      rule_version: 1,
      severity: "blocker",
      category: "toolchain",
      title: "Direct nvcc invocation",
      relative_path: "setup.py",
      line_start: 12,
      line_end: 12,
      evidence: "compiler = 'nvcc'",
      message: "The project invokes nvcc directly.",
      recommendation: "Use a configurable compiler entry point.",
      references: [],
    },
  ],
};
```

```tsx
// frontend/src/components/ReportView.test.tsx
import { blockedReportFixture } from "../test/fixtures";
it("groups findings and shows exact code evidence", () => {
  render(<ReportView report={blockedReportFixture} />);
  expect(screen.getByText("阻塞项 1")).toBeInTheDocument();
  expect(screen.getByText("setup.py:12")).toBeInTheDocument();
  expect(screen.getByText("compiler = 'nvcc'")).toBeInTheDocument();
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});
```

```tsx
// frontend/src/components/VerificationPanel.test.tsx
import { staticPassedFixture } from "../test/fixtures";
it("explains that static pass is not hardware verification", () => {
  render(<VerificationPanel report={staticPassedFixture} onUpdated={vi.fn()} />);
  expect(screen.getByText(/尚未在沐曦 GPU 上验证/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "下载远程验证包" })).toHaveAttribute(
    "href",
    `/api/scans/${staticPassedFixture.scan_id}/verification-bundle`,
  );
});
```

- [ ] **Step 2: Run tests and verify report components are missing**

Run: `cd frontend && npm test`

Expected: FAIL importing report components.

- [ ] **Step 3: Implement report summary, filters, and finding cards**

Summary displays repository, 12-character commit, scan time, tool/ruleset versions, static status, verification status, and exact counts. Filters are `all`, `blocker`, `warning`, `info`. Finding cards show title, severity, file/line, escaped evidence in `<code>`, message, recommendation, and external references with `rel="noreferrer"`.

Render checklist items as read-only because MVP does not persist user completion state.

- [ ] **Step 4: Implement downloads and 1 MiB upload validation**

Accept one `.json` file, reject larger than 1,048,576 bytes in the browser, upload with `Content-Type: application/json`, and render server error code/message. On success, call `onUpdated` with the returned report.

Add explicit copy:

```text
静态检查只能发现已编码的迁移风险，不代表项目已经兼容 MXMACA。
只有相同提交在沐曦 GPU 上验证成功后，状态才会变为“已验证”。
```

Run: `cd frontend && npm test && npm run build`

Expected: PASS.

- [ ] **Step 5: Commit complete report UI**

```bash
git add frontend/src
git commit -m "feat: present migration findings and verification status"
```

---

### Task 14: End-to-End Offline Test, Static Frontend Serving, and CLI

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/scan_repository.py`
- Create: `tests/backend/test_end_to_end.py`
- Create: `tests/backend/test_scan_cli.py`
- Modify: `backend/mxready/app.py`
- Modify: `backend/mxready/config.py`

**Interfaces:**
- Produces: `mxready-scan <local-path> --repo-url <url> --commit <sha> --output <directory>`
- Produces: FastAPI serves `frontend/dist` for non-API routes when the directory exists

- [ ] **Step 1: Write failing offline end-to-end test**

```python
# tests/backend/test_end_to_end.py
from pathlib import Path

from fastapi.testclient import TestClient

from mxready.app import create_app
from mxready.config import Settings
from mxready.models import ScanStatus
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog


def test_fixture_scan_to_report_and_badge(tmp_path):
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("rules/v1"),
            temp_dir=tmp_path / "tmp",
        )
    )
    with TestClient(app) as client:
        store = app.state.store
        job = store.create_job("https://github.com/example/cuda-extension", None)
        report = ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
            Path("tests/fixtures/repositories/cuda_extension"),
            repository_url="https://github.com/example/cuda-extension",
            commit="c" * 40,
            scan_id=job.id,
            stage_callback=lambda status: None,
        )
        store.save_report(report)
        store.update_job(
            job.id,
            status=ScanStatus.COMPLETED,
            stage_message="Scan complete",
            resolved_commit="c" * 40,
        )

        markdown = client.get(f"/api/scans/{report.scan_id}/report.md")
        badge = client.get(f"/api/scans/{report.scan_id}/badge.svg")

    assert report.summary.total_count > 0
    assert markdown.status_code == 200
    assert badge.status_code == 200
    assert badge.headers["content-type"].startswith("image/svg+xml")
```

- [ ] **Step 2: Run the test and verify no offline seam exists**

Run: `python -m pytest tests/backend/test_end_to_end.py tests/backend/test_scan_cli.py -v`

Expected: FAIL because the CLI and final application assembly do not exist.

- [ ] **Step 3: Add an explicit local-directory analyzer seam and CLI**

The CLI accepts a local directory only for developer/report generation use; the public Web API still rejects local paths. It calls `ScanAnalyzer` directly and writes:

- `<name>-<commit12>.json`;
- `<name>-<commit12>.md`;
- `<name>-<commit12>.svg`.

It exits 0 for passed/warnings, 2 for blockers, and 1 for operational failure.

- [ ] **Step 4: Serve the built frontend without shadowing `/api`**

Add `frontend_dist: Path = Path("frontend/dist")` to settings. After API routes, mount immutable assets and register an SPA fallback that returns `index.html` only for non-API GET paths. When `frontend/dist/index.html` is absent, leave API-only mode active.

Run:

```text
python -m pytest -v
python -m ruff check backend runner scripts tests
cd frontend && npm test && npm run build
```

Expected: all commands PASS.

- [ ] **Step 5: Commit end-to-end assembly**

```bash
git add scripts backend/mxready/app.py backend/mxready/config.py tests/backend/test_end_to_end.py tests/backend/test_scan_cli.py
git commit -m "feat: assemble offline end-to-end MXReady workflow"
```

---

### Task 15: Security Regression Tests, CI, License, and Contributor Documentation

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `LICENSE`
- Create: `README.md`
- Create: `CONTRIBUTING.md`
- Create: `docs/rules.md`
- Create: `docs/runner.md`
- Create: `docs/security.md`
- Create: `tests/backend/test_security_boundaries.py`

**Interfaces:**
- Produces: documented local setup, test, scan, rule contribution, and runner workflows
- Produces: CI gates for backend, runner, frontend, and build

- [ ] **Step 1: Write failing security regression tests**

```python
# tests/backend/test_security_boundaries.py
from pathlib import Path

from mxready.models import ScanStatus
from mxready.reporting.badge import render_badge
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog


def test_repository_source_is_never_executed(tmp_path):
    root = tmp_path / "repository"
    root.mkdir()
    marker = root / "EXECUTED"
    (root / "setup.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
    )
    ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
        root,
        repository_url="https://github.com/example/hostile",
        commit="d" * 40,
        scan_id=uuid4(),
        stage_callback=lambda status: None,
    )
    assert not marker.exists()


def test_svg_escapes_repository_and_finding_text(report_factory):
    report = report_factory(repository_name="<script>alert(1)</script>")
    svg = render_badge(report)
    assert "<script>" not in svg


def test_verification_upload_rejects_extra_fields(client, report_factory):
    store = client.app.state.store
    job = store.create_job("https://github.com/example/project", None)
    report = report_factory(scan_id=job.id)
    store.save_report(report)
    store.update_job(
        job.id,
        status=ScanStatus.COMPLETED,
        stage_message="Scan complete",
        resolved_commit=report.repository.commit,
    )
    response = client.post(
        f"/api/scans/{job.id}/verification-runs",
        content=b'{"schema_version":"1.0","unexpected":"value"}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
```

- Add `from uuid import uuid4` to the test imports.

- [ ] **Step 2: Run security tests and fix any exposed boundary**

Run: `python -m pytest tests/backend/test_security_boundaries.py -v`

Expected: PASS if all earlier trust-boundary work is correct. If a regression test fails, apply only the minimal boundary fix and rerun it before proceeding.

- [ ] **Step 3: Add CI with exact commands**

Create this complete workflow:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: python -m pip install -e ".[dev]"
      - run: python -m ruff check backend runner scripts tests
      - run: >-
          python -m pytest
          --cov=mxready
          --cov=mxready_runner
          --cov-report=term-missing
          --cov-fail-under=80

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm test
      - run: npm run build
```

Use Python 3.11 and Node 22 on Ubuntu. Require at least 80% Python line coverage using `--cov-fail-under=80`.

- [ ] **Step 4: Write operational and contribution documentation**

README must contain:

- problem statement and non-goals;
- architecture summary;
- Windows PowerShell and Linux setup;
- `uvicorn mxready.app:create_app --factory --reload`;
- frontend development command;
- offline fixture scan command;
- report status meanings;
- security warning for runner commands;
- project roadmap limited to approved MVP.

`docs/rules.md` documents every YAML field, all three pattern types, evidence limits, positive/negative test requirements, and primary-source reference policy.

`docs/runner.md` documents inspect/run separation, command review, JSON output, redaction, and upload.

`docs/security.md` documents the trust boundary, fixed repository allowlist, clone limits, non-execution guarantee, disclosure instructions, and the local/controlled-deployment assumption.

Use the canonical Apache License 2.0 text in `LICENSE`. `CONTRIBUTING.md` requires tests and source references for new rules.

- [ ] **Step 5: Run the full quality gate and commit**

Run:

```text
python -m ruff check backend runner scripts tests
python -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80
cd frontend && npm test && npm run build
```

Expected: all commands PASS and coverage is at least 80%.

```bash
git add .github LICENSE README.md CONTRIBUTING.md docs .gitignore tests/backend/test_security_boundaries.py
git commit -m "docs: complete MXReady contributor and security baseline"
```

---

### Task 16: Three Public Project Reports and MetaX Validation Handoff

**Files:**
- Create: `examples/reports/pytorch-extension-cpp.json`
- Create: `examples/reports/pytorch-extension-cpp.md`
- Create: `examples/reports/apex.json`
- Create: `examples/reports/apex.md`
- Create: `examples/reports/flash-attention.json`
- Create: `examples/reports/flash-attention.md`
- Create after hardware access: `examples/verification/metax-verification-redacted.json`
- Create: `docs/application-evidence.md`

**Interfaces:**
- Consumes: running API/CLI and fixed public repository URLs
- Produces: reproducible evidence package for the seed-plan application

- [ ] **Step 1: Run the full local verification gate before external scans**

Run:

```text
python -m ruff check backend runner scripts tests
python -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80
cd frontend && npm test && npm run build
```

Expected: all commands PASS.

- [ ] **Step 2: Scan the three fixed candidate repositories**

Use:

```text
https://github.com/pytorch/extension-cpp
https://github.com/NVIDIA/apex
https://github.com/Dao-AILab/flash-attention
```

For each repository:

1. record the resolved 40-character commit;
2. save JSON and Markdown output under `examples/reports`;
3. manually inspect every blocker for false positives;
4. fix rule precision with a failing fixture test before changing a pattern;
5. rerun all rule tests after each precision fix.

If one repository exceeds an approved hard limit, retain the failed scan record in `docs/application-evidence.md` and replace only that candidate with `https://github.com/pytorch/pytorch3d`; do not relax safety limits.

- [ ] **Step 3: Prepare the MetaX verification package**

Choose the smallest project that:

- has no unresolved blocker after human review;
- has a documented test command under 10 minutes;
- does not require downloading model weights;
- can run on one MetaX GPU.

Generate its verification ZIP, list exact commands in `docs/application-evidence.md`, and request remote MetaX access. Do not fabricate a verification result while access is unavailable.

- [ ] **Step 4: Perform the authorized hardware checkpoint**

On an authorized MetaX server:

```text
python -m mxready_runner inspect --manifest mxready.yml --output inspect.json
python -m mxready_runner run --manifest mxready.yml --output result.json
```

Review `result.json` for hostnames, usernames, tokens, absolute home paths, and unrelated environment data. Upload it through MXReady, export the updated report, and save only the redacted result as `examples/verification/metax-verification-redacted.json`.

This step requires real remote hardware access and is the only implementation-plan checkpoint that cannot be completed with local fixtures.

- [ ] **Step 5: Prepare, but do not submit, an upstream contribution**

Select one actionable finding, create a minimal tested patch in a fork or separate worktree, and write the proposed title/body in `docs/application-evidence.md`. External PR submission requires separate explicit user approval.

- [ ] **Step 6: Commit application evidence**

Run: `git diff --check`

Expected: no whitespace errors.

```bash
git add examples docs/application-evidence.md
git commit -m "docs: add reproducible MXReady application evidence"
```

---

## Final Verification

After all locally executable tasks:

```text
python -m ruff check backend runner scripts tests
python -m pytest --cov=mxready --cov=mxready_runner --cov-report=term-missing --cov-fail-under=80
cd frontend && npm test && npm run build
git status --short
```

Expected:

- Ruff exits 0;
- all Python tests pass;
- Python coverage is at least 80%;
- all frontend tests pass;
- the production frontend build succeeds;
- the worktree contains no unintended changes;
- the Web service has never executed a scanned repository;
- static-only reports never claim `verified`;
- the final hardware criterion remains visibly pending until an authentic MetaX result is available.
