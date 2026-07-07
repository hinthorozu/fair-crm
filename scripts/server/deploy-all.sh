#!/usr/bin/env bash
#
# Application deploy/update for KYROX Core + Fair CRM.
# Run after bootstrap-server.sh on fresh servers, or alone for updates.
#
# Safe deploy contract (backup/restore compatible):
#   - Git pull + dependency install + frontend build + systemd/nginx reload
#   - Alembic upgrade head on both databases (required after restore; non-destructive)
#   - Backend restart via systemd (normal)
#   - ensure_database only CREATE DATABASE when missing (no drop/truncate/reset)
#   - Never runs pg_restore, restore jobs, or backup deletion
#   - Never touches backups/, data/restore_uploads/, or data/restore_logs/
#   - Never overwrites backend/.env or other .env files (copy-if-missing only)
#   - Preserves server .env keys such as ALLOW_RESTORE and TARGET_DATABASE_URL
#   - Does not clear system_backup_restore_jobs or other CRM data tables
#
# Usage (on server):
#   sudo /opt/fair-crm/scripts/server/deploy-all.sh
#
# Optional environment overrides:
#   KYROX_CORE_DIR=/opt/kyrox-core
#   FAIR_CRM_DIR=/opt/fair-crm
#   KYROX_CORE_BRANCH=main
#   FAIR_CRM_BRANCH=feat/dev-auto-start-v1
#   KYROX_CORE_REPO=https://github.com/hinthorozu/kyrox-core.git
#   DEPLOY_SERVICE_USER=ubuntu
#   SERVER_PUBLIC_URL=http://203.0.113.10
#   SKIP_FRONTEND_BUILD=1
#   SKIP_CORE_DEV_SEED=1
#   SKIP_SYSTEMD=1
#   SKIP_NGINX_RELOAD=1
#   RUN_POST_CHECK=1
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

KYROX_CORE_DIR="${KYROX_CORE_DIR:-/opt/kyrox-core}"
FAIR_CRM_DIR="${FAIR_CRM_DIR:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
KYROX_CORE_REPO="${KYROX_CORE_REPO:-https://github.com/hinthorozu/kyrox-core.git}"
KYROX_CORE_BRANCH="${KYROX_CORE_BRANCH:-main}"
FAIR_CRM_BRANCH="${FAIR_CRM_BRANCH:-feat/dev-auto-start-v1}"
DEPLOY_SERVICE_USER="${DEPLOY_SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
SERVER_PUBLIC_URL="${SERVER_PUBLIC_URL:-$(detect_server_public_url)}"

CORE_PORT="${CORE_PORT:-8000}"
FAIR_CRM_PORT="${FAIR_CRM_PORT:-8001}"
CORE_HEALTH_PATH="${CORE_HEALTH_PATH:-/api/v1/health}"
FAIR_CRM_HEALTH_PATH="${FAIR_CRM_HEALTH_PATH:-/health}"

PROTECTED_FAIR_CRM_PATHS=(
  "docker-compose.yml"
  "backend/.env"
  "frontend/.env"
  "frontend/.env.production"
  "backups"
  "data/restore_uploads"
  "data/restore_logs"
)
PROTECTED_KYROX_CORE_PATHS=(
  "backend/.env"
  ".env"
)

REPORT_CORE_STATUS="unknown"
REPORT_FAIR_STATUS="unknown"
REPORT_FRONTEND_BUILD="skipped"
REPORT_CORE_MIGRATION="not run"
REPORT_FAIR_MIGRATION="not run"
REPORT_CORE_HEALTH="000"
REPORT_FAIR_HEALTH="000"
REPORT_CORE_HASH="n/a"
REPORT_FAIR_HASH="n/a"
REPORT_CORE_SEED="not run"
REPORT_NGINX="skipped"
REPORT_NGINX_TEST="skipped"
REPORT_POST_CHECK="skipped"
REPORT_LOGIN_SMOKE="not run"
REPORT_FINAL_STATUS="unknown"

clone_or_update_repo() {
  local dir="$1"
  local repo_url="$2"
  local branch="$3"
  shift 3
  local -a protected=("$@")

  if [[ ! -d "$dir" ]]; then
    step "Clone repository into ${dir}"
    mkdir -p "$(dirname "$dir")"
    git clone --branch "$branch" "$repo_url" "$dir"
    return 0
  fi

  ensure_git_ff_pull "$dir" "$branch" "${protected[@]}"
}

