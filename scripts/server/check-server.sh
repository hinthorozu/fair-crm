#!/usr/bin/env bash
#
# Read-only health audit for an existing KYROX Core + Fair CRM server.
#
# Usage:
#   sudo bash /opt/fair-crm/scripts/server/check-server.sh
#
# Exit codes:
#   0 = HEALTHY (or DEGRADED unless CHECK_STRICT=1)
#   1 = BROKEN (or DEGRADED with CHECK_STRICT=1)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

CHECK_QUIET=1
KYROX_CORE_DIR="${KYROX_CORE_DIR:-/opt/kyrox-core}"
FAIR_CRM_DIR="${FAIR_CRM_DIR:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
SERVER_PUBLIC_URL="${SERVER_PUBLIC_URL:-$(detect_server_public_url)}"
CORE_PORT="${CORE_PORT:-8000}"
FAIR_CRM_PORT="${FAIR_CRM_PORT:-8001}"
CORE_HEALTH_PATH="${CORE_HEALTH_PATH:-/api/v1/health}"
FAIR_CRM_HEALTH_PATH="${FAIR_CRM_HEALTH_PATH:-/health}"

main() {
  check_reset_counters

  echo "FAIR CRM Server Check"
  echo ""

  if command -v docker >/dev/null 2>&1; then
    :
  else
    check_fail "Docker installed"
  fi
  if command -v docker >/dev/null 2>&1 && run_root systemctl is-active docker >/dev/null 2>&1; then
    check_pass "Docker service active"
  elif command -v docker >/dev/null 2>&1; then
    check_fail "Docker service active"
  fi

  check_docker_postgres "$FAIR_CRM_DIR"
  resolve_postgres_connection "$FAIR_CRM_DIR" "$KYROX_CORE_DIR"
  check_postgres_connectivity
  check_database_exists "kyrox_core"
  check_database_exists "fair_crm"

  validate_env_files_check

  if [[ -d "${KYROX_CORE_DIR}" && -x "${KYROX_CORE_DIR}/.venv/bin/python" ]]; then
    check_pass "Core virtualenv present"
  else
    check_fail "Core virtualenv present"
  fi
  if [[ -x "${FAIR_CRM_DIR}/backend/.venv/bin/python" ]]; then
    check_pass "Fair CRM virtualenv present"
  else
    check_fail "Fair CRM virtualenv present"
  fi
  check_playwright_chromium "$FAIR_CRM_DIR"
  if [[ -f "${FAIR_CRM_DIR}/frontend/dist/index.html" ]]; then
    check_pass "Frontend build present"
  else
    check_fail "Frontend build present"
  fi

  check_git_branch "fair-crm" "$FAIR_CRM_DIR" "$EXPECTED_FAIR_CRM_BRANCH"
  check_git_branch "kyrox-core" "$KYROX_CORE_DIR" "$EXPECTED_KYROX_CORE_BRANCH"
  check_fair_crm_server_scripts_executable "$FAIR_CRM_DIR"

  if [[ -f "${KYROX_CORE_DIR}/backend/.env" && -f "${FAIR_CRM_DIR}/backend/.env" ]]; then
    local core_db_url fair_db_url
    core_db_url="$(resolve_core_db_url)"
    fair_db_url="$(resolve_fair_db_url)"
    check_alembic_at_head "kyrox-core" "$KYROX_CORE_DIR" "${KYROX_CORE_DIR}/.venv/bin/python" "$core_db_url"
    check_core_migration_meets_seed_minimum \
      "$KYROX_CORE_DIR" "${KYROX_CORE_DIR}/.venv/bin/python" "$core_db_url"
    check_alembic_at_head "fair-crm" "$FAIR_CRM_DIR" "${FAIR_CRM_DIR}/backend/.venv/bin/python" "$fair_db_url"
  fi

  check_systemd_service "kyrox-core.service" "Core"
  check_systemd_service "fair-crm-backend.service" "Fair CRM backend"

  check_port_bindings
  check_firewall_rules
  check_nginx_site

  local core_url="http://127.0.0.1:${CORE_PORT}${CORE_HEALTH_PATH}"
  local fair_url="http://127.0.0.1:${FAIR_CRM_PORT}${FAIR_CRM_HEALTH_PATH}"
  local public_url=""
  if [[ "${SKIP_PUBLIC_CHECKS:-0}" != "1" ]]; then
    public_url="${SERVER_PUBLIC_URL}"
  fi
  check_http_endpoints "$core_url" "$fair_url" "$public_url"
  run_login_smoke_test "$CORE_PORT" "check"
  run_admin_backups_smoke_test "$FAIR_CRM_PORT" "$CORE_PORT" "check"

  echo ""
  echo "systemd service audit:"
  print_systemd_service_audit "$SCRIPT_DIR"
  print_nginx_config_audit "$FAIR_CRM_DIR"

  if check_finalize_exit; then
    exit 0
  fi
  exit 1
}

main "$@"
