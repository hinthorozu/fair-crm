#!/usr/bin/env bash
#
# Execute a persisted Fair CRM restore job (destructive pg_restore).
#
# NOT invoked by deploy-all.sh. Run manually after creating a restore job in
# Admin → System → Database Backups.
#
# Required guards:
#   ALLOW_RESTORE=true
#   TARGET_DATABASE_URL=<explicit target database URL>
#   fair-crm-backend and fair-crm-mail-worker must already be stopped
#   FAIR CRM restore: kyrox-core must remain active for external reconciliation
#   KYROX Core restore: kyrox-core must already be stopped; Core-owned CLI
#                       captures/reconciles lifecycle directly against the DB
#
# Usage:
#   sudo systemctl stop fair-crm-backend fair-crm-mail-worker
#   # additionally for a Core restore: sudo systemctl stop kyrox-core
#   export ALLOW_RESTORE=true
#   export TARGET_DATABASE_URL='postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/fair_crm'
#   sudo -E /opt/fair-crm/scripts/server/run-restore-job.sh <restore-job-uuid>
#
# Optional:
#   FAIR_CRM_DIR=/opt/fair-crm
#   RESTART_BACKEND=1   # restart appropriate services only after certified success
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

FAIR_CRM_DIR="${FAIR_CRM_DIR:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
RESTORE_JOB_ID="${1:-${RESTORE_JOB_ID:-}}"
ALLOW_RESTORE="${ALLOW_RESTORE:-}"
TARGET_DATABASE_URL="${TARGET_DATABASE_URL:-}"
RESTART_BACKEND="${RESTART_BACKEND:-0}"
MAINTENANCE_LOCK="${FAIR_CRM_DIR}/data/restore_maintenance.lock"
RESTORE_CERTIFIED=0
TARGET_DATABASE_KEY=""

retain_or_clear_lock() {
  if [[ "$RESTORE_CERTIFIED" == "1" ]]; then
    rm -f "$MAINTENANCE_LOCK"
    log "Restore maintenance lock cleared after certified success"
  elif [[ -e "$MAINTENANCE_LOCK" ]]; then
    warn "Restore did not certify successfully; maintenance lock retained: ${MAINTENANCE_LOCK}"
    warn "Do not start FAIR CRM or KYROX Core services until the restore failure is reconciled."
  fi
}

trap retain_or_clear_lock EXIT

assert_service_inactive() {
  local service="$1"
  if systemctl is-active --quiet "$service"; then
    die "${service} is active and must be stopped for this restore target"
  fi
}

assert_service_active() {
  local service="$1"
  if ! systemctl is-active --quiet "$service"; then
    die "${service} is not active; FAIR CRM restore requires live Core lifecycle authority"
  fi
}

resolve_target_database_key() {
  local venv_python="$1"
  (
    cd "${FAIR_CRM_DIR}/backend"
    PYTHONPATH="${FAIR_CRM_DIR}/backend" "$venv_python" - "$TARGET_DATABASE_URL" <<'PY'
import sys
from app.shared.database_backup.connection import parse_database_url
from app.shared.database_backup.database_keys import DatabaseKey, expected_database_name

actual = parse_database_url(sys.argv[1]).database
matches = [key.value for key in DatabaseKey if expected_database_name(key) == actual]
if len(matches) != 1:
    raise SystemExit(
        f"TARGET_DATABASE_URL database {actual!r} does not resolve to exactly one configured database key"
    )
print(matches[0])
PY
  )
}

