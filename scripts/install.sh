#!/usr/bin/env bash
# Install diri-agent-toolbox via curl:
#   curl -fsSL https://raw.githubusercontent.com/Team-Deepiri/diri-agent-toolbox/main/scripts/install.sh | bash
set -euo pipefail

REPO="Team-Deepiri/diri-agent-toolbox"
REPO_URL="https://github.com/${REPO}.git"
BRANCH="${DEEPIRI_AGENT_TOOLBOX_BRANCH:-main}"
KEEP_DIR="${DEEPIRI_AGENT_TOOLBOX_KEEP_DIR:-0}"

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Clone (when needed) and pip-install diri-agent-toolbox.

Options:
  -h, --help     Show this help
  --dry-run      Print actions without installing

Environment:
  DEEPIRI_AGENT_TOOLBOX_SRC       Existing checkout
  DEEPIRI_AGENT_TOOLBOX_BRANCH    Git branch (default: main)
  DEEPIRI_AGENT_TOOLBOX_KEEP_DIR  Keep clone when set to 1

Requires: git, python3 (>=3.11)
Verify:   python3 -c "import diri_agent_toolbox; print('ok')"
EOF
}

log() { printf '==> %s\n' "$*"; }

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

for cmd in git python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "error: $cmd is required." >&2; exit 1; }
done

ROOT=""
CLEANUP=""

if [[ -n "${DEEPIRI_AGENT_TOOLBOX_SRC:-}" && -f "${DEEPIRI_AGENT_TOOLBOX_SRC}/pyproject.toml" ]]; then
  ROOT="${DEEPIRI_AGENT_TOOLBOX_SRC}"
elif [[ -n "${BASH_SOURCE[0]:-}" ]] && [[ "${BASH_SOURCE[0]}" != bash ]] && [[ -f "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/pyproject.toml" ]]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
  ROOT="$(mktemp -d)"
  [[ "$KEEP_DIR" != "1" ]] && CLEANUP="$ROOT"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "Would clone ${REPO_URL} to ${ROOT}"
    log "Would pip install -e ."
    exit 0
  fi
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$ROOT"
fi

[[ "$DRY_RUN" -eq 1 ]] && { log "Would pip install from ${ROOT}"; exit 0; }

trap '[[ -n "$CLEANUP" ]] && rm -rf "$CLEANUP"' EXIT
cd "$ROOT"

VENV="${ROOT}/.venv"
log "Creating venv at ${VENV}"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -U pip wheel -q
log "Installing diri-agent-toolbox"
"$VENV/bin/pip" install -e . -q

"$VENV/bin/python" -c "import diri_agent_toolbox; print('diri-agent-toolbox import ok')"
echo ""
echo "Activate: source ${VENV}/bin/activate"
echo "Verify:   python3 -c \"import diri_agent_toolbox; print('ok')\""
