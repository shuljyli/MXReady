#!/usr/bin/env bash
set -euo pipefail
bundle_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -x "$bundle_dir/.venv/bin/python" ]]; then
  echo "Run bash install.sh first." >&2
  exit 1
fi
exec "$bundle_dir/.venv/bin/python" -m mxready.cli.serve "$@"
