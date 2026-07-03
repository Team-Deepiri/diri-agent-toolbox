#!/usr/bin/env bash
# Run the same checks as .github/workflows/ci.yml in venv.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

set -euo pipefail

source .venv/bin/activate

poetry install --with dev --no-interaction

python -m pre_commit install

echo "pre-commit hook installed, tests will run automatically before each commit."
echo "Run: python -m pre_commit run --all-files to run checks manually."

