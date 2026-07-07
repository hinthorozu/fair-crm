#!/usr/bin/env bash
#
# One-shot server bootstrap/update for KYROX Core + Fair CRM.
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
#   SKIP_FRONTEND_BUILD=1
#   SKIP_CORE_DEV_SEED=1
#   SKIP_SYSTEMD=1
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

CORE_PORT="${CORE_PORT:-8000}"
FAIR_CRM_PORT="${FAIR_CRM_PORT:-8001}"
CORE_HEALTH_PATH="${CORE_HEALTH_PATH:-/api/v1/health}"
FAIR_CRM_HEALTH_PATH="${FAIR_CRM_HEALTH_PATH:-/health}"

PROTECTED_FAIR_CRM_PATHS=(
  "docker-compose.yml"
  "backend/.env"
  "frontend/.env"
  "frontend/.env.production"
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

parse_compose_postgres() {
  local compose_file="$1"
  COMPOSE_PG_USER="postgres"
  COMPOSE_PG_PASS="postgres"
  COMPOSE_PG_PORT="5432"

  [[ -f "$compose_file" ]] || return 0

  local user_line pass_line port_line
  user_line="$(grep -E 'POSTGRES_USER:' "$compose_file" | head -n 1 || true)"
  pass_line="$(grep -E 'POSTGRES_PASSWORD:' "$compose_file" | head -n 1 || true)"
  port_line="$(grep -E '^[[:space:]]*-[[:space:]]*"[0-9]+:5432"' "$compose_file" | head -n 1 || true)"

  if [[ -n "$user_line" ]]; then
    COMPOSE_PG_USER="$(echo "$user_line" | sed -E 's/.*POSTGRES_USER:[[:space:]]*//; s/[[:space:]]+$//')"
  fi
  if [[ -n "$pass_line" ]]; then
    COMPOSE_PG_PASS="$(echo "$pass_line" | sed -E 's/.*POSTGRES_PASSWORD:[[:space:]]*//; s/[[:space:]]+$//')"
  fi
  if [[ -n "$port_line" ]]; then
    COMPOSE_PG_PORT="$(echo "$port_line" | sed -E 's/.*"([0-9]+):5432".*/\1/')"
  fi
}

ensure_postgres_running() {
  local compose_file="${FAIR_CRM_DIR}/docker-compose.yml"
  if [[ -f "$compose_file" ]] && command -v docker >/dev/null 2>&1; then
    step "Ensure Postgres container is up (docker compose; local compose file preserved)"
    (
      cd "$FAIR_CRM_DIR"
      docker compose up -d postgres
    )
  fi
}

psql_admin_exec() {
  local sql="$1"
  PGPASSWORD="${PG_PASS}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres -v ON_ERROR_STOP=1 -c "$sql"
}

database_exists() {
  local db_name="$1"
  local count
  count="$(PGPASSWORD="${PG_PASS}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres -tAc \
    "SELECT COUNT(*) FROM pg_database WHERE datname='${db_name}'")"
  [[ "${count}" == "1" ]]
}

ensure_database() {
  local db_name="$1"
  if database_exists "$db_name"; then
    log "Database exists: ${db_name}"
  else
    log "Creating database: ${db_name}"
    psql_admin_exec "CREATE DATABASE \"${db_name}\";"
  fi
}

resolve_postgres_connection() {
  step "Resolve PostgreSQL connection settings"
  parse_compose_postgres "${FAIR_CRM_DIR}/docker-compose.yml"

  PG_HOST="127.0.0.1"
  PG_PORT="${COMPOSE_PG_PORT}"
  PG_USER="${COMPOSE_PG_USER}"
  PG_PASS="${COMPOSE_PG_PASS}"

  local fair_env="${FAIR_CRM_DIR}/backend/.env"
  local core_env="${KYROX_CORE_DIR}/backend/.env"
  local fair_db_url core_db_url

  if [[ -f "$fair_env" ]]; then
    fair_db_url="$(read_env_key "$fair_env" DATABASE_URL || read_env_key "$fair_env" FAIR_CRM_DATABASE_URL || true)"
  fi
  if [[ -f "$core_env" ]]; then
    core_db_url="$(read_env_key "$core_env" DATABASE_URL || read_env_key "$core_env" KYROX_CORE_DATABASE_URL || true)"
  fi

  if [[ -n "${fair_db_url:-}" ]]; then
    eval "$(parse_database_url "$fair_db_url")"
    log "Postgres settings from Fair CRM .env (host=${PG_HOST} port=${PG_PORT} user=${PG_USER})"
  elif [[ -n "${core_db_url:-}" ]]; then
    eval "$(parse_database_url "$core_db_url")"
    log "Postgres settings from Core .env (host=${PG_HOST} port=${PG_PORT} user=${PG_USER})"
  else
    log "Postgres settings from docker-compose defaults (host=${PG_HOST} port=${PG_PORT} user=${PG_USER})"
  fi
}

