#!/usr/bin/env bash
# Shared helpers for server deploy scripts.

set -euo pipefail

DEPLOY_STEP=""
DEPLOY_FAILED_STEP=""
DEPLOY_LOG_PREFIX="[deploy]"

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
  log "==> $1"
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "Required command not found: ${cmd}"
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

urlencode_component() {
  python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"
}

parse_database_url() {
  # Sets PG_USER PG_PASS PG_HOST PG_PORT PG_DB globals from a postgres URL.
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