setup_python_project() {
  local name="$1"
  local project_dir="$2"
  local venv_dir="$3"

  step "Python dependencies for ${name}"
  local requirements
  requirements="$(resolve_requirements_file "$project_dir" || die "requirements.txt not found under ${project_dir}")"
  ensure_python_venv "$venv_dir"
  pip_install_requirements "$venv_dir" "$requirements"
}

run_core_dev_seed() {
  step "Seed Core dev identity for Fair CRM"
  local core_env="${KYROX_CORE_DIR}/backend/.env"
  local db_url
  db_url="$(read_env_key "$core_env" DATABASE_URL || read_env_key "$core_env" KYROX_CORE_DATABASE_URL || true)"
  [[ -n "$db_url" ]] || die "Cannot resolve Core DATABASE_URL for dev seed"

  if [[ "${SKIP_CORE_DEV_SEED:-0}" == "1" ]]; then
    REPORT_CORE_SEED="skipped (SKIP_CORE_DEV_SEED=1)"
    warn "Skipping Core dev seed"
    return 0
  fi

  local seed_script="${KYROX_CORE_DIR}/scripts/seed_fair_crm_dev_identity.py"
  [[ -f "$seed_script" ]] || die "Core dev seed script missing: ${seed_script}"

  (
    cd "$KYROX_CORE_DIR"
    env DATABASE_URL="$db_url" KYROX_CORE_DATABASE_URL="$db_url" \
      "${KYROX_CORE_DIR}/.venv/bin/python" "$seed_script"
  ) || die "Core dev identity seed failed"
  REPORT_CORE_SEED="success (idempotent)"
  print_core_seed_identity_report
}

manage_systemd_services() {
  if [[ "${SKIP_SYSTEMD:-0}" == "1" ]]; then
    warn "SKIP_SYSTEMD=1; leaving systemd units untouched"
    return 0
  fi

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  render_template "${SCRIPT_DIR}/systemd/kyrox-core.service" "${tmp_dir}/kyrox-core.service"
  render_template "${SCRIPT_DIR}/systemd/fair-crm-backend.service" "${tmp_dir}/fair-crm-backend.service"

  install_systemd_unit "${tmp_dir}/kyrox-core.service" "kyrox-core.service"
  install_systemd_unit "${tmp_dir}/fair-crm-backend.service" "fair-crm-backend.service"
  rm -rf "$tmp_dir"

  if [[ "${EUID}" -ne 0 ]]; then
    warn "Run with sudo to reload/restart systemd services"
    return 0
  fi

  step "Reload and restart systemd services"
  systemctl daemon-reload
  systemctl enable kyrox-core fair-crm-backend
  systemctl restart kyrox-core
  sleep 2
  systemctl restart fair-crm-backend

  REPORT_CORE_STATUS="$(systemctl is-active kyrox-core 2>/dev/null || echo unknown)"
  REPORT_FAIR_STATUS="$(systemctl is-active fair-crm-backend 2>/dev/null || echo unknown)"
}

build_frontend() {
  if [[ "${SKIP_FRONTEND_BUILD:-0}" == "1" ]]; then
    REPORT_FRONTEND_BUILD="skipped (SKIP_FRONTEND_BUILD=1)"
    return 0
  fi

  step "Frontend npm install + build"
  require_cmd npm
  (
    cd "${FAIR_CRM_DIR}/frontend"
    npm install
    npm run build
  )
  REPORT_FRONTEND_BUILD="success"

  if [[ ! -d "${FAIR_CRM_DIR}/frontend/dist" ]]; then
    REPORT_FRONTEND_BUILD="failed (dist missing)"
    die "Frontend build did not produce frontend/dist"
  fi
  log "Frontend build output: ${FAIR_CRM_DIR}/frontend/dist"
}

run_health_checks() {
  step "Health checks"
  local core_url="http://127.0.0.1:${CORE_PORT}${CORE_HEALTH_PATH}"
  local fair_url="http://127.0.0.1:${FAIR_CRM_PORT}${FAIR_CRM_HEALTH_PATH}"
  local statuses

  if statuses="$(wait_for_http_health "$core_url" "$fair_url" 60)"; then
    read -r REPORT_CORE_HEALTH REPORT_FAIR_HEALTH <<<"$statuses"
  else
    read -r REPORT_CORE_HEALTH REPORT_FAIR_HEALTH <<<"$statuses"
  fi

  if [[ "$REPORT_CORE_HEALTH" != "200" ]]; then
    local legacy_core_health
    legacy_core_health="$(http_status "http://127.0.0.1:${CORE_PORT}/health")"
    warn "Core health ${core_url} => ${REPORT_CORE_HEALTH}; /health => ${legacy_core_health}"
    die "Core health check failed (expected 200 at ${core_url})"
  fi
  if [[ "$REPORT_FAIR_HEALTH" != "200" ]]; then
    die "Fair CRM health check failed (expected 200 at ${fair_url})"
  fi
}

