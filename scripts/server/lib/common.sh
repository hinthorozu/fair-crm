#!/usr/bin/env bash
# Shared helpers for server bootstrap, deploy, and health-check scripts.

set -euo pipefail

DEPLOY_STEP=""
DEPLOY_FAILED_STEP=""
DEPLOY_LOG_PREFIX="[server]"

CHECK_FAIL_COUNT=0
CHECK_WARN_COUNT=0
CHECK_PASS_COUNT=0
CHECK_STRICT="${CHECK_STRICT:-0}"
CHECK_QUIET="${CHECK_QUIET:-0}"

DEV_LOGIN_EMAIL="${DEV_LOGIN_EMAIL:-dev@example.com}"
DEV_LOGIN_PASSWORD="${DEV_LOGIN_PASSWORD:-DevPassword123!}"
DEV_LOGIN_ORG_ID="${DEV_LOGIN_ORG_ID:-00000000-0000-4000-8000-000000000010}"

log() {
  echo "${DEPLOY_LOG_PREFIX} $*"
}

warn() {
  echo "${DEPLOY_LOG_PREFIX} WARN: $*" >&2
}

die() {
  DEPLOY_FAILED_STEP="${DEPLOY_STEP:-unknown}"
  echo "${DEPLOY_LOG_PREFIX} ERROR at step '${DEPLOY_FAILED_STEP}': $*" >&2
  exit 1
}

step() {
  DEPLOY_STEP="$1"
  if [[ "${CHECK_QUIET:-0}" != "1" ]]; then
    log "==> $1"
  fi
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "Required command not found: ${cmd}"
}

require_linux() {
  [[ "$(uname -s)" == "Linux" ]] || die "This script supports Linux servers only"
}

require_root_or_sudo() {
  if [[ "${EUID}" -ne 0 ]]; then
    if ! command -v sudo >/dev/null 2>&1; then
      die "Run as root or install sudo"
    fi
    if ! sudo -n true 2>/dev/null; then
      warn "Some steps need sudo; you may be prompted for a password"
    fi
  fi
}

run_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

check_reset_counters() {
  CHECK_FAIL_COUNT=0
  CHECK_WARN_COUNT=0
  CHECK_PASS_COUNT=0
}

check_pass() {
  local label="$1"
  CHECK_PASS_COUNT=$((CHECK_PASS_COUNT + 1))
  echo "[OK] ${label}"
}

check_fail() {
  local label="$1"
  CHECK_FAIL_COUNT=$((CHECK_FAIL_COUNT + 1))
  echo "[FAIL] ${label}" >&2
}

check_warn_item() {
  local label="$1"
  CHECK_WARN_COUNT=$((CHECK_WARN_COUNT + 1))
  echo "[WARN] ${label}" >&2
}

check_compute_final_status() {
  if [[ "${CHECK_FAIL_COUNT}" -gt 0 ]]; then
    printf '%s' "BROKEN"
  elif [[ "${CHECK_WARN_COUNT}" -gt 0 ]]; then
    printf '%s' "DEGRADED"
  else
    printf '%s' "HEALTHY"
  fi
}

check_finalize_exit() {
  local final
  final="$(check_compute_final_status)"
  echo ""
  echo "Final: ${final}"
  if [[ "${CHECK_FAIL_COUNT}" -gt 0 ]]; then
    return 1
  fi
  if [[ "${CHECK_STRICT}" == "1" && "${CHECK_WARN_COUNT}" -gt 0 ]]; then
    return 1
  fi
  return 0
}

read_env_key() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 1
  local line
  line="$(grep -E "^[[:space:]]*${key}=" "$file" | tail -n 1 || true)"
  [[ -n "$line" ]] || return 1
  local value="${line#*=}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  printf '%s' "$value"
}

parse_database_url() {
  local url="${1//+psycopg2/}"
  python3 - "$url" <<'PY'
import sys
from urllib.parse import urlparse

raw = sys.argv[1]
parsed = urlparse(raw)
user = parsed.username or "postgres"
password = parsed.password or ""
host = parsed.hostname or "127.0.0.1"
port = parsed.port or 5432
db = (parsed.path or "/postgres").lstrip("/") or "postgres"
print(f"PG_USER={user}")
print(f"PG_PASS={password}")
print(f"PG_HOST={host}")
print(f"PG_PORT={port}")
print(f"PG_DB={db}")
PY
}

http_status() {
  local url="$1"
  curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 15 "$url" 2>/dev/null || echo "000"
}

git_short_hash() {
  local dir="$1"
  if [[ -d "${dir}/.git" ]]; then
    git -C "$dir" rev-parse --short HEAD 2>/dev/null || echo "unknown"
  else
    echo "n/a"
  fi
}

is_port_listening() {
  local port="$1"
  local host="${2:-127.0.0.1}"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :${port}" 2>/dev/null | grep -q ":${port} " && return 0
  fi
  if command -v nc >/dev/null 2>&1; then
    nc -z "$host" "$port" >/dev/null 2>&1 && return 0
  fi
  return 1
}

ensure_git_ff_pull() {
  local dir="$1"
  local branch="$2"
  shift 2
  local -a protected_paths=("$@")

  step "Git update in ${dir} (branch ${branch})"
  [[ -d "${dir}/.git" ]] || die "Not a git repository: ${dir}"

  local dirty
  dirty="$(git -C "$dir" status --porcelain 2>/dev/null || true)"
  if [[ -n "$dirty" ]]; then
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      local path="${line:3}"
      local allowed=0
      for protected in "${protected_paths[@]}"; do
        if [[ "$path" == "$protected" || "$path" == "${protected}/"* ]]; then
          allowed=1
          break
        fi
      done
      if [[ "$allowed" -eq 0 ]]; then
        die "Repository ${dir} has local changes in '${path}'. Commit/stash before deploy."
      fi
      warn "Preserving local server config change: ${dir}/${path}"
    done <<< "$dirty"
  fi

  git -C "$dir" fetch origin
  if git -C "$dir" show-ref --verify --quiet "refs/heads/${branch}"; then
    git -C "$dir" checkout "${branch}"
  elif git -C "$dir" show-ref --verify --quiet "refs/remotes/origin/${branch}"; then
    git -C "$dir" checkout -B "${branch}" "origin/${branch}"
  else
    die "Branch '${branch}' not found in ${dir}"
  fi
  git -C "$dir" pull --ff-only origin "${branch}"
}