validate_env_files() {
  step "Validate Core and Fair CRM .env files"
  local core_env="${KYROX_CORE_DIR}/backend/.env"
  local fair_env="${FAIR_CRM_DIR}/backend/.env"

  [[ -f "$core_env" ]] || die "Missing Core env file: ${core_env} (create manually; deploy will not overwrite)"
  [[ -f "$fair_env" ]] || die "Missing Fair CRM env file: ${fair_env} (create manually; deploy will not overwrite)"

  local core_jwt fair_jwt fair_core_url
  core_jwt="$(read_env_key "$core_env" JWT_SECRET_KEY || true)"
  fair_jwt="$(read_env_key "$fair_env" JWT_SECRET_KEY || true)"
  fair_core_url="$(read_env_key "$fair_env" KYROX_CORE_BASE_URL || true)"

  [[ -n "$core_jwt" ]] || die "JWT_SECRET_KEY missing in ${core_env}"
  [[ -n "$fair_jwt" ]] || die "JWT_SECRET_KEY missing in ${fair_env}"
  [[ "$core_jwt" == "$fair_jwt" ]] || die "JWT_SECRET_KEY mismatch between Core and Fair CRM .env files"

  if [[ -n "$fair_core_url" && "$fair_core_url" != "http://127.0.0.1:8000" && "$fair_core_url" != "http://localhost:8000" ]]; then
    warn "Fair CRM KYROX_CORE_BASE_URL=${fair_core_url} (expected http://127.0.0.1:8000 on single-host deploy)"
  else
    log "Fair CRM KYROX_CORE_BASE_URL OK (${fair_core_url:-http://127.0.0.1:8000})"
  fi
}

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

render_systemd_unit() {
  local template="$1"
  local output="$2"
  sed "s/@DEPLOY_SERVICE_USER@/${DEPLOY_SERVICE_USER}/g" "$template" >"$output"
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
  )
  REPORT_CORE_SEED="success"
}

manage_systemd_services() {
  if [[ "${SKIP_SYSTEMD:-0}" == "1" ]]; then
    warn "SKIP_SYSTEMD=1; leaving systemd units untouched"
    return 0
  fi

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  render_systemd_unit "${SCRIPT_DIR}/systemd/kyrox-core.service" "${tmp_dir}/kyrox-core.service"
  render_systemd_unit "${SCRIPT_DIR}/systemd/fair-crm-backend.service" "${tmp_dir}/fair-crm-backend.service"

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

  if [[ -d "${FAIR_CRM_DIR}/frontend/dist" ]]; then
    log "Frontend build output: ${FAIR_CRM_DIR}/frontend/dist"
    if command -v nginx >/dev/null 2>&1; then
      if grep -R "frontend/dist" /etc/nginx 2>/dev/null | head -n 1 >/dev/null; then
        log "nginx config references frontend/dist"
      else
        warn "nginx installed but no config referencing frontend/dist found; verify static root manually"
      fi
    fi
  else
    REPORT_FRONTEND_BUILD="failed (dist missing)"
    die "Frontend build did not produce frontend/dist"
  fi
}