run_login_smoke_deploy() {
  step "Login smoke test (Core auth)"
  if run_login_smoke_test "$CORE_PORT" "deploy"; then
    REPORT_LOGIN_SMOKE="passed (HTTP 200, access_token present)"
    echo "[OK] Login smoke test passed"
  else
    REPORT_LOGIN_SMOKE="failed"
    die "Login smoke test failed"
  fi
}

maybe_run_post_check() {
  if [[ "${RUN_POST_CHECK:-1}" != "1" ]]; then
    REPORT_POST_CHECK="skipped (RUN_POST_CHECK=0)"
    return 0
  fi
  step "Post-deploy health audit (check-server.sh)"
  if [[ "${EUID}" -ne 0 ]]; then
    REPORT_POST_CHECK="skipped (requires sudo)"
    warn "Skipping post-deploy check; run sudo ${SCRIPT_DIR}/check-server.sh manually"
    return 0
  fi
  if SKIP_PUBLIC_CHECKS=1 "${SCRIPT_DIR}/check-server.sh"; then
    REPORT_POST_CHECK="passed"
  else
    REPORT_POST_CHECK="failed"
    die "Post-deploy check-server.sh reported failures"
  fi
}

print_final_report() {
  local health_label login_label
  if [[ "$REPORT_CORE_HEALTH" == "200" && "$REPORT_FAIR_HEALTH" == "200" ]]; then
    health_label="passed"
  else
    health_label="failed"
  fi
  if [[ "$REPORT_LOGIN_SMOKE" == passed* ]]; then
    login_label="passed"
  else
    login_label="${REPORT_LOGIN_SMOKE}"
  fi
  if [[ "$REPORT_FRONTEND_BUILD" == "success" ]]; then
    REPORT_FINAL_STATUS="deploy complete"
  elif [[ "${DEPLOY_FAILED_STEP:-none}" != "none" ]]; then
    REPORT_FINAL_STATUS="BROKEN"
  else
    REPORT_FINAL_STATUS="see details"
  fi

  echo ""
  echo "========== DEPLOY ACCEPTANCE REPORT =========="
  echo "Failed step: ${DEPLOY_FAILED_STEP:-none}"
  echo ""
  echo "1. Scripts:"
  echo "   scripts/server/bootstrap-server.sh"
  echo "   scripts/server/deploy-all.sh"
  echo "   scripts/server/check-server.sh"
  echo ""
  echo "2. Core seed: ${REPORT_CORE_SEED}"
  echo "   email: ${DEV_LOGIN_EMAIL}"
  echo "   password: ${DEV_LOGIN_PASSWORD}"
  echo "   org id: ${DEV_LOGIN_ORG_ID}"
  echo "   role: owner/admin; permissions: all fair_crm.*"
  echo ""
  echo "3. systemd:"
  print_systemd_service_summary "$SCRIPT_DIR" | sed 's/^/   /'
  echo ""
  echo "4. nginx:"
  echo "   /              -> ${FAIR_CRM_DIR}/frontend/dist"
  echo "   /api/          -> 127.0.0.1:8001"
  echo "   /kyrox-core/   -> 127.0.0.1:8000"
  echo "   nginx -t: ${REPORT_NGINX_TEST}; reload: ${REPORT_NGINX}"
  echo ""
  echo "5. Health: Core ${REPORT_CORE_HEALTH}, Fair CRM ${REPORT_FAIR_HEALTH} (${health_label})"
  echo "6. Login smoke: ${REPORT_LOGIN_SMOKE} (${login_label})"
  echo "7. Frontend build: ${REPORT_FRONTEND_BUILD}"
  echo "8. Migrations: Core ${REPORT_CORE_MIGRATION}, Fair CRM ${REPORT_FAIR_MIGRATION}"
  echo "9. Git commits: kyrox-core=${REPORT_CORE_HASH}, fair-crm=${REPORT_FAIR_HASH}"
  echo "10. Post-deploy check: ${REPORT_POST_CHECK}"
  echo "11. Push: not run by deploy script (manual git push if needed)"
  echo ""
  echo "Core API: http://127.0.0.1:${CORE_PORT}"
  echo "Fair CRM API: http://127.0.0.1:${FAIR_CRM_PORT}"
  echo "Public UI: ${SERVER_PUBLIC_URL}/"
  echo "=============================================="
}