FAIR_CRM_SAFE_DEPLOY_RESTORE_PATHS=(
  "scripts/server/bootstrap-server.sh"
  "scripts/server/deploy-all.sh"
  "scripts/server/check-server.sh"
  "scripts/server/systemd"
  "scripts/server/nginx"
)

FAIR_CRM_SERVER_EXECUTABLE_SCRIPTS=(
  "scripts/server/bootstrap-server.sh"
  "scripts/server/deploy-all.sh"
  "scripts/server/check-server.sh"
  "scripts/server/run-restore-job.sh"
)

ensure_fair_crm_server_scripts_executable() {
  local dir="$1"
  local rel script_path
  for rel in "${FAIR_CRM_SERVER_EXECUTABLE_SCRIPTS[@]}"; do
    script_path="${dir}/${rel}"
    if [[ -f "$script_path" ]]; then
      chmod +x "$script_path"
    fi
  done
}

restore_safe_fair_crm_deploy_files() {
  local dir="$1"
  REPORT_SAFE_DEPLOY_RESTORE="${REPORT_SAFE_DEPLOY_RESTORE:-not run}"

  [[ -d "${dir}/.git" ]] || return 0

  step "Restore safe deploy files before git pull"
  local dirty
  dirty="$(
    git -C "$dir" status --porcelain -- "${FAIR_CRM_SAFE_DEPLOY_RESTORE_PATHS[@]}" 2>/dev/null || true
  )"
  if [[ -z "$dirty" ]]; then
    REPORT_SAFE_DEPLOY_RESTORE="none needed"
    log "No safe deploy file changes to restore"
  else
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      log "Restoring safe deploy path: ${line:3}"
    done <<< "$dirty"

    if git -C "$dir" checkout HEAD -- "${FAIR_CRM_SAFE_DEPLOY_RESTORE_PATHS[@]}" 2>/dev/null; then
      :
    elif git -C "$dir" restore --source=HEAD --worktree --staged -- "${FAIR_CRM_SAFE_DEPLOY_RESTORE_PATHS[@]}" 2>/dev/null; then
      :
    else
      die "Failed to restore safe deploy files in ${dir}"
    fi

    REPORT_SAFE_DEPLOY_RESTORE="safe deploy files restored before git pull"
    log "${REPORT_SAFE_DEPLOY_RESTORE}"
  fi

  ensure_fair_crm_server_scripts_executable "$dir"
}

copy_env_if_missing() {
  local example="$1"
  local target="$2"
  if [[ -f "$target" ]]; then
    log "Preserving existing env: ${target}"
    return 0
  fi
  if [[ ! -f "$example" ]]; then
    warn "Env example missing: ${example}"
    return 0
  fi
  cp "$example" "$target"
  warn "Created ${target} from example — review secrets and URLs before production use"
}

ensure_core_backend_env() {
  local core_dir="${1:-${KYROX_CORE_DIR}}"
  local backend_env="${core_dir}/backend/.env"
  local backend_example="${core_dir}/backend/.env.example"
  local root_env="${core_dir}/.env"
  local root_example="${core_dir}/.env.example"

  if [[ -f "$backend_env" ]]; then
    log "Preserving existing Core env: ${backend_env}"
    return 0
  fi

  if [[ ! -d "$core_dir" ]]; then
    warn "Core checkout not present at ${core_dir}; cannot create backend/.env"
    return 1
  fi

  mkdir -p "${core_dir}/backend"

  if [[ -f "$backend_example" ]]; then
    cp "$backend_example" "$backend_env"
    warn "Created ${backend_env} from backend/.env.example"
    return 0
  fi

  if [[ -f "$root_env" ]]; then
    cp "$root_env" "$backend_env"
    warn "Created ${backend_env} from legacy ${root_env}"
    return 0
  fi

  if [[ -f "$root_example" ]]; then
    cp "$root_example" "$backend_env"
    warn "Created ${backend_env} from ${root_example}"
    return 0
  fi

  warn "Core env example missing; expected ${backend_example} or ${root_example}"
  return 1
}

detect_server_public_url() {
  local configured="${SERVER_PUBLIC_URL:-}"
  if [[ -n "$configured" ]]; then
    printf '%s' "${configured%/}"
    return 0
  fi
  local ip
  ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  if [[ -n "$ip" ]]; then
    printf '%s' "http://${ip}"
    return 0
  fi
  printf '%s' "http://127.0.0.1"
}

write_frontend_production_env_if_missing() {
  local fair_dir="$1"
  local target="${fair_dir}/frontend/.env.production"
  if [[ -f "$target" ]]; then
    log "Preserving existing frontend env: ${target}"
    return 0
  fi

  local public_url
  public_url="$(detect_server_public_url)"
  cat >"$target" <<EOF
VITE_API_BASE_URL=${public_url}
VITE_CORE_BASE_URL=${public_url}/kyrox-core
VITE_APP_ENV=production
VITE_DEV_BYPASS_ENABLED=false
VITE_ORGANIZATION_ID=00000000-0000-4000-8000-000000000010
EOF
  warn "Created ${target} with SERVER_PUBLIC_URL=${public_url} — adjust if using a domain name"
}

