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
CORE_PORT="${CORE_PORT:-8000}"
FAIR_CRM_PORT="${FAIR_CRM_PORT:-8001}"
CORE_HEALTH_PATH="${CORE_HEALTH_PATH:-/api/v1/health}"
FAIR_CRM_HEALTH_PATH="${FAIR_CRM_HEALTH_PATH:-/health}"
SERVER_BOOTSTRAP_ENV_FILE="${SERVER_BOOTSTRAP_ENV_FILE:-/etc/fair-crm/server-bootstrap.env}"
DEV_SEED_ENV_FILE="${DEV_SEED_ENV_FILE:-/etc/fair-crm/dev-seed.env}"

check_bootstrap_settings() {
  local domain="faircrm.domain.com"
  local public_ip=""
  local letsencrypt_email=""

  if [[ -f "$SERVER_BOOTSTRAP_ENV_FILE" ]]; then
    check_pass "Bootstrap settings file present"
    domain="$(read_env_key "$SERVER_BOOTSTRAP_ENV_FILE" FAIR_CRM_DOMAIN || printf '%s' "$domain")"
    public_ip="$(read_env_key "$SERVER_BOOTSTRAP_ENV_FILE" SERVER_PUBLIC_IP || true)"
    letsencrypt_email="$(read_env_key "$SERVER_BOOTSTRAP_ENV_FILE" LETSENCRYPT_EMAIL || true)"
  else
    check_warn_item "Bootstrap settings file present (${SERVER_BOOTSTRAP_ENV_FILE})"
  fi

  if [[ -n "$domain" ]]; then
    check_pass "Configured domain: ${domain}"
  else
    check_fail "Configured domain present"
  fi

  if [[ -n "$public_ip" ]]; then
    check_pass "Configured public IPv4: ${public_ip}"
  else
    check_warn_item "Configured public IPv4 present"
  fi

  if [[ -n "$letsencrypt_email" ]]; then
    check_pass "Let's Encrypt e-mail configured: ${letsencrypt_email}"
  else
    check_warn_item "Let's Encrypt e-mail configured"
  fi

  local nginx_site="/etc/nginx/sites-available/fair-crm"
  if [[ -f "$nginx_site" ]] && grep -Eq "^[[:space:]]*server_name[[:space:]]+${domain//./\\.};" "$nginx_site"; then
    check_pass "Nginx server_name=${domain}"
  else
    check_fail "Nginx server_name=${domain}"
  fi

  if [[ -f "/etc/letsencrypt/live/${domain}/fullchain.pem" && -f "/etc/letsencrypt/live/${domain}/privkey.pem" ]]; then
    check_pass "Let's Encrypt certificate present for ${domain}"
  else
    check_warn_item "Let's Encrypt certificate present for ${domain}"
  fi

  if command -v systemctl >/dev/null 2>&1 && systemctl is-enabled certbot.timer >/dev/null 2>&1; then
    check_pass "Certbot renewal timer enabled"
  else
    check_warn_item "Certbot renewal timer enabled"
  fi

  local dev_password=""
  dev_password="$(read_env_key "$DEV_SEED_ENV_FILE" DEV_USER_PASSWORD || true)"
  if [[ -n "$dev_password" ]]; then
    check_pass "DEV admin seed password configured"
  else
    check_fail "DEV admin seed password configured (${DEV_SEED_ENV_FILE})"
  fi

  local compose_file="${FAIR_CRM_DIR}/docker-compose.yml"
  if [[ -f "$compose_file" ]] && grep -qE '^[[:space:]]*-[[:space:]]*"127\.0\.0\.1:5432:5432"' "$compose_file"; then
    check_pass "PostgreSQL local 127.0.0.1:5432 mapping preserved"
  else
    check_fail "PostgreSQL local 127.0.0.1:5432 mapping preserved"
  fi

  # Security contract: PostgreSQL is local-only. Remote database exposure was
  # intentionally retired after the server hardening incident. A public Docker
  # publish or UFW allow for 15432 is therefore a failure, not a requirement.
  if [[ -f "$compose_file" ]] && grep -qE '^[[:space:]]*-[[:space:]]*"([0-9.]+:)?15432:5432"' "$compose_file"; then
    check_fail "PostgreSQL remote tcp/15432 not published by Docker"
  else
    check_pass "PostgreSQL remote tcp/15432 not published by Docker"
  fi

  if command -v ufw >/dev/null 2>&1; then
    if run_root ufw status 2>/dev/null | awk '$1 == "15432" || $1 == "15432/tcp" { if ($0 ~ /ALLOW/) found=1 } END { exit(found ? 0 : 1) }'; then
      check_fail "UFW blocks tcp/15432"
    else
      check_pass "UFW blocks tcp/15432"
    fi
  fi
}

# UFW port checks must match the rule's port token exactly.
check_firewall_rules_exact() {
  if ! command -v ufw >/dev/null 2>&1; then
    check_warn_item "UFW installed"
    return 0
  fi

  local status
  status="$(run_root ufw status 2>/dev/null || true)"

  if grep -q "Status: active" <<<"$status"; then
    check_pass "UFW active"
  else
    check_warn_item "UFW active"
  fi

  if awk '$1 == "22/tcp" || $1 == "22" || $1 == "OpenSSH" { if ($0 ~ /ALLOW/) found=1 } END { exit(found ? 0 : 1) }' <<<"$status"; then
    check_pass "22 allowed"
  else
    check_warn_item "22 allowed"
  fi

  if awk '$1 == "80/tcp" || $1 == "80" { if ($0 ~ /ALLOW/) found=1 } END { exit(found ? 0 : 1) }' <<<"$status"; then
    check_pass "80 allowed"
  else
    check_warn_item "80 allowed"
  fi

  if awk '$1 == "443/tcp" || $1 == "443" { if ($0 ~ /ALLOW/) found=1 } END { exit(found ? 0 : 1) }' <<<"$status"; then
    check_pass "443 allowed"
  else
    check_warn_item "443 not configured"
  fi

  local port
  for port in 5432 8000 8001 15432; do
    if awk -v p="$port" '$1 == p || $1 == p "/tcp" { if ($0 ~ /ALLOW/) found=1 } END { exit(found ? 0 : 1) }' <<<"$status"; then
      check_fail "${port} not publicly exposed"
    else
      check_pass "${port} not publicly exposed"
    fi
  done
}

main() {
  check_reset_counters

  echo "FAIR CRM Server Check"
  echo ""

  check_nodejs_runtime

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
  check_bootstrap_settings

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
  check_firewall_rules_exact
  check_nginx_site

  local core_url="http://127.0.0.1:${CORE_PORT}${CORE_HEALTH_PATH}"
  local fair_url="http://127.0.0.1:${FAIR_CRM_PORT}${FAIR_CRM_HEALTH_PATH}"
  check_http_endpoints "$core_url" "$fair_url"
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