run_health_checks() {
  step "Health checks"
  local core_url="http://127.0.0.1:${CORE_PORT}${CORE_HEALTH_PATH}"
  local fair_url="http://127.0.0.1:${FAIR_CRM_PORT}${FAIR_CRM_HEALTH_PATH}"

  local deadline=$((SECONDS + 60))
  while (( SECONDS < deadline )); do
    REPORT_CORE_HEALTH="$(http_status "$core_url")"
    REPORT_FAIR_HEALTH="$(http_status "$fair_url")"
    if [[ "$REPORT_CORE_HEALTH" == "200" && "$REPORT_FAIR_HEALTH" == "200" ]]; then
      break
    fi
    sleep 2
  done

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

print_final_report() {
  echo ""
  echo "========== DEPLOY REPORT =========="
  echo "Failed step: ${DEPLOY_FAILED_STEP:-none}"
  echo "Core systemd: ${REPORT_CORE_STATUS}"
  echo "Fair CRM systemd: ${REPORT_FAIR_STATUS}"
  echo "Frontend build: ${REPORT_FRONTEND_BUILD}"
  echo "Core migration: ${REPORT_CORE_MIGRATION}"
  echo "Fair CRM migration: ${REPORT_FAIR_MIGRATION}"
  echo "Core dev seed: ${REPORT_CORE_SEED}"
  echo "Core health (${CORE_HEALTH_PATH}): ${REPORT_CORE_HEALTH}"
  echo "Fair CRM health (${FAIR_CRM_HEALTH_PATH}): ${REPORT_FAIR_HEALTH}"
  echo "Git commit kyrox-core: ${REPORT_CORE_HASH}"
  echo "Git commit fair-crm: ${REPORT_FAIR_HASH}"
  echo "Core URL: http://127.0.0.1:${CORE_PORT}"
  echo "Fair CRM API: http://127.0.0.1:${FAIR_CRM_PORT}"
  echo "Frontend dist: ${FAIR_CRM_DIR}/frontend/dist"
  echo "==================================="
}

main() {
  step "Preflight commands"
  require_cmd git
  require_cmd python3
  require_cmd curl
  require_cmd psql

  step "Verify target directories"
  mkdir -p "$(dirname "$KYROX_CORE_DIR")" "$(dirname "$FAIR_CRM_DIR")"
  log "KYROX_CORE_DIR=${KYROX_CORE_DIR}"
  log "FAIR_CRM_DIR=${FAIR_CRM_DIR}"

  clone_or_update_repo "$KYROX_CORE_DIR" "$KYROX_CORE_REPO" "$KYROX_CORE_BRANCH" "${PROTECTED_KYROX_CORE_PATHS[@]}"

  if [[ -d "${FAIR_CRM_DIR}/.git" ]]; then
    clone_or_update_repo "$FAIR_CRM_DIR" "$(git -C "$FAIR_CRM_DIR" remote get-url origin)" "$FAIR_CRM_BRANCH" "${PROTECTED_FAIR_CRM_PATHS[@]}"
  else
    warn "Fair CRM repo not initialized at ${FAIR_CRM_DIR}; using working tree without git pull"
  fi

  REPORT_CORE_HASH="$(git_short_hash "$KYROX_CORE_DIR")"
  REPORT_FAIR_HASH="$(git_short_hash "$FAIR_CRM_DIR")"

  setup_python_project "kyrox-core" "$KYROX_CORE_DIR" "${KYROX_CORE_DIR}/.venv"
  setup_python_project "fair-crm" "$FAIR_CRM_DIR" "${FAIR_CRM_DIR}/backend/.venv"

  ensure_postgres_running
  resolve_postgres_connection

  step "PostgreSQL connectivity"
  PGPASSWORD="${PG_PASS}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres -c "SELECT 1" >/dev/null \
    || die "Cannot connect to PostgreSQL at ${PG_HOST}:${PG_PORT}"

  ensure_database "kyrox_core"
  ensure_database "fair_crm"

  validate_env_files

  local core_db_url fair_db_url
  core_db_url="$(read_env_key "${KYROX_CORE_DIR}/backend/.env" DATABASE_URL || read_env_key "${KYROX_CORE_DIR}/backend/.env" KYROX_CORE_DATABASE_URL || echo "postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/kyrox_core")"
  fair_db_url="$(read_env_key "${FAIR_CRM_DIR}/backend/.env" DATABASE_URL || read_env_key "${FAIR_CRM_DIR}/backend/.env" FAIR_CRM_DATABASE_URL || echo "postgresql+psycopg2://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/fair_crm")"

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
  run_health_checks
  print_final_report
}

trap 'if [[ $? -ne 0 ]]; then echo ""; print_final_report; fi' EXIT

main "$@"