validate_env_files_required() {
  step "Validate Core and Fair CRM .env files"
  local core_env="${KYROX_CORE_DIR}/backend/.env"
  local fair_env="${FAIR_CRM_DIR}/backend/.env"

  [[ -f "$core_env" ]] || die "Missing Core env file: ${core_env}"
  [[ -f "$fair_env" ]] || die "Missing Fair CRM env file: ${fair_env}"

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

validate_env_files_check() {
  local core_env="${KYROX_CORE_DIR}/backend/.env"
  local fair_env="${FAIR_CRM_DIR}/backend/.env"

  if [[ ! -f "$core_env" ]]; then
    check_fail "Core .env present"
    return 0
  fi
  check_pass "Core .env present"

  if [[ ! -f "$fair_env" ]]; then
    check_fail "Fair CRM .env present"
    return 0
  fi
  check_pass "Fair CRM .env present"

  local core_jwt fair_jwt fair_core_url
  core_jwt="$(read_env_key "$core_env" JWT_SECRET_KEY || true)"
  fair_jwt="$(read_env_key "$fair_env" JWT_SECRET_KEY || true)"
  fair_core_url="$(read_env_key "$fair_env" KYROX_CORE_BASE_URL || true)"

  if [[ -z "$core_jwt" || -z "$fair_jwt" ]]; then
    check_fail "JWT_SECRET_KEY configured in both .env files"
  elif [[ "$core_jwt" != "$fair_jwt" ]]; then
    check_fail "JWT_SECRET_KEY match between Core and Fair CRM"
  else
    check_pass "JWT_SECRET_KEY match between Core and Fair CRM"
  fi

  if [[ -z "$fair_core_url" || "$fair_core_url" == "http://127.0.0.1:8000" || "$fair_core_url" == "http://localhost:8000" ]]; then
    check_pass "Fair CRM KYROX_CORE_BASE_URL=http://127.0.0.1:8000"
  else
    check_warn_item "Fair CRM KYROX_CORE_BASE_URL is ${fair_core_url} (expected http://127.0.0.1:8000)"
  fi
}

ensure_python_venv() {
  local venv_dir="$1"
  if [[ ! -d "${venv_dir}/bin" ]]; then
    log "Creating venv at ${venv_dir}"
    python3 -m venv "${venv_dir}"
  fi
}

pip_install_requirements() {
  local venv_dir="$1"
  local requirements_file="$2"
  [[ -f "$requirements_file" ]] || die "requirements.txt not found: ${requirements_file}"
  "${venv_dir}/bin/pip" install --upgrade pip wheel
  "${venv_dir}/bin/pip" install -r "$requirements_file"
}

resolve_requirements_file() {
  local project_dir="$1"
  if [[ -f "${project_dir}/requirements.txt" ]]; then
    printf '%s\n' "${project_dir}/requirements.txt"
    return 0
  fi
  if [[ -f "${project_dir}/backend/requirements.txt" ]]; then
    printf '%s\n' "${project_dir}/backend/requirements.txt"
    return 0
  fi
  return 1
}

run_alembic_upgrade() {
  local project_root="$1"
  local venv_python="$2"
  local alembic_ini="${3:-alembic.ini}"
  local database_url="${4:-}"

  step "Alembic upgrade head in ${project_root}"
  if [[ -f "${project_root}/${alembic_ini}" ]]; then
    local -a env_args=()
    if [[ -n "$database_url" ]]; then
      env_args+=(DATABASE_URL="$database_url")
    fi
    (
      cd "$project_root"
      env "${env_args[@]}" PYTHONPATH="${project_root}/backend" \
        "$venv_python" -m alembic -c "$alembic_ini" upgrade head
    )
    return 0
  fi

  log "No ${alembic_ini} in ${project_root}; running programmatic alembic"
  (
    cd "$project_root"
    env PYTHONPATH="${project_root}/backend" \
      "$venv_python" - <<'PY'
from alembic.config import Config
from alembic import command
from pathlib import Path

root = Path.cwd()
cfg = Config()
cfg.set_main_option("script_location", str(root / "backend" / "alembic"))
cfg.set_main_option("prepend_sys_path", str(root / "backend"))
command.upgrade(cfg, "head")
PY
  )
}

alembic_revision_snapshot() {
  local project_root="$1"
  local venv_python="$2"
  local database_url="$3"
  local mode="$4"

  if [[ ! -x "$venv_python" ]]; then
    printf '%s\n' "missing-venv"
    return 0
  fi

  local alembic_ini="${project_root}/alembic.ini"
  local -a env_args=(PYTHONPATH="${project_root}/backend")
  if [[ -n "$database_url" ]]; then
    env_args+=(DATABASE_URL="$database_url")
  fi

  if [[ -f "$alembic_ini" ]]; then
    (
      cd "$project_root"
      env "${env_args[@]}" "$venv_python" -m alembic -c alembic.ini "$mode" 2>/dev/null || true
    )
    return 0
  fi

  (
    cd "$project_root"
    env "${env_args[@]}" "$venv_python" - <<PY
from alembic.config import Config
from alembic import command
from pathlib import Path

root = Path.cwd()
cfg = Config()
cfg.set_main_option("script_location", str(root / "backend" / "alembic"))
cfg.set_main_option("prepend_sys_path", str(root / "backend"))
command.${mode}(cfg)
PY
  ) 2>/dev/null || true
}

alembic_pick_revision() {
  tr -d '\r' | grep -oE '[0-9]{8}_[0-9]{4}[^ ]*|[0-9]{4}(_[0-9]{4})?' | tail -n 1
}

check_alembic_at_head() {
  local label="$1"
  local project_root="$2"
  local venv_python="$3"
  local database_url="$4"

  if [[ ! -d "$project_root" ]]; then
    check_warn_item "migration:${label}" "project directory missing"
    return 0
  fi

  local current heads
  current="$(alembic_revision_snapshot "$project_root" "$venv_python" "$database_url" "current" | alembic_pick_revision)"
  heads="$(alembic_revision_snapshot "$project_root" "$venv_python" "" "heads" | alembic_pick_revision)"

  if [[ -z "$current" || "$current" == "missing-venv" ]]; then
    check_fail "${label} migration at head (could not read alembic current)"
    return 0
  fi
  if [[ -z "$heads" ]]; then
    check_warn_item "${label} migration heads readable"
    return 0
  fi

  if [[ "$current" == "$heads" ]]; then
    check_pass "${label} migration at head (${current})"
  else
    check_fail "${label} migration at head (current=${current}, head=${heads})"
  fi
}

render_template() {
  local template="$1"
  local output="$2"
  sed \
    -e "s|@DEPLOY_SERVICE_USER@|${DEPLOY_SERVICE_USER}|g" \
    -e "s|@KYROX_CORE_DIR@|${KYROX_CORE_DIR}|g" \
    -e "s|@FAIR_CRM_DIR@|${FAIR_CRM_DIR}|g" \
    -e "s|@SERVER_PUBLIC_URL@|${SERVER_PUBLIC_URL:-$(detect_server_public_url)}|g" \
    "$template" >"$output"
}

install_systemd_unit() {
  local template="$1"
  local service_name="$2"
  local dest="/etc/systemd/system/${service_name}"
  step "Install systemd unit ${service_name}"
  [[ -f "$template" ]] || die "systemd template missing: ${template}"
  if [[ "${EUID}" -ne 0 ]]; then
    warn "Not running as root; skipping systemd install for ${service_name}"
    return 0
  fi
  cp "$template" "$dest"
  chmod 644 "$dest"
}

check_systemd_service() {
  local service="$1"
  local label="$2"
  if ! command -v systemctl >/dev/null 2>&1; then
    check_warn_item "${label} service active"
    return 0
  fi
  if ! systemctl list-unit-files "${service}" >/dev/null 2>&1; then
    check_fail "${label} service active"
    return 0
  fi
  local active enabled
  active="$(systemctl is-active "${service}" 2>/dev/null || echo unknown)"
  enabled="$(systemctl is-enabled "${service}" 2>/dev/null || echo unknown)"
  if [[ "$active" == "active" && "$enabled" == "enabled" ]]; then
    check_pass "${label} service active"
  elif [[ "$active" == "active" ]]; then
    check_warn_item "${label} service enabled (enabled=${enabled})"
  else
    check_fail "${label} service active (active=${active}, enabled=${enabled})"
  fi
}

parse_compose_postgres() {
  local compose_file="$1"
  COMPOSE_PG_USER="postgres"
  COMPOSE_PG_PASS="postgres"
  COMPOSE_PG_PORT="5432"
  COMPOSE_PG_CONTAINER=""

  [[ -f "$compose_file" ]] || return 0

  local user_line pass_line port_line container_line
  user_line="$(grep -E 'POSTGRES_USER:' "$compose_file" | head -n 1 || true)"
  pass_line="$(grep -E 'POSTGRES_PASSWORD:' "$compose_file" | head -n 1 || true)"
  port_line="$(grep -E '^[[:space:]]*-[[:space:]]*"(127\.0\.0\.1:)?[0-9]+:5432"' "$compose_file" | head -n 1 || true)"
  container_line="$(grep -E 'container_name:' "$compose_file" | head -n 1 || true)"

  if [[ -n "$user_line" ]]; then
    COMPOSE_PG_USER="$(echo "$user_line" | sed -E 's/.*POSTGRES_USER:[[:space:]]*//; s/[[:space:]]+$//')"
  fi
  if [[ -n "$pass_line" ]]; then
    COMPOSE_PG_PASS="$(echo "$pass_line" | sed -E 's/.*POSTGRES_PASSWORD:[[:space:]]*//; s/[[:space:]]+$//')"
  fi
  if [[ -n "$port_line" ]]; then
    COMPOSE_PG_PORT="$(echo "$port_line" | sed -E 's/.*"(127\.0\.0\.1:)?([0-9]+):5432".*/\2/')"
  fi
  if [[ -n "$container_line" ]]; then
    COMPOSE_PG_CONTAINER="$(echo "$container_line" | sed -E 's/.*container_name:[[:space:]]*//; s/[[:space:]]+$//')"
  fi
}

ensure_compose_localhost_postgres_bind() {
  local fair_dir="$1"
  local compose_file="${fair_dir}/docker-compose.yml"
  [[ -f "$compose_file" ]] || return 1

  if grep -qE '^[[:space:]]*-[[:space:]]*"127\.0\.0\.1:5432:5432"' "$compose_file"; then
    log "Postgres compose port already bound to 127.0.0.1:5432"
    return 1
  fi

  if grep -qE '^[[:space:]]*-[[:space:]]*"(5432:5432|0\.0\.0\.0:5432:5432)"' "$compose_file"; then
    step "Patch docker-compose Postgres port to 127.0.0.1:5432 (localhost only)"
    sed -i.bak -E 's/"5432:5432"/"127.0.0.1:5432:5432"/; s/"0\.0\.0\.0:5432:5432"/"127.0.0.1:5432:5432"/' "$compose_file"
    rm -f "${compose_file}.bak"
    log "Updated ${compose_file} Postgres binding to 127.0.0.1:5432"
    return 0
  fi

  warn "Postgres port mapping in ${compose_file} is custom; expected 127.0.0.1:5432:5432"
  return 1
}

ensure_postgres_container() {
  local fair_dir="$1"
  local compose_file="${fair_dir}/docker-compose.yml"
  if [[ ! -f "$compose_file" ]]; then
    warn "No docker-compose.yml at ${compose_file}; assuming external PostgreSQL"
    return 0
  fi
  require_cmd docker
  local recreate=0
  if ensure_compose_localhost_postgres_bind "$fair_dir"; then
    recreate=1
  fi
  step "Ensure Postgres container is up (docker compose; local compose file preserved)"
  (
    cd "$fair_dir"
    if [[ "$recreate" -eq 1 ]]; then
      docker compose up -d postgres --force-recreate
    else
      docker compose up -d postgres
    fi
  )
}

check_docker_postgres() {
  local fair_dir="$1"
  local compose_file="${fair_dir}/docker-compose.yml"
  if [[ ! -f "$compose_file" ]]; then
    check_warn_item "PostgreSQL container running (external DB assumed)"
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    check_fail "Docker installed"
    return 0
  fi
  check_pass "Docker installed"

  if ! run_root systemctl is-active docker >/dev/null 2>&1; then
    check_fail "Docker service active"
    return 0
  fi
  check_pass "Docker service active"

  parse_compose_postgres "$compose_file"
  local container="${COMPOSE_PG_CONTAINER:-kyrox-postgres-dev}"
  if docker ps --format '{{.Names}}' | grep -qx "$container"; then
    check_pass "PostgreSQL container running"
  else
    check_fail "PostgreSQL container running"
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
    "SELECT COUNT(*) FROM pg_database WHERE datname='${db_name}'" 2>/dev/null || echo 0)"
  [[ "${count}" == "1" ]]
}

