# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

[中文](README.md) | **English** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

You have PyTorch code running on NVIDIA GPUs and you want to move it to a MetaX GPU. You do not
know yet what will break.

MXReady reads the code first (read-only, without running it) and lists the places likely to cause
trouble: where it calls NVIDIA's compiler directly, where it hard-codes "32 threads to a group"
(MetaX uses 64), where it inlines NVIDIA-only assembly, where it depends on libraries that will not
run. Every finding tells you which file, which line, why it matters, and what to change.

It does not rewrite your code, and it does not produce a "compatibility percentage" — the number of
rules a project hits says nothing about the probability of compatibility. A clean static check only
means nothing obvious was found; the real answer comes from running it on a MetaX machine.

> MXReady is a community prototype, not an official MetaX compatibility certification. A passing
> static check does **not** mean a project already works on MXMACA; the final answer still has to
> come from running the same commit in a controlled MetaX GPU environment.

## What it does

- Accepts public HTTPS repositories on GitHub and Gitee, optionally at a branch, tag or
  40-character commit;
- Scans Python, C/C++, CUDA, CMake, Shell, TOML, YAML and other text files;
- Ships **35 rules** (`MXR-*`); every finding carries file path, line numbers, the matched snippet,
  a recommendation and a primary-source reference;
- Hits in tests, examples and documentation only count as hints: they still appear in the report,
  but they do not get the whole project judged as blocked;
- Outputs JSON, Markdown, an SVG badge and a printable HTML report (print to PDF from the browser),
  plus a standard-library-only remote verification bundle;
- Keeps the static conclusions strictly separate from the hardware verification conclusions;
- Provides a read-only CLI for local directories, useful for offline regression and example reports;
- Optional `mxready-mcp`: exposes scanning, task status, reports and rule lookup as 5 Model Context
  Protocol tools for coding agents;
- Packages the React single-page UI and the FastAPI service as one deployable unit.

The web UI provides "Source Health Check", "Batch Scan", "Scan History", "Migration Progress",
"Rule Library", "MCP Access" and "CLI Usage" pages; reports support priority-file navigation,
paginated search, comparison and sharing, a manual review checklist and HTML print export. MCP and
Web must explicitly share the same local data directory to read each other's reports.

The MVP does not include private repositories, automatic source rewriting, Docker orchestration of
remote GPU servers, cloud GPU scheduling, user accounts, or a percentage "compatibility score".

## What it found on real projects

