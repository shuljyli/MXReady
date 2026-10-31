# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.3.0-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

[中文](README.md) | **English** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

You have PyTorch code running on NVIDIA GPUs and you want to move it to a MetaX GPU. You do not
know yet what will break.

MXReady reads the code without running it, and lists the places likely to cause trouble: where it
calls NVIDIA's compiler directly, where it assumes 32 threads to a group (MetaX uses 64), where it
inlines NVIDIA-only assembly, where it depends on something that does not exist on the new card.
Every finding tells you which file, which line, why it matters, and what to change.

It does not rewrite your code, and it does not produce a "compatibility percentage" — the number of
rules a project hits says nothing about whether it will work. A clean static check only means
nothing obvious was found; the real answer comes from running the same commit on a MetaX machine.

> MXReady is a community prototype, not an official MetaX compatibility certification. A passing
> static check does **not** mean a project already works on MXMACA; the final answer still has to come
> from running the same commit on a controlled MetaX GPU.

## What it does

- Accepts public HTTPS repositories on GitHub and Gitee, optionally at a branch, tag or 40-character commit;
- Indexes Python, C/C++, CUDA, CMake, Shell, TOML and YAML text files;
- Ships **35 rules** (`MXR-*`); every finding carries file path, line numbers, the matched snippet,
  a recommendation and a primary-source reference;
- Exports JSON, Markdown, an SVG badge and a standard-library-only remote verification bundle;
- Keeps the static status strictly separate from the hardware verification status;
- Provides a read-only CLI for local directories, useful for offline regression and example reports;
- Optional `mxready-mcp`: exposes scanning, reports and rule lookup as four Model Context Protocol
  tools for coding agents;
- Packages the React single-page UI and the FastAPI service as one deployable unit.

Out of scope for this release: private repositories, automatic source rewriting, remote GPU
orchestration, cloud GPU scheduling, user accounts, and any percentage "compatibility score".

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

## Install

Release bundles need no Node.js, no PyTorch and no GPU driver. All platforms require
**Python 3.11+ (with pip/venv) and Git**; the installer downloads Python dependencies on first run.

| Platform | Artifact | After extracting, run |
| --- | --- | --- |
| Windows 10/11 | `mxready-0.3.0-windows.zip` | PowerShell: `.\install.ps1`, then `.\start.ps1` |
| Linux | `mxready-0.3.0-linux.zip` | `bash install.sh`, then `bash start.sh` |
| macOS (Apple Silicon / Intel) | `mxready-0.3.0-macos.zip` | `bash install.sh`, then `bash start.sh` |
| Existing Python environment | `mxready-0.3.0-py3-none-any.whl` | in a dedicated venv: `python -m pip install <wheel>`, then `mxready-serve` |

Open <http://127.0.0.1:8000> after starting; press `Ctrl+C` in the terminal to stop.
The installer creates a `.venv/` next to itself and keeps the database in the OS user-data
directory, so replacing the program preserves earlier reports.

The ZIPs are Python application bundles: they do not embed Python or Git, and they are not native
EXE/DMG packages or system package-manager installers. See [docs/installation.md](docs/installation.md)
(in Chinese) for offline preparation, checksum verification, upgrades and uninstall.

## Development

Requirements: Python 3.11+, Git, and Node.js 22+ (only for development and building the UI).

```bash
make install          # .venv + pip install -e ".[dev]" + npm ci
bash scripts/dev.sh   # FastAPI on :8000 and Vite on :5173
```

On Windows use `.\scripts\make.ps1 install` and `.\scripts\dev.ps1`.

### Quality gate

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

CI runs the gate on Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS, plus `pip-audit`, a Docker
build-and-serve check, shell syntax checks and the frontend suite. Branch coverage is currently
90% against an 80% threshold.

### Rule engine benchmark

```bash
python scripts/bench_prefilter.py --repeat 5 --output bench.json
```