ensure_database() {
  local db_name="$1"
  if database_exists "$db_name"; then
    log "Database exists: ${db_name} (no drop/truncate/reset)"
  else
    log "Creating database: ${db_name}"
    psql_admin_exec "CREATE DATABASE \"${db_name}\";"
  fi
}

ensure_repo_data_dirs() {
  local fair_dir="$1"
  step "Ensure backup/restore data directories exist (create only; never delete contents)"
  local dir
  for dir in \
    "${fair_dir}/backups" \
    "${fair_dir}/data/restore_uploads" \
    "${fair_dir}/data/restore_logs"; do
    if [[ -d "$dir" ]]; then
      log "Preserving existing data directory: ${dir}"
    else
      mkdir -p "$dir"
      warn "Created empty data directory: ${dir}"
    fi
  done
}

check_database_exists() {
  local db_name="$1"
  if database_exists "$db_name"; then
    check_pass "${db_name} DB exists"
  else
    check_fail "${db_name} DB exists"
  fi
}

resolve_postgres_connection() {
  local fair_dir="$1"
  local core_dir="$2"
  step "Resolve PostgreSQL connection settings"
  parse_compose_postgres "${fair_dir}/docker-compose.yml"

  PG_HOST="127.0.0.1"
  PG_PORT="${COMPOSE_PG_PORT}"
  PG_USER="${COMPOSE_PG_USER}"
  PG_PASS="${COMPOSE_PG_PASS}"

  local fair_env="${fair_dir}/backend/.env"
  local core_env="${core_dir}/backend/.env"
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

check_postgres_connectivity() {
  if PGPASSWORD="${PG_PASS}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres -c "SELECT 1" >/dev/null 2>&1; then
    check_pass "PostgreSQL reachable at ${PG_HOST}:${PG_PORT}"
  else
    check_fail "PostgreSQL reachable at ${PG_HOST}:${PG_PORT}"
  fi
}

install_apt_packages() {
  step "Install OS packages (apt)"
  require_cmd apt-get
  run_root apt-get update -qq
  run_root apt-get install -y -qq \
    ca-certificates curl git gnupg \
    nginx postgresql-client ufw \
    python3 python3-pip python3-venv
}

ensure_nodejs() {
  step "Ensure Node.js + npm"
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    log "node $(node --version), npm $(npm --version)"
    return 0
  fi
  require_cmd apt-get
  run_root apt-get update -qq
  run_root apt-get install -y -qq nodejs npm
}

ensure_docker() {
  step "Ensure Docker Engine + compose plugin"
  if ! command -v docker >/dev/null 2>&1; then
    require_cmd apt-get
    run_root apt-get update -qq
    run_root apt-get install -y -qq docker.io docker-compose-v2 \
      || run_root apt-get install -y -qq docker.io docker-compose-plugin
  fi
  run_root systemctl enable docker
  run_root systemctl start docker
  if id -nG "${DEPLOY_SERVICE_USER}" 2>/dev/null | grep -qw docker; then
    log "User ${DEPLOY_SERVICE_USER} already in docker group"
  else
    run_root usermod -aG docker "${DEPLOY_SERVICE_USER}"
    warn "Added ${DEPLOY_SERVICE_USER} to docker group — re-login required for non-root docker"
  fi
}

ensure_ufw_firewall() {
  step "Configure UFW firewall (SSH + HTTP public; API/DB local only)"
  if ! command -v ufw >/dev/null 2>&1; then
    require_cmd apt-get
    run_root apt-get install -y -qq ufw
  fi
  run_root ufw allow OpenSSH
  run_root ufw allow 80/tcp comment 'Fair CRM nginx'
  if ufw status 2>/dev/null | grep -q "Status: inactive"; then
    run_root ufw --force enable
  fi
  log "UFW rules: OpenSSH + 80/tcp (8000/8001/5432 not opened)"
}

check_firewall_rules() {
  if ! command -v ufw >/dev/null 2>&1; then
    check_warn_item "UFW installed"
    return 0
  fi
  local status
  status="$(ufw status 2>/dev/null || true)"
  if grep -q "Status: active" <<<"$status"; then
    check_pass "UFW active"
  else
    check_warn_item "UFW active"
  fi

  if grep -E '(22/tcp|OpenSSH).*ALLOW|22.*ALLOW' <<<"$status" >/dev/null; then
    check_pass "22 allowed"
  else
    check_warn_item "22 allowed"
  fi

  if grep -E '80/tcp.*ALLOW|80.*ALLOW' <<<"$status" >/dev/null; then
    check_pass "80 allowed"
  else
    check_warn_item "80 allowed"
  fi

  if grep -E '443/tcp.*ALLOW|443.*ALLOW' <<<"$status" >/dev/null; then
    check_pass "443 allowed"
  else
    check_warn_item "443 not configured"
  fi

  local port
  for port in 5432 8000 8001; do
    if grep -E "${port}/tcp" <<<"$status" | grep -q ALLOW; then
      check_fail "${port} not publicly exposed"
    else
      check_pass "${port} not publicly exposed"
    fi
  done
}

check_required_commands() {
  local cmd
  for cmd in git python3 curl psql docker nginx node npm; do
    if command -v "$cmd" >/dev/null 2>&1; then
      check_pass "${cmd} installed"
    else
      if [[ "$cmd" == "git" || "$cmd" == "python3" || "$cmd" == "curl" || "$cmd" == "psql" ]]; then
        check_fail "${cmd} installed"
      else
        check_warn_item "${cmd} installed"
      fi
    fi
  done
}

get_port_listeners() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk -v p=":${port}" '$4 ~ p "$" { print $4 }'
    return 0
  fi
  return 1
}

