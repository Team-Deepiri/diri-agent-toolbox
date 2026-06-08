#!/usr/bin/env bash
# Run the same checks as .github/workflows/ci.yml in venv.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

set -euo pipefail

source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e ".[dev]"

python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m pytest

echo "local-ci: all checks passed"