Reports per-rule regex cost versus literal-prefilter cost, and asserts that enabling or disabling the
prefilter yields an identical finding set. The output has no timestamps so two runs can be diffed.

## Feature matrix

| Capability | Status | How it is verified |
| --- | --- | --- |
| Static scan of public repositories | Available | End-to-end tests + example reports |
| 35 `MXR-*` rules | Available | Each rule has a positive and a similar negative fixture |
| Report output: JSON / Markdown / SVG badge | Available | Contract tests + `generate_contracts.py --check` |
| Verification bundle and stdlib-only runner | Available | Installer regression + security boundary tests |
| Windows / Linux / macOS installers and UI wheel | Available | Release workflow installs and starts on all three OSes |
| React single-page UI | Available | Vitest + TypeScript strict mode |
| Batch assessment (`mxready-scan-batch`) | Available | CLI regression |
| Real MetaX GPU verification | Designed, not yet run on hardware | Report `verification_status` stays `not-run` |

## Known limitations

- **No compatibility verdict.** Every output stops at a static risk signal. A statement such as
  "verified on MetaX" requires a `verified` result for the same commit, produced on a controlled
  MetaX GPU, no older than 30 days.
- **Rule precision has not been calibrated on real projects.** The 35 rules are exercised by
  controlled fixtures; false-positive rates on public CUDA extensions still need measurement.
- **Verification results expire after 30 days** and turn into `stale`, requiring a re-run.
- **Release scope**: no private repositories, no automatic source rewriting, no cloud GPU scheduling,
  no user accounts, no percentage compatibility score.
- **Environment**: bundles ship without Python and Git. Docker image build and startup are covered by CI.
- **No ESLint / Prettier in the frontend**; TypeScript strict mode and Vitest are the safety net.
- **Detailed documentation is currently written in Chinese**; commands and code samples are
  language-neutral, so they can be followed directly.

## Documentation

| Document | Content |
| --- | --- |
| [docs/index.md](docs/index.md) | Documentation index |
| [docs/architecture.md](docs/architecture.md) | Layering, dependency directions, task lifecycle, package resources |
| [docs/deployment.md](docs/deployment.md) | Production deployment: bare metal / systemd / Docker / nginx / backup / logging |
| [docs/api.md](docs/api.md) | HTTP API manual with `curl` examples |
| [docs/installation.md](docs/installation.md) | Installers, offline setup, upgrade and release build |
| [docs/security.md](docs/security.md) | Security model |
| [docs/rules.md](docs/rules.md) | Rule authoring guide |
| [docs/runner.md](docs/runner.md) | Remote verification runner guide |
| [examples/verification/README.md](examples/verification/README.md) | On-hardware verification handover SOP |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution flow and quality gate |

## Security boundaries

- Only public HTTPS repositories on `github.com` and `gitee.com` (`MXREADY_ALLOWED_HOSTS` can be
  extended, URL normalisation and no-credential / no-private-address checks stay in place);
- Git never reads credentials, never prompts for login, never fetches LFS objects and never
  initialises submodules;
- Git fetch times out after 60 seconds; a checked-out work tree is capped at 50 MiB and 10,000 files,
  and the archive fallback applies the same caps during download and extraction;
- A single indexed text file is capped at 1 MiB, and symbolic links are never followed;
- Web scans never execute repository code;
- Verification results are capped at 1 MiB, use a strictly versioned model and are bound to the scan commit;
- The runner never uses `sudo`, never installs software and never modifies drivers; commands run as
  argument arrays with `shell=False`;
- Enable `MXREADY_RATE_LIMIT_ENABLED` and the request-body limit before exposing a deployment publicly.

## Roadmap

1. Generate reproducible reports on three public CUDA extension projects and calibrate rule precision;
2. Obtain a MetaX remote server and complete at least one redacted verification of the same commit;
3. Submit a small, reviewable migration pull request upstream;
4. Extend the rule set and the minimal verification template based on real adaptation feedback.

## License

[Apache License 2.0](LICENSE).