check_port_binding_local_only() {
  local port="$1"
  local label="$2"
  local listeners
  listeners="$(get_port_listeners "$port" | paste -sd ',' - || true)"

  if [[ -z "$listeners" ]]; then
    check_fail "${label} binding 127.0.0.1:${port}"
    return 0
  fi

  if grep -qE '(0\.0\.0\.0|\[::\]):'"${port}" <<<"$listeners"; then
    if [[ "$label" == "PostgreSQL" ]]; then
      check_warn_item "${label} binding publicly exposed (${listeners}) — prefer 127.0.0.1:${port} in docker-compose"
    else
      check_fail "${label} binding publicly exposed (${listeners})"
    fi
  elif grep -q "127.0.0.1:${port}" <<<"$listeners"; then
    check_pass "${label} binding 127.0.0.1:${port}"
  else
    check_warn_item "${label} binding (${listeners})"
  fi
}

check_port_binding_public() {
  local port="$1"
  local label="$2"
  local listeners
  listeners="$(get_port_listeners "$port" | paste -sd ',' - || true)"

  if [[ -z "$listeners" ]]; then
    check_fail "${label} public ${port}"
    return 0
  fi

  if grep -qE '(0\.0\.0\.0|\[::\]):'"${port}" <<<"$listeners" || grep -q ":${port}" <<<"$listeners"; then
    check_pass "${label} public ${port} (${listeners})"
  else
    check_warn_item "${label} public ${port} (${listeners})"
  fi
}

