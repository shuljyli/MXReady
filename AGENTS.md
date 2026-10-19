# Repository Guidelines

## Project Structure & Module Organization

MXReady statically assesses PyTorch CUDA extensions for migration to MetaX MXMACA.

- `src/mxready/`: FastAPI endpoints, domain models, scanning, reporting, and CLI entry points.
- `src/mxready_runner/`: user-controlled hardware verification CLI.
- `frontend/src/`: React/TypeScript components, API client, styles, and colocated tests; builds to `frontend/dist/`.
- `src/mxready/resources/rules/v1/` and `src/mxready/resources/schemas/`: versioned YAML rules and verification-result schema.
- `tests/backend/`, `tests/runner/`, and `tests/fixtures/`: Python tests and minimal repository fixtures; `tests/load/` contains Locust scenarios.
- `src/mxready/persistence/`: SQLite storage, migrations, and task leases.
- `scripts/`: development/operations entry points and contract generation; production CLI modules live in `src/mxready/cli/`.
- `tests/integration/`: sdist/wheel and installation-independent smoke tests.
- `frontend/src/hooks/`: scan lifecycle, URL restoration, cancellation, and bounded polling retries.
- `docs/` and `examples/`: architecture/reference documentation and pinned evidence.

## Build, Test, and Development Commands

Use Python 3.11+, Node.js 22+, and Git. Run from the repository root:

- `make install`: create `.venv`, install Python development dependencies, and run `npm ci`.
- `bash scripts/dev.sh`: launch FastAPI on port 8000 and Vite on 5173.
- `make dev` / `make frontend`: launch either service separately.
- `make lint`: run Ruff; `make typecheck`: run mypy for the host and Windows; PowerShell also checks the Linux target.
- `make contracts`: regenerate TypeScript response types and verification JSON Schema; CI runs `python scripts/generate_contracts.py --check`.
- `make test`: run pytest with coverage reporting and an 80% minimum.
- `cd frontend && npm test`: run Vitest.
- `cd frontend && npm run typecheck`: check TypeScript.
- `make build`: type-check and build the frontend.

Windows equivalents use `.\scripts\make.ps1 <target>` and `.\scripts\dev.ps1`.

## Coding Style & Naming Conventions

Use four-space Python indentation, type annotations, snake_case functions/modules, and PascalCase classes. Ruff targets Python 3.11 with a 100-character line limit and import sorting. Match existing TypeScript: two-space indentation, double quotes, semicolons, PascalCase components, and camelCase functions. TypeScript strict mode is enabled; no frontend formatter or linter is configured.

## Testing Guidelines

Use pytest/pytest-cov for Python (`test_*.py`) and Vitest with React Testing Library/jsdom for frontend (`*.test.ts`, `*.test.tsx`). Add failing regression tests before fixes. New `MXR-<category>-<three-digit-number>` rules require positive and similar negative fixtures, false-positive analysis, and a primary-source reference. Add security regressions for boundary changes; cover accessible names, keyboard behavior, and responsive UI changes.

## Commit & Pull Request Guidelines

Use short conventional subjects: `feat:`, `fix:`, `docs:`, `test:`, or `chore:`; scopes are optional. Branch from current `main`. Follow `.github/pull_request_template.md`: explain the problem, evidence, linked issue, actual validation results, and contract changes. Update `CHANGELOG.md` for user-visible changes.

## Security & Agent Instructions

Never execute scanned repository code in the Web service. Preserve runner confirmation, command allowlists, `shell=False`, timeouts, redaction, and output limits. Keep static findings separate from hardware verification; never introduce percentage compatibility scores. See `CONTRIBUTING.md` and `docs/security.md`. Synchronize `AGENTS.md` and `CLAUDE.md` when both exist.

See `docs/architecture.md` for dependency directions and migration paths. Keep default rules and schemas inside package resources and verify installed artifacts outside the checkout. Task writes must preserve execution-token and lease checks; never mark all active jobs failed during application startup. Derive verification freshness when reading reports. Keep generated contracts synchronized with model changes and retain the dependency-free runner.
