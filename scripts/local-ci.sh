#!/usr/bin/env bash
# Run the same checks as .github/workflows/ci.yml in venv.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

set -euo pipefail

source .venv/bin/activate

poetry install --with dev --no-interaction

poetry run ruff check src tests
poetry run ruff format --check src tests
poetry run mypy src
poetry run pytest

echo "local-ci: all checks passed"