check_postgres_port_binding() {
  local port="${COMPOSE_PG_PORT:-5432}"
  local listeners
  listeners="$(get_port_listeners "$port" | paste -sd ',' - || true)"

  if [[ -z "$listeners" ]]; then
    check_fail "PostgreSQL bound to 127.0.0.1:${port}"
    check_fail "5432 not publicly exposed"
    return 0
  fi

  if grep -q "127.0.0.1:${port}" <<<"$listeners"; then
    check_pass "PostgreSQL bound to 127.0.0.1:${port}"
    check_pass "5432 not publicly exposed"
    return 0
  fi

  if grep -qE '(0\.0\.0\.0|\[::\]):'"${port}" <<<"$listeners"; then
    check_warn_item "PostgreSQL bound to 127.0.0.1:${port} (currently ${listeners})"
    check_fail "5432 not publicly exposed"
    return 0
  fi

  check_warn_item "PostgreSQL bound to 127.0.0.1:${port} (listeners: ${listeners})"
  check_warn_item "5432 not publicly exposed"
}

check_port_bindings() {
  parse_compose_postgres "${FAIR_CRM_DIR}/docker-compose.yml"
  check_postgres_port_binding
  check_port_binding_local_only "8000" "KYROX Core"
  check_port_binding_local_only "8001" "Fair CRM"
  check_port_binding_public "80" "Nginx"
  if get_port_listeners "443" | grep -q .; then
    check_port_binding_public "443" "Nginx HTTPS"
  else
    check_warn_item "Nginx HTTPS 443 not listening"
  fi
}

install_nginx_site() {
  local template="$1"
  local site_name="${2:-fair-crm}"
  local available="/etc/nginx/sites-available/${site_name}"
  local enabled="/etc/nginx/sites-enabled/${site_name}"
  local rendered
  rendered="$(mktemp)"

  step "Install nginx site ${site_name}"
  [[ -f "$template" ]] || die "nginx template missing: ${template}"
  render_template "$template" "$rendered"

  if [[ -f "$available" ]] && ! cmp -s "$rendered" "$available"; then
    warn "Preserving existing nginx config: ${available}"
    rm -f "$rendered"
  else
    run_root cp "$rendered" "$available"
    run_root chmod 644 "$available"
    log "Installed nginx site: ${available}"
    rm -f "$rendered"
  fi

  if [[ ! -L "$enabled" ]]; then
    run_root ln -sf "$available" "$enabled"
  fi
  if [[ -L /etc/nginx/sites-enabled/default ]]; then
    run_root rm -f /etc/nginx/sites-enabled/default
  fi

  run_root nginx -t
  run_root systemctl enable nginx
  run_root systemctl reload nginx
}

reload_nginx_if_installed() {
  if command -v nginx >/dev/null 2>&1 && [[ -d /etc/nginx/sites-enabled ]]; then
    step "Reload nginx"
    run_root nginx -t
    run_root systemctl reload nginx
  fi
}