main() {
  step "Fair CRM restore job runner (maintenance; not deploy)"
  log "FAIR_CRM_DIR=${FAIR_CRM_DIR}"
  log "RESTORE_JOB_ID=${RESTORE_JOB_ID:-<missing>}"
  log "ALLOW_RESTORE=${ALLOW_RESTORE:-<not set>}"
  if [[ -n "$TARGET_DATABASE_URL" ]]; then
    log "TARGET_DATABASE_URL=<set>"
  else
    log "TARGET_DATABASE_URL=<not set>"
  fi

  [[ -n "$RESTORE_JOB_ID" ]] || die "Restore job id required: run-restore-job.sh <uuid>"

  case "${ALLOW_RESTORE,,}" in
    1|true|yes) ;;
    *)
      die "Destructive restore blocked. Set ALLOW_RESTORE=true before running this script."
      ;;
  esac

  [[ -n "$TARGET_DATABASE_URL" ]] || die "TARGET_DATABASE_URL is required (explicit target DB URL)"
  command -v systemctl >/dev/null 2>&1 || die "systemctl is required for the production restore maintenance boundary"

  local venv_python="${FAIR_CRM_DIR}/backend/.venv/bin/python"
  [[ -x "$venv_python" ]] || die "Fair CRM venv missing: ${venv_python} (run deploy-all.sh first)"

  TARGET_DATABASE_KEY="$(resolve_target_database_key "$venv_python")" || die "Could not resolve restore target database key"
  log "target database key: ${TARGET_DATABASE_KEY}"

  assert_service_inactive "fair-crm-backend"
  assert_service_inactive "fair-crm-mail-worker"
  if [[ "$TARGET_DATABASE_KEY" == "kyrox_core" ]]; then
    assert_service_inactive "kyrox-core"
  elif [[ "$TARGET_DATABASE_KEY" == "fair_crm" ]]; then
    assert_service_active "kyrox-core"
  else
    die "Unsupported restore target database key: ${TARGET_DATABASE_KEY}"
  fi

  ensure_repo_data_dirs "$FAIR_CRM_DIR"
  if [[ -e "$MAINTENANCE_LOCK" ]]; then
    die "Restore maintenance lock already exists: ${MAINTENANCE_LOCK}. Resolve the previous restore before starting another."
  fi
  printf 'restore_job_id=%s\ntarget_database_key=%s\nstarted_at_utc=%s\n' \
    "$RESTORE_JOB_ID" "$TARGET_DATABASE_KEY" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$MAINTENANCE_LOCK"
  chmod 600 "$MAINTENANCE_LOCK"
  log "External restore maintenance lock created"

  step "Run OL10-certified maintenance restore job ${RESTORE_JOB_ID}"
  (
    cd "${FAIR_CRM_DIR}/backend"
    env ALLOW_RESTORE="${ALLOW_RESTORE}" TARGET_DATABASE_URL="${TARGET_DATABASE_URL}" \
      PYTHONPATH="${FAIR_CRM_DIR}/backend" \
      "$venv_python" -m app.modules.system_admin.maintenance.run_restore_job \
      --job-id "$RESTORE_JOB_ID" \
      --database-url "$TARGET_DATABASE_URL" \
      --allow-restore
  )

  RESTORE_CERTIFIED=1
  rm -f "$MAINTENANCE_LOCK"
  log "Restore job runner finished with OL10 certification"
  log "Runner applied alembic upgrade head and authoritative lifecycle reconciliation"

  if [[ "${RESTART_BACKEND}" == "1" ]]; then
    step "Start application services"
    if [[ "${EUID}" -ne 0 ]]; then
      if [[ "$TARGET_DATABASE_KEY" == "kyrox_core" ]]; then
        warn "Run with sudo to start services, or: sudo systemctl start kyrox-core fair-crm-backend fair-crm-mail-worker"
      else
        warn "Run with sudo to start services, or: sudo systemctl start fair-crm-backend fair-crm-mail-worker"
      fi
    else
      if [[ "$TARGET_DATABASE_KEY" == "kyrox_core" ]]; then
        systemctl start kyrox-core
      fi
      systemctl start fair-crm-backend fair-crm-mail-worker
      log "application services started after certified restore"
    fi
  else
    warn "Application services remain in the maintenance state. Review the certified restore log before starting stopped services."
  fi
}

main "$@"