log_deploy_safety_contract() {
  step "Deploy safety contract (backup/restore compatible)"
  log "Will run: git pull, pip/npm install, alembic upgrade head, systemd restart"
  log "Will not: drop/truncate DB, pg_restore, touch backups/ or restore data dirs, overwrite .env"
}

main() {
  log_deploy_safety_contract

  step "Preflight commands"
  require_linux
  require_cmd git
  require_cmd python3
  require_cmd curl
  require_cmd psql

  step "Verify target directories"
  mkdir -p "$(dirname "$KYROX_CORE_DIR")" "$(dirname "$FAIR_CRM_DIR")"
  log "KYROX_CORE_DIR=${KYROX_CORE_DIR}"
  log "FAIR_CRM_DIR=${FAIR_CRM_DIR}"
  log "SERVER_PUBLIC_URL=${SERVER_PUBLIC_URL}"

  clone_or_update_repo "$KYROX_CORE_DIR" "$KYROX_CORE_REPO" "$KYROX_CORE_BRANCH" "${PROTECTED_KYROX_CORE_PATHS[@]}"

  copy_env_if_missing "${KYROX_CORE_DIR}/backend/.env.example" "${KYROX_CORE_DIR}/backend/.env"
  copy_env_if_missing "${KYROX_CORE_DIR}/.env.example" "${KYROX_CORE_DIR}/.env"

  if [[ -d "${FAIR_CRM_DIR}/.git" ]]; then
    clone_or_update_repo "$FAIR_CRM_DIR" "$(git -C "$FAIR_CRM_DIR" remote get-url origin)" "$FAIR_CRM_BRANCH" "${PROTECTED_FAIR_CRM_PATHS[@]}"
  else
    warn "Fair CRM repo not initialized at ${FAIR_CRM_DIR}; using working tree without git pull"
  fi

  REPORT_CORE_HASH="$(git_short_hash "$KYROX_CORE_DIR")"
  REPORT_FAIR_HASH="$(git_short_hash "$FAIR_CRM_DIR")"

  setup_python_project "kyrox-core" "$KYROX_CORE_DIR" "${KYROX_CORE_DIR}/.venv"
  setup_python_project "fair-crm" "$FAIR_CRM_DIR" "${FAIR_CRM_DIR}/backend/.venv"

  ensure_postgres_container "$FAIR_CRM_DIR"
  resolve_postgres_connection "$FAIR_CRM_DIR" "$KYROX_CORE_DIR"

  step "PostgreSQL connectivity"
  PGPASSWORD="${PG_PASS}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres -c "SELECT 1" >/dev/null \
    || die "Cannot connect to PostgreSQL at ${PG_HOST}:${PG_PORT}"

  ensure_database "kyrox_core"
  ensure_database "fair_crm"
  ensure_repo_data_dirs "$FAIR_CRM_DIR"

  validate_env_files_required

  local core_db_url fair_db_url
  core_db_url="$(resolve_core_db_url)"
  fair_db_url="$(resolve_fair_db_url)"

  if run_alembic_upgrade "$KYROX_CORE_DIR" "${KYROX_CORE_DIR}/.venv/bin/python" "alembic.ini" "$core_db_url"; then
    REPORT_CORE_MIGRATION="success"
  else
    REPORT_CORE_MIGRATION="failed"
    die "kyrox-core alembic upgrade failed"
  fi

  run_core_dev_seed

  if run_alembic_upgrade "$FAIR_CRM_DIR" "${FAIR_CRM_DIR}/backend/.venv/bin/python" "alembic.ini" "$fair_db_url"; then
    REPORT_FAIR_MIGRATION="success"
  else
    REPORT_FAIR_MIGRATION="failed"
    die "fair-crm alembic upgrade failed"
  fi

  manage_systemd_services
  build_frontend

  if [[ "${SKIP_NGINX_RELOAD:-0}" != "1" ]]; then
    step "Reload nginx"
    if command -v nginx >/dev/null 2>&1; then
      if run_root nginx -t >/dev/null 2>&1; then
        REPORT_NGINX_TEST="ok"
        run_root systemctl reload nginx
        REPORT_NGINX="reloaded"
      else
        REPORT_NGINX_TEST="failed"
        die "nginx -t failed before reload"
      fi
    else
      REPORT_NGINX_TEST="skipped (nginx not installed)"
    fi
  fi

  run_health_checks
  run_login_smoke_deploy
  maybe_run_post_check
  print_final_report
}

trap 'if [[ $? -ne 0 ]]; then echo ""; print_final_report; fi' EXIT

main "$@"