check_nginx_site() {
  if ! command -v nginx >/dev/null 2>&1; then
    check_fail "nginx installed"
    return 0
  fi
  check_pass "nginx installed"

  local nginx_test_output nginx_test_rc=0
  nginx_test_output="$(run_root nginx -t 2>&1)" || nginx_test_rc=$?
  if [[ "$nginx_test_rc" -eq 0 ]]; then
    check_pass "nginx -t syntax OK"
  else
    check_fail "nginx -t failed"
  fi

  if [[ -f /etc/nginx/sites-enabled/fair-crm || -L /etc/nginx/sites-enabled/fair-crm ]]; then
    check_pass "nginx fair-crm site enabled"
  else
    check_warn_item "nginx fair-crm site enabled"
  fi

  if run_root systemctl is-active nginx >/dev/null 2>&1; then
    check_pass "nginx service active"
  else
    check_fail "nginx service active"
  fi
}

wait_for_http_health() {
  local core_url="$1"
  local fair_url="$2"
  local timeout="${3:-60}"
  local core_status="000"
  local fair_status="000"
  local deadline=$((SECONDS + timeout))

  while (( SECONDS < deadline )); do
    core_status="$(http_status "$core_url")"
    fair_status="$(http_status "$fair_url")"
    if [[ "$core_status" == "200" && "$fair_status" == "200" ]]; then
      printf '%s %s' "$core_status" "$fair_status"
      return 0
    fi
    sleep 2
  done
  printf '%s %s' "$core_status" "$fair_status"
  return 1
}

check_http_endpoints() {
  local core_url="$1"
  local fair_url="$2"
  local public_url="${3:-}"

  local core_status fair_status
  core_status="$(http_status "$core_url")"
  fair_status="$(http_status "$fair_url")"

  if [[ "$core_status" == "200" ]]; then
    check_pass "Core health ${core_status}"
  else
    check_fail "Core health ${core_status}"
  fi

  if [[ "$fair_status" == "200" ]]; then
    check_pass "Fair CRM health ${fair_status}"
  else
    check_fail "Fair CRM health ${fair_status}"
  fi

  if [[ -n "$public_url" ]]; then
    local ui_status
    ui_status="$(http_status "${public_url}/")"
    if [[ "$ui_status" == "200" ]]; then
      check_pass "Frontend ${ui_status}"
    else
      check_fail "Frontend ${ui_status}"
    fi
  fi
}

login_smoke_parse_response_body() {
  local body_file="$1"
  python3 -c '
import json
import sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
except OSError as exc:
    print(f"read_error={exc}")
    raise SystemExit(1)

if not raw.strip():
    print("empty_body")
    raise SystemExit(1)

try:
    data = json.loads(raw)
except json.JSONDecodeError as exc:
    preview = raw.replace("\n", " ").replace("\r", " ")[:300]
    print(f"json_error={exc}; raw={preview}")
    raise SystemExit(1)

if data.get("access_token"):
    print("ok")
    raise SystemExit(0)

preview = raw.replace("\n", " ").replace("\r", " ")[:300]
print(f"missing_access_token; raw={preview}")
raise SystemExit(1)
' "$body_file"
}

run_login_smoke_test() {
  local core_port="${1:-8000}"
  local fail_mode="${2:-check}"
  local url="http://127.0.0.1:${core_port}/api/v1/auth/login"
  local tmp_body tmp_payload tmp_curl_err
  local http_code curl_rc=0 body_preview parse_detail parse_rc=0
  local attempt max_attempts=5

  tmp_body="$(mktemp -t login-smoke-body.XXXXXX)"
  tmp_payload="$(mktemp -t login-smoke-payload.XXXXXX)"
  tmp_curl_err="$(mktemp -t login-smoke-curl.XXXXXX)"

  LOGIN_SMOKE_FAIL_DETAIL=""

  _login_smoke_cleanup() {
    rm -f "$tmp_body" "$tmp_payload" "$tmp_curl_err"
  }

  _login_smoke_fail() {
    local status="$1"
    local body="$2"
    local extra="${3:-}"
    LOGIN_SMOKE_FAIL_DETAIL="status=${status}, body=${body}"
    if [[ -n "$extra" ]]; then
      LOGIN_SMOKE_FAIL_DETAIL="${LOGIN_SMOKE_FAIL_DETAIL}, ${extra}"
    fi
    _login_smoke_cleanup
    if [[ "$fail_mode" != "deploy" ]]; then
      check_fail "Login smoke test failed (${LOGIN_SMOKE_FAIL_DETAIL})"
    fi
    return 1
  }

  export DEV_LOGIN_EMAIL DEV_LOGIN_PASSWORD
  python3 -c 'import json, os, sys; json.dump({"email": os.environ["DEV_LOGIN_EMAIL"], "password": os.environ["DEV_LOGIN_PASSWORD"]}, sys.stdout)' \
    >"$tmp_payload"

  http_code="000"
  curl_rc=0
  parse_detail=""

  for (( attempt=1; attempt<=max_attempts; attempt++ )); do
    : >"$tmp_body"
    : >"$tmp_curl_err"
    curl_rc=0
    http_code="$(
      curl -sS -o "$tmp_body" -w '%{http_code}' -X POST "$url" \
        -H "Content-Type: application/json" \
        --data-binary "@${tmp_payload}" \
        --connect-timeout 10 --max-time 30 2>"$tmp_curl_err"
    )" || curl_rc=$?

    body_preview="$(tr -d '\n\r' <"$tmp_body" 2>/dev/null | head -c 300)"
    [[ -n "$body_preview" ]] || body_preview="empty"

    if [[ "$curl_rc" -ne 0 ]]; then
      if [[ "$attempt" -lt "$max_attempts" ]]; then
        sleep 2
        continue
      fi
      local curl_error
      curl_error="$(tr -d '\n\r' <"$tmp_curl_err" 2>/dev/null | head -c 200)"
      _login_smoke_fail "${http_code:-000}" "$body_preview" "curl_error=${curl_error:-unknown}"
      return 1
    fi

    if [[ -z "$http_code" || "$http_code" == "000" ]]; then
      if [[ "$attempt" -lt "$max_attempts" ]]; then
        sleep 2
        continue
      fi
      _login_smoke_fail "000" "$body_preview"
      return 1
    fi

    if [[ "$http_code" != "200" ]]; then
      if [[ "$attempt" -lt "$max_attempts" ]]; then
        sleep 2
        continue
      fi
      _login_smoke_fail "$http_code" "$body_preview"
      return 1
    fi

    if [[ ! -s "$tmp_body" ]]; then
      if [[ "$attempt" -lt "$max_attempts" ]]; then
        sleep 2
        continue
      fi
      _login_smoke_fail "$http_code" "empty"
      return 1
    fi

    parse_rc=0
    parse_detail="$(login_smoke_parse_response_body "$tmp_body" 2>&1)" || parse_rc=$?
    if [[ "$parse_rc" -eq 0 ]]; then
      break
    fi

    if [[ "$attempt" -lt "$max_attempts" ]]; then
      sleep 2
      continue
    fi

    _login_smoke_fail "$http_code" "$body_preview" "${parse_detail:-parse_failed}"
    return 1
  done

  _login_smoke_cleanup
  if [[ "$fail_mode" != "deploy" ]]; then
    check_pass "Login smoke test passed"
  fi
  return 0
}