Health check of [`NVIDIA/apex`](https://github.com/NVIDIA/apex) at commit
`575968bc1f9127ccd61003a681472a83af4ff1a1`: **12 blocked · 65 warnings · 140 hints**. The full
report is in [examples/reports/nvidia-apex.md](examples/reports/nvidia-apex.md).

The four most representative of the 12 blockers:

| Location | Match | Why it breaks on MetaX |
| --- | --- | --- |
| `csrc/welford.cu:36` | `#define WARP_SIZE 32` | Warp width hard-coded to 32; MetaX uses 64 |
| `nhwc_batch_norm_kernel.h:1245` | `int lane_id = threadIdx.x & 31;` | lane 0 and lane 32 get computed as the same lane |
| `group_norm_nhwc.h:40` | `asm volatile("red.release.gpu.global.add.s32 …")` | Inline PTX binds the code to the NVIDIA backend |
| `setup.py:65` | `subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"])` | Calls `nvcc` directly to probe the version; that command does not exist in a MetaX environment |

Two of the four **compile successfully**, but the lane arithmetic and warp width produce wrong
results on 64-wide waves, and tests may not cover it; the other two simply fail to compile on MetaX.
Both kinds of problem can stretch a migration by weeks.

Two more pinned-commit cases fill in the evidence on both sides of the blocker-diagnosis and fix
loop:

- [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes) (`a616886`): 27
  findings, 7 blockers; report at
  [examples/reports/bitsandbytes.md](examples/reports/bitsandbytes.md).
- [`causal-conv1d`](https://github.com/Dao-AILab/causal-conv1d) (`cd81f04`): after fixing according
  to the report the finding count dropped, and on-hardware verification on a MetaX C500 came back
  all `passed`; see the [migration case notes](docs/migration-case-2026-11.md).

## Architecture

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── SQLite-backed task queue and reports
   │
   ├─ atomic claim / lease heartbeat ── restricted git fetch ── read-only file index ── YAML rule engine
   ├─ JSON / Markdown / SVG reports
   └─ verification ZIP ◀── runs on your own MetaX host ── result.json
```

The web service never imports, installs, builds or executes code from the scanned repository. The
remote runner only runs on a machine you control and requires explicit confirmation before any
project command is executed.

Python code lives uniformly under `src/`; default rules and the verification schema ship with the
installed package. Directory conventions, the task queue and upgrade notes are covered in the
[architecture guide](docs/architecture.md). After changing the models, run `make contracts` to
regenerate the interface contracts.

## Feature matrix

| Capability | Status | How it is verified |
| --- | --- | --- |
| Static scan of public repositories (GitHub / Gitee, optionally at a branch, tag or 40-character commit) | Available | End-to-end tests + example reports |
| 35 `MXR-*` rules | Available | Each rule has a positive and a similar negative fixture |
| Report output: JSON / Markdown / HTML / SVG badge | Available | Contract tests + `generate_contracts.py --check` |
| Migration progress dashboard (cross-repository aggregation, blocker trends) | Available | Backend aggregation tests + Vitest |
| Verification bundle and stdlib-only runner | Available | Installer regression + security boundary tests |
| Install ZIPs for all three platforms and UI-enabled wheel/sdist | Available | The release workflow actually installs and starts on Windows / Linux / macOS |
| React single-page UI | Available | Vitest + TypeScript strict mode |
| Batch assessment (`mxready-scan-batch`) | Available | CLI regression |
| MCP tools (`mxready-mcp`, requires `.[mcp]`) | Available | Backend tests and a real stdio handshake |
| Real MetaX GPU verification | Two redacted runs completed (MetaX C500: `pytorch/extension-cpp` @ `1c325b2`, `causal-conv1d` @ `cd81f04`) | All five runner `inspect` environment checks and the single-GPU smoke all `passed`; the causal-conv1d build used a temporary patch that was not submitted upstream, and every other project still needs its own run |

Engineering status: `ruff`, `mypy`, contract checks and `pytest` are all green (540+ test cases, 90%
branch coverage); CI covers Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS, plus a Python 3.10
runner job.

## Known limitations

- **No compatibility verdict.** Every output stops at static risk signals and manual-review
  recommendations; a statement such as "verified in a MetaX environment" must be bound to a specific
  commit, produced as a `verified` result on a controlled MetaX GPU, and no older than 30 days.
- **Rule precision has not been statistically calibrated on large numbers of real projects.** The
  positive and negative cases come from controlled fixtures and were re-checked on public
  repositories (0 false positives); systematic false-positive and false-negative rates still need
  statistics from more real projects, see the [rules guide](docs/rules.md).
- **Verification results are valid for 30 days**; once expired, the report status turns into `stale`
  and the result must be uploaded again.
- **MVP scope**: no private repositories, no automatic source rewriting, no cloud GPU scheduling, no
  user accounts, no percentage compatibility score.

> Example reports for public projects are in [examples/reports](examples/reports):
> `pytorch-extension-cpp` passes everything (4 hints), `nvidia-apex` (12 blockers) and
> `bitsandbytes` (7 blockers) are in a blocked state, and `causal-conv1d` keeps both the pre-fix and
> post-fix reports. They sit side by side to show that reports really do go green, and really do go
> red. The remote verification flow is described in
> [examples/verification/README.md](examples/verification/README.md).

## Installation and startup

Regular users can just install the UI-enabled release bundle: no Node.js, no PyTorch and no GPU
driver needed. All three platforms require **Python 3.11+ (with pip/venv) and Git** to be
pre-installed; the first install downloads Python dependencies from the network by default.

| Platform | Artifact | After extracting, run in the bundle directory |
| --- | --- | --- |
| Windows 10/11 | `mxready-1.0.1-windows.zip` | PowerShell: `.\install.ps1`, then `.\start.ps1` |
| Linux | `mxready-1.0.1-linux.zip` | `bash install.sh`, then `bash start.sh` |
| macOS (Apple Silicon / Intel) | `mxready-1.0.1-macos.zip` | `bash install.sh`, then `bash start.sh` |
| Managed Python environment | `mxready` on PyPI | `python -m pip install mxready`, then `mxready-serve` |
| Existing Python environment | `mxready-1.0.1-py3-none-any.whl` | in a dedicated venv: `python -m pip install <wheel path>`, then `mxready-serve` |

After starting, open <http://127.0.0.1:8000>; press `Ctrl+C` in the terminal to stop the service.
The ZIPs are Python application bundles: they do not bundle Python or Git, and they are not native
EXE/DMG packages or system package-manager installers. Published artifacts are on
[GitHub Releases](https://github.com/shuljyli/MXReady/releases); offline preparation, checksum
verification, upgrade, uninstall and Windows troubleshooting are covered in the
[installation and release notes](docs/installation.md) (in Chinese).

Maintainers building release bundles: install the development dependencies, then run `make release`
(Windows: `.\scripts\make.ps1 release`); artifacts land in the git-ignored `dist/`. Server
deployment (bare metal / systemd / Docker / nginx) and the `MXREADY_*` configuration options are
covered in the [deployment guide](docs/deployment.md) and [.env.example](.env.example).

### Development from source

Requirements: Python 3.11+, Git, and Node.js 22+ (only needed when developing/building the
frontend).

```bash
make install                # create .venv, install dev dependencies, npm ci (Windows: .\scripts\make.ps1 install)
bash ./scripts/dev.sh       # start frontend and backend in one step (Windows: .\scripts\dev.ps1)
```

`dev.sh` / `dev.ps1` start the frontend <http://localhost:5173> (`/api` proxied to the backend) and
the backend <http://127.0.0.1:8000> (`--reload` hot reload) at the same time. Use port 5173 in
development mode; the backend serves the full UI when `frontend/dist` already exists, the API docs
live at `/docs`, and the Chinese API manual is at [docs/api.md](docs/api.md).

Unified command entry points (`install` / `dev` / `frontend` / `test` / `lint` / `typecheck` /
`build` / `release` / `clean`):

| Task | Windows (PowerShell) | Linux / macOS | What it does |
| --- | --- | --- | --- |
| Install dependencies | `.\scripts\make.ps1 install` | `make install` | venv + backend dependencies + `npm ci` |
| Start the backend | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`, port 8000 |
| Start the frontend | `.\scripts\make.ps1 frontend` | `make frontend` | Vite dev, port 5173 |
| Run tests | `.\scripts\make.ps1 test` | `make test` | backend pytest (with coverage gate) |
| Lint | `.\scripts\make.ps1 lint` | `make lint` | ruff over src / scripts / tests / packaging |
| Type-check | `.\scripts\make.ps1 typecheck` | `make typecheck` | mypy over src / scripts |
| Build the frontend | `.\scripts\make.ps1 build` | `make build` | `npm run build` produces `frontend/dist` |
| Build release bundles | `.\scripts\make.ps1 release` | `make release` | UI + wheel/sdist + three-platform ZIPs into `dist/` |
| Clean | `.\scripts\make.ps1 clean` | `make clean` | removes `.pytest-temp` |

## Command-line tools

Detailed usage and exit-code conventions for `mxready-scan` (local directories),
`mxready-scan-public` (public repository evidence), `mxready-build-bundle` (verification bundle),
`mxready-scan-batch` (batch assessment) and `mxready-mcp` (for coding agents) are in the
[CLI guide](docs/cli.md). All CLIs analyze read-only and never execute scanned code.

## Status meanings

| Status | Meaning |
| --- | --- |
| `passed` | No blockers or warnings matched; on-hardware verification still required |
| `warnings` | Migration risks that need manual review |
| `blocked` | Blockers that should be handled before requesting remote compute |
| `not-run` | No MetaX-environment verification result has been uploaded yet |
| `verified` | `mx-smi` and the PyTorch device check passed for the same commit, all environment checks succeeded and the result is no older than 30 days; this is not the same as full project certification |
| `failed` | The verification command failed |
| `stale` | The verification result is older than 30 days and needs a re-run |

Reports deliberately do not provide a percentage compatibility score, because the number of rule
hits cannot represent a project's probability of compatibility.

## Testing

```bash
python -m ruff check src scripts tests packaging
python -m ruff format --check src scripts tests packaging
python -m mypy
python scripts/generate_contracts.py --check
python -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80

cd frontend
npm test
npm run build
```

Load-testing scripts (locust, with a local mock Git and no dependency on the public internet) are in
[tests/load/](tests/load/).

## Documentation

| Document | Content |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Directory layout, dependency directions, task lifecycle and package resource conventions |
| [docs/deployment.md](docs/deployment.md) | Production deployment: bare metal / systemd / Docker / nginx / backup / logging / configuration options |
| [docs/api.md](docs/api.md) | Chinese API manual (with `curl` examples) |
| [docs/cli.md](docs/cli.md) | Detailed CLI and MCP usage |
| [docs/installation.md](docs/installation.md) | Three-platform installers, offline preparation, upgrade, release build and Windows troubleshooting |
| [docs/report-workflow.md](docs/report-workflow.md) | Full findings, scan scope, report comparison, SARIF and CI integration |
| [docs/security.md](docs/security.md) | Security model |
| [docs/rules.md](docs/rules.md) | Rule authoring guide |
| [docs/runner.md](docs/runner.md) | Remote verification runner guide |
| [docs/migration-case-2026-11.md](docs/migration-case-2026-11.md) | Real-repository cases: blocker diagnosis, fix and on-hardware re-verification |
| [examples/verification/README.md](examples/verification/README.md) | On-hardware verification handover SOP |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution flow and quality gate |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community code of conduct |

## Security boundaries

- Only public HTTPS repositories on `github.com` and `gitee.com` are allowed; Git never reads
  credentials, never downloads LFS objects and never initialises submodules, and fetches have
  timeouts and size/entry caps;
- Web scans never execute repository code; verification results are capped at 1 MiB and bound to
  the scanned commit;
- The runner never uses `sudo` and never installs software; commands run with `shell=False`, and
  project commands require manual confirmation before execution;
- Enable rate limiting and a request-body size limit before exposing a deployment publicly.

Before deploying, read the [security model](docs/security.md) and the [runner guide](docs/runner.md)
in full.

## Contributing

New rules must include positive cases, similar negative cases and primary technical references.
Please read:

- [Contribution guide](CONTRIBUTING.md)
- [Rule authoring guide](docs/rules.md)
- [Remote verification guide](docs/runner.md)
- [Security model](docs/security.md)

## MVP roadmap

1. Generate reproducible reports on three public CUDA extension projects and calibrate rule
   precision;
2. Complete redacted on-hardware verification for more public projects at the same commits (done for
   `pytorch/extension-cpp` @ `1c325b2` and `causal-conv1d` @ `cd81f04`);
3. Submit a small, reviewable migration PR to one upstream project;
4. Extend the rule set and the minimal verification template based on real adaptation feedback.

## Main contributors

- **shuli-黍黎** — project initiator and lead developer.

## License

This project is licensed under the [Apache License 2.0](LICENSE). You are welcome to use, modify and
distribute it under the terms of the license.

## Contact

Questions, suggestions and collaboration are welcome — open a GitHub Issue, or contact us by email:

- shuli_ljy@outlook.com
- 2199553510@qq.com
