#!/usr/bin/env bash
# First-time setup and development server launcher for Mu2eTalks.

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { printf "${CYAN}==> %s${RESET}\n" "$*"; }
success() { printf "${GREEN}✓  %s${RESET}\n" "$*"; }
warn()    { printf "${YELLOW}!  %s${RESET}\n" "$*"; }
error()   { printf "${RED}✗  %s${RESET}\n" "$*" >&2; }
header()  { printf "\n${BOLD}%s${RESET}\n%s\n" "$*" "$(printf '─%.0s' {1..60})"; }

ADMIN_PASSWORD="${MU2E_INITIAL_ADMIN_PASSWORD:-}"
START_SERVER=true
SKIP_NPM=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --admin-password) ADMIN_PASSWORD="$2"; shift 2 ;;
    --no-server)      START_SERVER=false;  shift ;;
    --skip-npm)       SKIP_NPM=true;       shift ;;
    -h|--help)
      echo "Usage: ./bootstrap.sh [--admin-password PASS] [--no-server] [--skip-npm]"
      exit 0 ;;
    *) error "Unknown option: $1"; exit 1 ;;
  esac
done

header "Mu2eTalks Bootstrap"

info "Locating Python 3.12+..."
PYTHON=""
for cmd in python3.12 python3.13 python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  error "Python 3.12 or newer is required."
  exit 1
fi
success "Found $("$PYTHON" --version)"

if [[ ! -d .venv ]]; then
  info "Creating virtual environment (.venv)..."
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

info "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements-dev.txt

if [[ "$SKIP_NPM" == false ]] && command -v npm >/dev/null 2>&1; then
  info "Installing Node dependencies..."
  (cd theme/static_src && npm install --silent)
fi

header "Database"
python manage.py migrate -v 0

if [[ -z "$ADMIN_PASSWORD" ]]; then
  warn "No admin password provided; skipping seed_admin."
  warn "Use ./bootstrap.sh --admin-password <password> or set MU2E_INITIAL_ADMIN_PASSWORD."
else
  MU2E_INITIAL_ADMIN_PASSWORD="$ADMIN_PASSWORD" python manage.py seed_admin
  success "Admin account ready: mu2e-admin@fnal.gov"
fi

if [[ "$START_SERVER" == false ]]; then
  success "Bootstrap complete."
  exit 0
fi

info "Starting development server at http://localhost:8000 ..."
python manage.py runserver