print_core_seed_identity_report() {
  echo ""
  echo "Core dev seed identity (idempotent):"
  echo "  email: ${DEV_LOGIN_EMAIL}"
  echo "  password: ${DEV_LOGIN_PASSWORD}"
  echo "  org id: ${DEV_LOGIN_ORG_ID}"
  echo "  role: owner/admin"
  echo "  permissions: all fair_crm.* permissions in Core catalog"
  echo "  behavior: safe to re-run; creates or updates user/org/role mappings"
}

print_systemd_service_summary() {
  local script_dir="$1"
  local -a units=(
    "kyrox-core.service#8000#${KYROX_CORE_DIR}"
    "fair-crm-backend.service#8001#${FAIR_CRM_DIR}"
  )
  local entry service port root_dir template
  for entry in "${units[@]}"; do
    IFS='#' read -r service port root_dir <<<"$entry"
    template="${script_dir}/systemd/${service}"
    echo "scripts/server/systemd/${service}"
    echo "  bind: 127.0.0.1"
    echo "  port: ${port}"
    if [[ -f "$template" ]]; then
      echo "  Restart=$(grep -E '^Restart=' "$template" | head -n1 | cut -d= -f2-)"
      echo "  RestartSec=$(grep -E '^RestartSec=' "$template" | head -n1 | cut -d= -f2-)"
      echo "  WorkingDirectory=${root_dir}/backend"
      echo "  EnvironmentFile=${root_dir}/backend/.env"
      if [[ "$service" == "kyrox-core.service" ]]; then
        echo "  ExecStart=${KYROX_CORE_DIR}/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${port}"
      else
        echo "  ExecStart=${FAIR_CRM_DIR}/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${port}"
      fi
    fi
    echo ""
  done
}

print_systemd_service_audit() {
  print_systemd_service_summary "$1"
  local script_dir="$1"
  local installed
  for service in kyrox-core.service fair-crm-backend.service; do
    installed="/etc/systemd/system/${service}"
    local port="8000"
    [[ "$service" == "fair-crm-backend.service" ]] && port="8001"
    if [[ -f "$installed" ]]; then
      if grep -q '127.0.0.1' "$installed" && grep -q 'Restart=always' "$installed"; then
        check_pass "${service} unit configured (127.0.0.1:${port}, Restart=always)"
      else
        check_warn_item "${service} unit configured (verify bind/Restart in ${installed})"
      fi
    else
      check_fail "${service} unit installed"
    fi
  done
}

print_nginx_config_audit() {
  local fair_dir="$1"
  echo ""
  echo "nginx routing audit:"
  echo "  /              -> ${fair_dir}/frontend/dist"
  echo "  /api/          -> Fair CRM backend 127.0.0.1:8001"
  echo "  /kyrox-core/   -> KYROX Core 127.0.0.1:8000"
  echo "  template: scripts/server/nginx/fair-crm.conf"
  if command -v nginx >/dev/null 2>&1; then
    local nginx_test_output nginx_test_rc=0
    nginx_test_output="$(run_root nginx -t 2>&1)" || nginx_test_rc=$?
    echo "  nginx -t: rc=${nginx_test_rc} (${nginx_test_output//$'\n'/; })"
    if run_root systemctl is-active nginx >/dev/null 2>&1; then
      echo "  systemctl reload nginx: service active"
      check_pass "nginx routing configured"
    else
      check_fail "nginx routing configured"
    fi
  fi
}

resolve_core_db_url() {
  read_env_key "${KYROX_CORE_DIR}/backend/.env" DATABASE_URL \
    || read_env_key "${KYROX_CORE_DIR}/backend/.env" KYROX_CORE_DATABASE_URL \
    || echo "postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/kyrox_core"
}

resolve_fair_db_url() {
  read_env_key "${FAIR_CRM_DIR}/backend/.env" DATABASE_URL \
    || read_env_key "${FAIR_CRM_DIR}/backend/.env" FAIR_CRM_DATABASE_URL \
    || echo "postgresql+psycopg2://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/fair_crm"
}
