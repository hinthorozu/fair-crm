#!/usr/bin/env bash
#
# Execute a persisted Fair CRM restore job (destructive pg_restore).
#
# NOT invoked by deploy-all.sh. Run manually after creating a restore job in
# Admin → System → Database Backups.
#
# Required guards (same as scripts/dev/run-restore-job.ps1):
#   ALLOW_RESTORE=true
#   TARGET_DATABASE_URL=postgresql+psycopg2://user:pass@127.0.0.1:5432/fair_crm
#
# Usage:
#   export ALLOW_RESTORE=true
#   export TARGET_DATABASE_URL='postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/fair_crm'
#   sudo -E /opt/fair-crm/scripts/server/run-restore-job.sh <restore-job-uuid>
#
# Optional:
#   FAIR_CRM_DIR=/opt/fair-crm
#   RESTART_BACKEND=1   # systemctl restart fair-crm-backend after success
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

  local venv_python="${FAIR_CRM_DIR}/backend/.venv/bin/python"
  [[ -x "$venv_python" ]] || die "Fair CRM venv missing: ${venv_python} (run deploy-all.sh first)"

  ensure_repo_data_dirs "$FAIR_CRM_DIR"

  step "Run maintenance restore job ${RESTORE_JOB_ID}"
  (
    cd "${FAIR_CRM_DIR}/backend"
    env ALLOW_RESTORE="${ALLOW_RESTORE}" TARGET_DATABASE_URL="${TARGET_DATABASE_URL}" \
      PYTHONPATH="${FAIR_CRM_DIR}/backend" \
      "$venv_python" -m app.modules.system_admin.maintenance.run_restore_job \
      --job-id "$RESTORE_JOB_ID" \
      --database-url "$TARGET_DATABASE_URL" \
      --allow-restore
  )

  log "Restore job runner finished successfully"
  log "Runner already applied alembic upgrade head on the target database"

  if [[ "${RESTART_BACKEND}" == "1" ]]; then
    step "Restart fair-crm-backend"
    if [[ "${EUID}" -ne 0 ]]; then
      warn "Run with sudo to restart systemd, or: sudo systemctl restart fair-crm-backend"
    else
      systemctl restart fair-crm-backend
      log "fair-crm-backend restarted"
    fi
  else
    warn "Backend not restarted. Run: sudo systemctl restart fair-crm-backend (or deploy-all.sh)"
  fi
}

main "$@"
